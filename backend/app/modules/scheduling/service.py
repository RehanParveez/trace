from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.scheduling.repository import SchedulingRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from app.modules.scheduling.schemas import ScheduleTaskCreateRequest, ProjectScheduleSettingsUpdateRequest, ScheduleTaskUpdateRequest
from app.modules.scheduling.models import ScheduleTask, ScheduleDependency, ScheduleTaskStatus
from app.modules.audit.models import AuditAction, AuditEntityType
from uuid import UUID, uuid4
from app.core.exceptions import TraceException
from app.modules.scheduling.cpm import CPMResult, TaskInput, compute_cpm

class SchedulingService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = SchedulingRepository(session)
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)

  async def create_task(
    self, organization_id: UUID, project_id: UUID, payload: ScheduleTaskCreateRequest, actor_user_id: UUID,
  ) -> ScheduleTask:
    project = await self._require_project(organization_id, project_id)

    task = ScheduleTask(
      id=uuid4(), organization_id=organization_id, project_id=project_id,
      name=payload.name.strip(), description=payload.description,
      planned_start_date=payload.planned_start_date, planned_duration_days=payload.planned_duration_days,
      is_milestone_marker=payload.is_milestone_marker,
    )
    await self.repo.create_task(task)

    for predecessor_id in payload.predecessor_task_ids:
      await self._add_dependency(organization_id, predecessor_id, task.id)

    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SCHEDULE_TASK, task.id, AuditAction.CREATE,
      f'Added schedule task "{task.name}" to {project.name}.',
    )
    return task

  async def update_task(
    self, organization_id: UUID, task_id: UUID, payload: ScheduleTaskUpdateRequest, actor_user_id: UUID,
  ) -> ScheduleTask:
    task = await self.repo.get_task(task_id, organization_id)
    if task is None:
      raise TraceException("Schedule task not found.", status_code=404, code="SCHEDULE_TASK_NOT_FOUND")

    was_complete = task.status == ScheduleTaskStatus.COMPLETE

    for field_name in (
      "name", "description", "planned_start_date", "planned_duration_days",
      "actual_start_date", "actual_end_date", "percent_complete", "is_milestone_marker",
    ):
      value = getattr(payload, field_name)
      if value is not None:
        setattr(task, field_name, value.strip() if isinstance(value, str) else value)

    self._recompute_status(task)
    await self.session.commit()

    if not was_complete and task.status == ScheduleTaskStatus.COMPLETE:
      await self.audit.log(
        organization_id, actor_user_id, AuditEntityType.SCHEDULE_TASK, task.id, AuditAction.UPDATE,
        f'Completed schedule task "{task.name}".',
      )
    return task

  async def delete_task(self, organization_id: UUID, task_id: UUID, actor_user_id: UUID) -> None:
    task = await self.repo.get_task(task_id, organization_id)
    if task is None:
      raise TraceException("Schedule task not found.", status_code=404, code="SCHEDULE_TASK_NOT_FOUND")
    name = task.name
    await self.repo.delete_task(task) 
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SCHEDULE_TASK, task_id, AuditAction.DELETE,
      f'Removed schedule task "{name}".',
    )

  async def add_dependency(
    self, organization_id: UUID, successor_task_id: UUID, predecessor_task_id: UUID, actor_user_id: UUID,
  ) -> None:
    await self._add_dependency(organization_id, predecessor_task_id, successor_task_id)
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SCHEDULE_TASK, successor_task_id, AuditAction.UPDATE,
      "Added a schedule dependency.",
    )

  async def remove_dependency(
    self, organization_id: UUID, successor_task_id: UUID, predecessor_task_id: UUID, actor_user_id: UUID,
  ) -> None:
    dependency = await self.repo.get_dependency(organization_id, predecessor_task_id, successor_task_id)
    if dependency is None:
      raise TraceException("Dependency not found.", status_code=404, code="SCHEDULE_DEPENDENCY_NOT_FOUND")
    await self.repo.delete_dependency(dependency)
    await self.session.commit()

  async def update_settings(
    self, organization_id: UUID, project_id: UUID, payload: ProjectScheduleSettingsUpdateRequest,
  ):
    settings = await self.repo.get_or_create_settings(organization_id, project_id)
    settings.target_completion_date = payload.target_completion_date
    await self.session.commit()
    return settings

  async def get_project_schedule(self, organization_id: UUID, project_id: UUID) -> dict:
    await self._require_project(organization_id, project_id)
    settings = await self.repo.get_or_create_settings(organization_id, project_id)
    tasks = await self.repo.list_tasks_by_project(organization_id, project_id)
    dependencies = await self.repo.list_dependencies_by_project(organization_id, project_id)

    predecessors_by_successor: dict[UUID, list[UUID]] = {task.id: [] for task in tasks}
    for dep in dependencies:
      predecessors_by_successor.setdefault(dep.successor_task_id, []).append(dep.predecessor_task_id)

    cpm_inputs = [
      TaskInput(
        id=task.id, planned_start_date=task.planned_start_date, planned_duration_days=task.planned_duration_days,
        predecessor_ids=predecessors_by_successor.get(task.id, []),
      )
      for task in tasks
    ]
    result: CPMResult = compute_cpm(cpm_inputs, settings.target_completion_date)

    task_responses = []
    for task in tasks:
      computed = result.tasks.get(task.id)
      task_responses.append({
        "id": task.id, "name": task.name, "description": task.description,
        "planned_start_date": task.planned_start_date, "planned_duration_days": task.planned_duration_days,
        "is_milestone_marker": task.is_milestone_marker, "actual_start_date": task.actual_start_date,
        "actual_end_date": task.actual_end_date, "percent_complete": task.percent_complete,
        "status": task.status.value, "sort_order": task.sort_order,
        "predecessor_task_ids": predecessors_by_successor.get(task.id, []),
        "is_computable": computed.is_computable if computed else False,
        "earliest_start": computed.earliest_start if computed else None,
        "earliest_finish": computed.earliest_finish if computed else None,
        "latest_start": computed.latest_start if computed else None,
        "latest_finish": computed.latest_finish if computed else None,
        "total_float_days": computed.total_float_days if computed else None,
        "is_critical": computed.is_critical if computed else False,
      })

    return {
      "project_id": project_id, "target_completion_date": settings.target_completion_date,
      "natural_completion_date": result.natural_completion_date,
      "days_ahead_or_behind_target": result.days_ahead_or_behind_target,
      "warnings": result.warnings, "tasks": task_responses,
    }

  async def _add_dependency(self, organization_id: UUID, predecessor_task_id: UUID, successor_task_id: UUID) -> None:
    if predecessor_task_id == successor_task_id:
      raise TraceException("A task cannot depend on itself.", status_code=422, code="SCHEDULE_SELF_DEPENDENCY")

    predecessor = await self.repo.get_task(predecessor_task_id, organization_id)
    successor = await self.repo.get_task(successor_task_id, organization_id)
    if predecessor is None or successor is None:
      raise TraceException("One of these tasks was not found.", status_code=404, code="SCHEDULE_TASK_NOT_FOUND")
    if predecessor.project_id != successor.project_id:
      raise TraceException(
        "Dependencies can only be created between tasks in the same project.",
        status_code=422, code="SCHEDULE_CROSS_PROJECT_DEPENDENCY",
      )

    existing = await self.repo.get_dependency(organization_id, predecessor_task_id, successor_task_id)
    if existing is not None:
      return

    if await self._would_create_cycle(organization_id, successor.project_id, predecessor_task_id, successor_task_id):
      raise TraceException(
        "This dependency would create a circular loop in the schedule.",
        status_code=422, code="SCHEDULE_CYCLE_DETECTED",
      )

    dependency = ScheduleDependency(
      id=uuid4(), organization_id=organization_id,
      predecessor_task_id=predecessor_task_id, successor_task_id=successor_task_id,
    )
    await self.repo.create_dependency(dependency)

  async def _would_create_cycle(
    self, organization_id: UUID, project_id: UUID, new_predecessor_id: UUID, new_successor_id: UUID,
  ) -> bool:
    dependencies = await self.repo.list_dependencies_by_project(organization_id, project_id)
    successors_of: dict[UUID, list[UUID]] = {}
    for dep in dependencies:
      successors_of.setdefault(dep.predecessor_task_id, []).append(dep.successor_task_id)

    visited: set[UUID] = set()
    queue = [new_successor_id]
    while queue:
      current = queue.pop()
      if current == new_predecessor_id:
        return True
      if current in visited:
        continue
      visited.add(current)
      queue.extend(successors_of.get(current, []))
    return False

  @staticmethod
  def _recompute_status(task: ScheduleTask) -> None:
    if task.percent_complete >= 100 or task.actual_end_date is not None:
      task.status = ScheduleTaskStatus.COMPLETE
    elif task.actual_start_date is not None:
      task.status = ScheduleTaskStatus.IN_PROGRESS
    else:
      task.status = ScheduleTaskStatus.NOT_STARTED

  async def _require_project(self, organization_id: UUID, project_id: UUID):
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    return project
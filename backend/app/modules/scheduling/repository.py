from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.scheduling.models import ProjectSchedule, ScheduleDependency, ScheduleTask
from sqlalchemy import select

class SchedulingRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_or_create_settings(self, organization_id: UUID, project_id: UUID) -> ProjectSchedule:
    result = await self.session.execute(
      select(ProjectSchedule).where(
        ProjectSchedule.organization_id == organization_id, ProjectSchedule.project_id == project_id,
      )
    )
    settings = result.scalar_one_or_none()
    if settings is None:
      import uuid as _uuid
      settings = ProjectSchedule(id=_uuid.uuid4(), organization_id=organization_id, project_id=project_id)
      self.session.add(settings)
      await self.session.flush()
    return settings

  async def create_task(self, task: ScheduleTask) -> ScheduleTask:
    self.session.add(task)
    await self.session.flush()
    return task

  async def get_task(self, task_id: UUID, organization_id: UUID) -> ScheduleTask | None:
    result = await self.session.execute(
      select(ScheduleTask).where(ScheduleTask.id == task_id, ScheduleTask.organization_id == organization_id)
    )
    return result.scalar_one_or_none()

  async def list_tasks_by_project(self, organization_id: UUID, project_id: UUID) -> list[ScheduleTask]:
    result = await self.session.execute(
      select(ScheduleTask)
      .where(ScheduleTask.organization_id == organization_id, ScheduleTask.project_id == project_id)
      .order_by(ScheduleTask.sort_order.asc(), ScheduleTask.created_at.asc())
    )
    return list(result.scalars().all())

  async def delete_task(self, task: ScheduleTask) -> None:
    await self.session.delete(task)
    await self.session.flush()

  async def create_dependency(self, dependency: ScheduleDependency) -> ScheduleDependency:
    self.session.add(dependency)
    await self.session.flush()
    return dependency

  async def get_dependency(
    self, organization_id: UUID, predecessor_task_id: UUID, successor_task_id: UUID,
  ) -> ScheduleDependency | None:
    result = await self.session.execute(
      select(ScheduleDependency).where(
        ScheduleDependency.organization_id == organization_id,
        ScheduleDependency.predecessor_task_id == predecessor_task_id,
        ScheduleDependency.successor_task_id == successor_task_id,
      )
    )
    return result.scalar_one_or_none()

  async def delete_dependency(self, dependency: ScheduleDependency) -> None:
    await self.session.delete(dependency)
    await self.session.flush()

  async def list_dependencies_by_project(self, organization_id: UUID, project_id: UUID) -> list[ScheduleDependency]:
    result = await self.session.execute(
      select(ScheduleDependency)
      .join(ScheduleTask, ScheduleTask.id == ScheduleDependency.successor_task_id)
      .where(ScheduleDependency.organization_id == organization_id, ScheduleTask.project_id == project_id)
    )
    return list(result.scalars().all())
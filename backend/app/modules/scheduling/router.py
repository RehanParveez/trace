from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.scheduling.service import SchedulingService
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.scheduling.schemas import ProjectScheduleResponse, ProjectScheduleSettingsUpdateRequest, ScheduleDependencyCreateRequest, ScheduleTaskCreateRequest, ScheduleTaskUpdateRequest

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])

def _service(session: AsyncSession) -> SchedulingService:
  return SchedulingService(session)

@router.post("/projects/{project_id}/tasks", status_code=201)
async def create_task(
  project_id: UUID,
  payload: ScheduleTaskCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _service(session).create_task(current_user.active_membership.organization_id, project_id, payload, current_user.id)
  return {"message": "Task created."}

@router.get("/projects/{project_id}/schedule", response_model=ProjectScheduleResponse)
async def get_project_schedule(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_project_schedule(current_user.active_membership.organization_id, project_id)
  return ProjectScheduleResponse(**data)

@router.patch("/tasks/{task_id}")
async def update_task(
  task_id: UUID,
  payload: ScheduleTaskUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _service(session).update_task(current_user.active_membership.organization_id, task_id, payload, current_user.id)
  return {"message": "Task updated."}

@router.delete("/tasks/{task_id}")
async def delete_task(
  task_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _service(session).delete_task(current_user.active_membership.organization_id, task_id, current_user.id)
  return {"message": "Task removed."}

@router.post("/tasks/{task_id}/predecessors", status_code=201)
async def add_predecessor(
  task_id: UUID,
  payload: ScheduleDependencyCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _service(session).add_dependency(
    current_user.active_membership.organization_id, task_id, payload.predecessor_task_id, current_user.id,
  )
  return {"message": "Dependency added."}

@router.delete("/tasks/{task_id}/predecessors/{predecessor_task_id}")
async def remove_predecessor(
  task_id: UUID,
  predecessor_task_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _service(session).remove_dependency(
    current_user.active_membership.organization_id, task_id, predecessor_task_id, current_user.id,
  )
  return {"message": "Dependency removed."}

@router.patch("/projects/{project_id}/settings")
async def update_settings(
  project_id: UUID,
  payload: ProjectScheduleSettingsUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _service(session).update_settings(current_user.active_membership.organization_id, project_id, payload)
  return {"message": "Schedule settings updated."}
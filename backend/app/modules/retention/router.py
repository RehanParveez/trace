from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.retention.service import RetentionService
from app.modules.retention.schemas import RetentionReleaseCreateRequest, ProjectRetentionSummaryResponse, RetentionReleaseResponse, OrganizationRetentionSummaryResponse
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey

router = APIRouter(prefix="/retention", tags=["Retention"])

def _service(session: AsyncSession) -> RetentionService:
  return RetentionService(session)

@router.post("/releases", response_model=RetentionReleaseResponse, status_code=201)
async def record_release(
  payload: RetentionReleaseCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RETENTION_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).record_release(current_user.active_membership.organization_id, payload, current_user.id)

@router.get("/releases", response_model=list[RetentionReleaseResponse])
async def list_releases(
  project_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.RETENTION_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_releases(current_user.active_membership.organization_id, project_id)

@router.get("/projects/{project_id}/summary", response_model=ProjectRetentionSummaryResponse)
async def get_project_summary(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RETENTION_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_project_summary(current_user.active_membership.organization_id, project_id)
  return ProjectRetentionSummaryResponse(**data)

@router.get("/organization-summary", response_model=OrganizationRetentionSummaryResponse)
async def get_organization_summary(
  current_user: User = Depends(require_permission(PermissionKey.RETENTION_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_organization_summary(current_user.active_membership.organization_id)
  return OrganizationRetentionSummaryResponse(**data)
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.site_progress.service import SiteProgressService
from app.modules.site_progress.schemas import SiteLogResponse, SiteLogCreateRequest, SiteLogUpdateRequest
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

router = APIRouter(prefix="/site-logs", tags=["Site Progress"])

def _service(session: AsyncSession) -> SiteProgressService:
  return SiteProgressService(session)

@router.get("", response_model=list[SiteLogResponse])
async def list_logs(
  project_id: UUID | None = Query(default=None, alias="project_id"),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=200),
  current_user: User = Depends(require_permission(PermissionKey.SITE_LOG_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).list_logs(
    org_id, project_id, skip=skip, limit=limit,
  )

@router.post("", response_model=SiteLogResponse, status_code=201)
async def create_log(
  payload: SiteLogCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SITE_LOG_CREATE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).create_log(org_id, current_user.id, payload)

@router.patch("/{log_id}", response_model=SiteLogResponse)
async def update_log(
  log_id: UUID,
  payload: SiteLogUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SITE_LOG_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).update_log(org_id, log_id, payload)

@router.delete("/{log_id}", status_code=204)
async def delete_log(
  log_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SITE_LOG_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  await _service(session).delete_log(org_id, log_id)
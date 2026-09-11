from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.procurement.service import ProcurementService
from app.modules.procurement.schemas import ProcurementCreateRequest, ProcurementOrganizationSummaryResponse, ProcurementResponse, ProcurementStatusUpdateRequest
from app.modules.procurement.models import ProcurementStatus
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db

router = APIRouter(prefix="/procurement", tags=["Procurement"])

def _service(session: AsyncSession) -> ProcurementService:
  return ProcurementService(session)

@router.get("/requests", response_model=list[ProcurementResponse])
async def list_requests(
  project_id: UUID | None = Query(default=None),
  status: ProcurementStatus | None = Query(default=None),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=200),
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).list_requests(
    org_id, project_id, status, skip, limit,
  )
  
@router.get("/organization-summary", response_model=ProcurementOrganizationSummaryResponse)
async def get_organization_summary(
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).get_organization_summary(org_id)

@router.post("/requests", response_model=ProcurementResponse, status_code=201)
async def create_request(
  payload: ProcurementCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_CREATE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).create_request(org_id, current_user.id, payload)

@router.patch("/requests/{request_id}/status", response_model=ProcurementResponse)
async def update_status(
  request_id: UUID,
  payload: ProcurementStatusUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).update_status(org_id, request_id, payload)
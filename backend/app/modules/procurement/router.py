from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.procurement.service import ProcurementService
from app.modules.procurement.schemas import (ProcurementCreateRequest, ProcurementDeliveryCreateRequest, ProcurementDeliveryResponse, ProcurementDeliveryVoidRequest, ProcurementOrganizationSummaryResponse, ProcurementResponse,
  ProcurementStatusSummaryResponse, ProcurementStatusUpdateRequest,
)
from datetime import date
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

@router.get("/status-summary", response_model=ProcurementStatusSummaryResponse)
async def get_status_summary(
  project_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  counts = await _service(session).get_status_counts(org_id, project_id)
  return ProcurementStatusSummaryResponse(
    counts={status.value: count for status, count in counts.items()}
  )

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
  return await _service(session).update_status(org_id, request_id, payload, current_user.id)

@router.post("/requests/{request_id}/deliveries", response_model=ProcurementDeliveryResponse, status_code=201)
async def record_delivery(
  request_id: UUID,
  payload: ProcurementDeliveryCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).record_delivery(org_id, request_id, payload, current_user.id)

@router.get("/requests/{request_id}/deliveries", response_model=list[ProcurementDeliveryResponse])
async def list_request_deliveries(
  request_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).list_deliveries(org_id, request_id=request_id)

@router.get("/projects/{project_id}/deliveries", response_model=list[ProcurementDeliveryResponse])
async def list_project_deliveries(
  project_id: UUID,
  date_from: date | None = Query(default=None),
  date_to: date | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).list_deliveries(
    org_id, project_id=project_id, date_from=date_from, date_to=date_to,
  )

@router.post("/deliveries/{delivery_id}/void", response_model=ProcurementDeliveryResponse)
async def void_delivery(
  delivery_id: UUID,
  payload: ProcurementDeliveryVoidRequest,
  current_user: User = Depends(require_permission(PermissionKey.PROCUREMENT_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).void_delivery(org_id, delivery_id, payload, current_user.id)
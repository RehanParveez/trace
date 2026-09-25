from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.change_orders.service import ChangeOrderService
from uuid import UUID
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.change_orders.schemas import ( ChangeOrderApproveRequest, ChangeOrderCancelRequest, ChangeOrderCreateRequest, ChangeOrderDetailResponse, ChangeOrderRejectRequest, ChangeOrderResponse,
  ProjectChangeOrderSummaryResponse,
)

router = APIRouter(prefix="/change-orders", tags=["Change Orders"])

def _service(session: AsyncSession) -> ChangeOrderService:
  return ChangeOrderService(session)

@router.post("", response_model=ChangeOrderDetailResponse, status_code=201)
async def create_change_order(
  payload: ChangeOrderCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.CHANGE_ORDER_CREATE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_change_order(
    current_user.active_membership.organization_id, payload, current_user.id,
  )

@router.get("", response_model=list[ChangeOrderDetailResponse])
async def list_change_orders(
  project_id: UUID = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.CHANGE_ORDER_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_change_orders(current_user.active_membership.organization_id, project_id)

@router.get("/{change_order_id}", response_model=ChangeOrderDetailResponse)
async def get_change_order(
  change_order_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.CHANGE_ORDER_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).get_change_order(current_user.active_membership.organization_id, change_order_id)

@router.get("/projects/{project_id}/summary", response_model=ProjectChangeOrderSummaryResponse)
async def get_project_summary(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.CHANGE_ORDER_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_project_summary(current_user.active_membership.organization_id, project_id)
  return ProjectChangeOrderSummaryResponse(**data)

@router.post("/{change_order_id}/approve", response_model=ChangeOrderResponse)
async def approve_change_order(
  change_order_id: UUID,
  payload: ChangeOrderApproveRequest,
  current_user: User = Depends(require_permission(PermissionKey.CHANGE_ORDER_APPROVE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).approve_change_order(
    current_user.active_membership.organization_id, change_order_id, payload.version, current_user.id,
  )

@router.post("/{change_order_id}/reject", response_model=ChangeOrderResponse)
async def reject_change_order(
  change_order_id: UUID,
  payload: ChangeOrderRejectRequest,
  current_user: User = Depends(require_permission(PermissionKey.CHANGE_ORDER_APPROVE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).reject_change_order(
    current_user.active_membership.organization_id, change_order_id, payload.version, payload.reason, current_user.id,
  )

@router.post("/{change_order_id}/cancel", response_model=ChangeOrderResponse)
async def cancel_change_order(
  change_order_id: UUID,
  payload: ChangeOrderCancelRequest,
  current_user: User = Depends(require_permission(PermissionKey.CHANGE_ORDER_CREATE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).cancel_change_order(
    current_user.active_membership.organization_id, change_order_id, payload.version, current_user.id,
  )
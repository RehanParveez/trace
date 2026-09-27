from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.cash_flow.service import CashFlowService
from app.modules.cash_flow.schemas import CashFlowForecastResponse, CashFlowSettingsResponse, CashFlowSettingsUpdateRequest
from decimal import Decimal
from uuid import UUID
from app.modules.identity.models import User
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey

router = APIRouter(prefix="/cash-flow", tags=["Cash Flow"])

def _service(session: AsyncSession) -> CashFlowService:
  return CashFlowService(session)

@router.get("/forecast", response_model=CashFlowForecastResponse)
async def get_forecast(
  project_id: UUID | None = Query(default=None),
  horizon_days: int = Query(default=90, ge=7, le=180),
  starting_cash_balance: float | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.CASH_FLOW_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_forecast(
    current_user.active_membership.organization_id, project_id, horizon_days,
    Decimal(str(starting_cash_balance)) if starting_cash_balance is not None else None,
  )
  return CashFlowForecastResponse(**data)

@router.get("/settings", response_model=CashFlowSettingsResponse)
async def get_settings(
  current_user: User = Depends(require_permission(PermissionKey.CASH_FLOW_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).get_settings(current_user.active_membership.organization_id)

@router.patch("/settings", response_model=CashFlowSettingsResponse)
async def update_settings(
  payload: CashFlowSettingsUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.CASH_FLOW_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_settings(current_user.active_membership.organization_id, payload)
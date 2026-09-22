from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.modules.withholding_tax.service import WithholdingTaxService
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.withholding_tax.schemas import WHTRateCreateRequest, WHTDeductionResponse, WHTPreviewResponse, WHTRateResponse, WHTRateUpdateRequest, WHTRegisterSummaryResponse
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey
from uuid import UUID
from datetime import date
from app.modules.withholding_tax.models import WHTCategory
from decimal import Decimal

router = APIRouter(prefix="/withholding-tax", tags=["Withholding Tax"])

def _service(session: AsyncSession) -> WithholdingTaxService:
  return WithholdingTaxService(session)

@router.post("/rates", response_model=WHTRateResponse, status_code=201)
async def create_rate(
  payload: WHTRateCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.WITHHOLDING_TAX_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_rate(current_user.active_membership.organization_id, payload)

@router.get("/rates", response_model=list[WHTRateResponse])
async def list_rates(
  current_user: User = Depends(require_permission(PermissionKey.WITHHOLDING_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_rates(current_user.active_membership.organization_id)

@router.patch("/rates/{rate_id}", response_model=WHTRateResponse)
async def update_rate(
  rate_id: UUID,
  payload: WHTRateUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.WITHHOLDING_TAX_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_rate(current_user.active_membership.organization_id, rate_id, payload)

@router.get("/preview", response_model=WHTPreviewResponse)
async def preview_wht(
  category: WHTCategory = Query(...),
  gross_amount: float = Query(..., gt=0),
  is_filer: bool = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.WITHHOLDING_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):

  gross = Decimal(str(gross_amount))
  rate_percentage, deducted_amount = await _service(session).calculate_preview(
    current_user.active_membership.organization_id, category, gross, is_filer,
  )
  return WHTPreviewResponse(
    category=category, rate_percentage=rate_percentage, gross_amount=gross,
    deducted_amount=deducted_amount, net_after_wht=gross - deducted_amount,
  )

@router.get("/deductions", response_model=list[WHTDeductionResponse])
async def list_deductions(
  period_start: date | None = Query(default=None),
  period_end: date | None = Query(default=None),
  project_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.WITHHOLDING_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_deductions(
    current_user.active_membership.organization_id, period_start, period_end, project_id,
  )

@router.get("/deductions/summary", response_model=WHTRegisterSummaryResponse)
async def get_register_summary(
  period_start: date = Query(...),
  period_end: date = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.WITHHOLDING_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_register_summary(
    current_user.active_membership.organization_id, period_start, period_end,
  )
  return WHTRegisterSummaryResponse(**data)
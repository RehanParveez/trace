from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.sales_tax.service import SalesTaxService
from app.modules.sales_tax.schemas import SalesTaxRateResponse, SalesTaxChargeResponse, SalesTaxPreviewResponse, SalesTaxRateCreateRequest, SalesTaxRateUpdateRequest, SalesTaxRegisterSummaryResponse
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey
from decimal import Decimal
from uuid import UUID
from app.modules.identity.models import User
from app.modules.sales_tax.models import SalesTaxAuthority
from datetime import date

router = APIRouter(prefix="/sales-tax", tags=["Sales Tax"])

def _service(session: AsyncSession) -> SalesTaxService:
  return SalesTaxService(session)

@router.post("/rates", response_model=SalesTaxRateResponse, status_code=201)
async def create_rate(
  payload: SalesTaxRateCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SALES_TAX_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_rate(current_user.active_membership.organization_id, payload)

@router.get("/rates", response_model=list[SalesTaxRateResponse])
async def list_rates(
  current_user: User = Depends(require_permission(PermissionKey.SALES_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_rates(current_user.active_membership.organization_id)

@router.patch("/rates/{rate_id}", response_model=SalesTaxRateResponse)
async def update_rate(
  rate_id: UUID,
  payload: SalesTaxRateUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SALES_TAX_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_rate(current_user.active_membership.organization_id, rate_id, payload)

@router.get("/preview", response_model=SalesTaxPreviewResponse)
async def preview_sales_tax(
  authority: SalesTaxAuthority = Query(...),
  taxable_amount: float = Query(..., gt=0),
  current_user: User = Depends(require_permission(PermissionKey.SALES_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):
  amount = Decimal(str(taxable_amount))
  rate_percentage, tax_amount = await _service(session).calculate_preview(
    current_user.active_membership.organization_id, authority, amount,
  )
  return SalesTaxPreviewResponse(
    authority=authority, rate_percentage=rate_percentage, taxable_amount=amount,
    tax_amount=tax_amount, total_including_tax=amount + tax_amount,
  )

@router.get("/charges", response_model=list[SalesTaxChargeResponse])
async def list_charges(
  period_start: date | None = Query(default=None),
  period_end: date | None = Query(default=None),
  project_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.SALES_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_charges(
    current_user.active_membership.organization_id, period_start, period_end, project_id,
  )

@router.get("/charges/summary", response_model=SalesTaxRegisterSummaryResponse)
async def get_register_summary(
  period_start: date = Query(...),
  period_end: date = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.SALES_TAX_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_register_summary(
    current_user.active_membership.organization_id, period_start, period_end,
  )
  return SalesTaxRegisterSummaryResponse(**data)
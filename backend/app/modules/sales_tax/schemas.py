from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from app.modules.sales_tax.models import SalesTaxAuthority
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID

class SalesTaxRateCreateRequest(BaseModel):
  authority: SalesTaxAuthority
  rate_percentage: Decimal = Field(ge=0, le=100)
  effective_from: date
  notes: str | None = None

class SalesTaxRateUpdateRequest(BaseModel):
  rate_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  effective_from: date | None = None
  is_active: bool | None = None
  notes: str | None = None

class SalesTaxRateResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  authority: SalesTaxAuthority
  rate_percentage: Decimal
  effective_from: date
  is_active: bool
  notes: str | None

class SalesTaxPreviewResponse(BaseModel):
  authority: SalesTaxAuthority
  rate_percentage: Decimal
  taxable_amount: Decimal
  tax_amount: Decimal
  total_including_tax: Decimal

class SalesTaxChargeResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  source_type: str
  source_id: UUID
  authority: SalesTaxAuthority
  rate_percentage: Decimal
  taxable_amount: Decimal
  tax_amount: Decimal
  charge_date: date
  currency: str
  created_at: datetime

class SalesTaxAuthoritySummary(BaseModel):
  authority: SalesTaxAuthority
  total_taxable_amount: Decimal
  total_tax_amount: Decimal
  charge_count: int

class SalesTaxRegisterSummaryResponse(BaseModel):
  period_start: date
  period_end: date
  by_authority: list[SalesTaxAuthoritySummary]
  total_tax_amount: Decimal
  currency: str
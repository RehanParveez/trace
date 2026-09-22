from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from app.modules.withholding_tax.models import WHTCategory
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID

class WHTRateCreateRequest(BaseModel):
  category: WHTCategory
  filer_rate_percentage: Decimal = Field(ge=0, le=100)
  non_filer_rate_percentage: Decimal = Field(ge=0, le=100)
  effective_from: date
  notes: str | None = None

class WHTRateUpdateRequest(BaseModel):
  filer_rate_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  non_filer_rate_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  effective_from: date | None = None
  is_active: bool | None = None
  notes: str | None = None

class WHTRateResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  category: WHTCategory
  filer_rate_percentage: Decimal
  non_filer_rate_percentage: Decimal
  effective_from: date
  is_active: bool
  notes: str | None

class WHTPreviewResponse(BaseModel):
  category: WHTCategory
  rate_percentage: Decimal
  gross_amount: Decimal
  deducted_amount: Decimal
  net_after_wht: Decimal

class WHTDeductionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  source_type: str
  source_id: UUID
  payee_name: str
  payee_ntn_or_cnic: str | None
  category: WHTCategory
  gross_amount: Decimal
  rate_percentage: Decimal
  is_filer: bool
  deducted_amount: Decimal
  deduction_date: date
  currency: str
  created_at: datetime

class WHTCategorySummary(BaseModel):
  category: WHTCategory
  total_gross_amount: Decimal
  total_deducted_amount: Decimal
  deduction_count: int

class WHTRegisterSummaryResponse(BaseModel):
  period_start: date
  period_end: date
  by_category: list[WHTCategorySummary]
  total_deducted_amount: Decimal
  currency: str
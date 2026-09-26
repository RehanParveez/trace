from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from app.modules.running_bills.models import RunningBillStatus
from app.modules.sales_tax.models import SalesTaxAuthority

class RunningBillLineItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  boq_item_id: UUID
  material_name: str
  unit: str
  contract_quantity: Decimal
  unit_rate: Decimal
  previous_percentage: Decimal
  cumulative_percentage: Decimal
  previous_quantity: Decimal
  cumulative_quantity: Decimal
  this_period_quantity: Decimal
  previous_value: Decimal
  cumulative_value: Decimal
  this_period_value: Decimal

class RunningBillResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  boq_version_id: UUID
  bill_number: int
  status: RunningBillStatus
  period_start: date
  period_end: date
  gross_value_this_period: Decimal
  gross_value_cumulative: Decimal
  retention_percentage: Decimal
  retention_cap_percentage: Decimal | None
  retention_this_period: Decimal
  retention_cumulative: Decimal
  advance_recovery_amount: Decimal
  other_deductions_amount: Decimal
  other_deductions_note: str | None
  net_payable: Decimal
  sales_tax_authority: str | None
  sales_tax_rate_percentage: Decimal | None
  sales_tax_amount: Decimal
  total_amount_due: Decimal = Decimal("0")
  currency: str
  notes: str | None
  version: int
  issued_at: datetime | None
  created_at: datetime

  @model_validator(mode="after")
  def _compute_total_amount_due(self) -> "RunningBillResponse":
    self.total_amount_due = self.net_payable + self.sales_tax_amount
    return self

class RunningBillDetailResponse(RunningBillResponse):
  line_items: list[RunningBillLineItemResponse] = Field(default_factory=list)

class RunningBillCreateRequest(BaseModel):
  project_id: UUID
  boq_version_id: UUID
  period_start: date
  period_end: date
  retention_percentage: Decimal = Field(default=Decimal("10"), ge=0, le=100)
  retention_cap_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  advance_recovery_amount: Decimal = Field(default=Decimal("0"), ge=0)
  other_deductions_amount: Decimal = Field(default=Decimal("0"), ge=0)
  other_deductions_note: str | None = Field(default=None, max_length=500)
  sales_tax_authority: SalesTaxAuthority | None = None
  notes: str | None = None

  @model_validator(mode="after")
  def _validate_period(self) -> "RunningBillCreateRequest":
    if self.period_end < self.period_start:
      raise ValueError("period_end must be on or after period_start.")
    return self

class RunningBillIssueRequest(BaseModel):
  version: int

class RunningBillCancelRequest(BaseModel):
  version: int
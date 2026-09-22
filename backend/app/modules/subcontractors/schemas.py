from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from app.modules.subcontractors.models import SubcontractAgreementStatus, SubcontractorBillStatus
from app.modules.withholding_tax.models import WHTCategory

class SubcontractorCreateRequest(BaseModel):
  name: str = Field(min_length=1, max_length=200)
  trade_specialization: str = Field(min_length=1, max_length=100)
  contact_name: str | None = None
  contact_phone: str | None = None
  ntn_or_cnic: str | None = None
  is_active_taxpayer: bool = False
  notes: str | None = None

class SubcontractorUpdateRequest(BaseModel):
  name: str | None = Field(default=None, min_length=1, max_length=200)
  trade_specialization: str | None = Field(default=None, min_length=1, max_length=100)
  contact_name: str | None = None
  contact_phone: str | None = None
  ntn_or_cnic: str | None = None
  is_active_taxpayer: bool = False
  is_active: bool | None = None
  notes: str | None = None

class SubcontractorResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  name: str
  trade_specialization: str
  contact_name: str | None
  contact_phone: str | None
  ntn_or_cnic: str | None
  is_active_taxpayer: bool = False
  is_active: bool
  notes: str | None

class AgreementItemInput(BaseModel):
  description: str = Field(min_length=1, max_length=300)
  unit: str = Field(min_length=1, max_length=50)
  quantity: Decimal = Field(gt=0)
  rate: Decimal = Field(ge=0)

class SubcontractAgreementCreateRequest(BaseModel):
  project_id: UUID
  subcontractor_id: UUID
  scope_description: str = Field(min_length=1)
  start_date: date
  default_retention_percentage: Decimal = Field(default=Decimal("10"), ge=0, le=100)
  default_retention_cap_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  notes: str | None = None
  items: list[AgreementItemInput] | None = None
  contract_value: Decimal | None = Field(default=None, gt=0)

  @model_validator(mode="after")
  def _validate_value_source(self) -> "SubcontractAgreementCreateRequest":
    if not self.items and self.contract_value is None:
      raise ValueError("Provide either a list of items or a flat contract_value.")
    return self

class SubcontractAgreementUpdateRequest(BaseModel):
  end_date: date | None = None
  status: SubcontractAgreementStatus | None = None
  default_retention_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  version: int

class AgreementItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  description: str
  unit: str
  quantity: Decimal
  rate: Decimal

class SubcontractAgreementResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  subcontractor_id: UUID
  scope_description: str
  contract_value: Decimal
  default_retention_percentage: Decimal
  default_retention_cap_percentage: Decimal | None
  start_date: date
  end_date: date | None
  status: SubcontractAgreementStatus
  notes: str | None
  version: int

class SubcontractAgreementDetailResponse(SubcontractAgreementResponse):
  items: list[AgreementItemResponse] = Field(default_factory=list)

class BillMeasurementInput(BaseModel):
  agreement_item_id: UUID
  cumulative_percentage: Decimal = Field(ge=0, le=100)

class SubcontractorBillCreateRequest(BaseModel):
  agreement_id: UUID
  period_start: date
  period_end: date
  retention_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  retention_cap_percentage: Decimal | None = Field(default=None, ge=0, le=100)
  other_deductions_amount: Decimal = Field(default=Decimal("0"), ge=0)
  other_deductions_note: str | None = Field(default=None, max_length=500)
  notes: str | None = None
  measurements: list[BillMeasurementInput] = Field(min_length=1)

  @model_validator(mode="after")
  def _validate_period(self) -> "SubcontractorBillCreateRequest":
    if self.period_end < self.period_start:
      raise ValueError("period_end must be on or after period_start.")
    return self

class SubcontractorBillIssueRequest(BaseModel):
  version: int

class SubcontractorBillCancelRequest(BaseModel):
  version: int

class SubcontractorBillLineItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  agreement_item_id: UUID
  description: str
  unit: str
  contract_quantity: Decimal
  rate: Decimal
  previous_percentage: Decimal
  cumulative_percentage: Decimal
  this_period_value: Decimal
  cumulative_value: Decimal

class SubcontractorBillResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  agreement_id: UUID
  bill_number: int
  status: SubcontractorBillStatus
  period_start: date
  period_end: date
  gross_value_this_period: Decimal
  gross_value_cumulative: Decimal
  retention_percentage: Decimal
  retention_cap_percentage: Decimal | None
  retention_this_period: Decimal
  retention_cumulative: Decimal
  other_deductions_amount: Decimal
  other_deductions_note: str | None
  net_payable: Decimal
  currency: str
  notes: str | None
  version: int
  issued_at: datetime | None
  created_at: datetime

class SubcontractorBillDetailResponse(SubcontractorBillResponse):
  line_items: list[SubcontractorBillLineItemResponse] = Field(default_factory=list)

class SubcontractorAdvanceCreateRequest(BaseModel):
  amount: Decimal = Field(gt=0)
  advance_date: date
  notes: str | None = None

class SubcontractorAdvanceResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  amount: Decimal
  advance_date: date
  notes: str | None

class SubcontractorPaymentCreateRequest(BaseModel):
  bill_id: UUID | None = None
  gross_amount: Decimal = Field(gt=0)
  advance_recovered_amount: Decimal = Field(default=Decimal("0"), ge=0)
  wht_category: "WHTCategory | None" = None
  payment_date: date
  notes: str | None = None

class SubcontractorPaymentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  bill_id: UUID | None
  gross_amount: Decimal
  advance_recovered_amount: Decimal
  wht_category: str | None
  wht_rate_percentage: Decimal | None
  wht_deducted_amount: Decimal
  net_paid_amount: Decimal
  payment_date: date
  notes: str | None

class SubcontractorLedgerResponse(BaseModel):
  agreement_id: UUID
  contract_value: Decimal
  total_billed: Decimal
  total_paid: Decimal
  outstanding_bill_balance: Decimal
  total_advances_given: Decimal
  outstanding_advance_balance: Decimal
  currency: str

class ProjectSubcontractCostResponse(BaseModel):
  project_id: UUID
  total_billed: Decimal
  currency: str
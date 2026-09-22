from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.modules.labour.models import LabourSourceType, LabourDeploymentStatus
from uuid import UUID
from decimal import Decimal
from datetime import date
from app.modules.withholding_tax.models import WHTCategory

class LabourSourceCreateRequest(BaseModel):
  name: str = Field(min_length=1, max_length=200)
  source_type: LabourSourceType
  contact_name: str | None = None
  contact_phone: str | None = None
  is_active_taxpayer: bool = False
  notes: str | None = None

class LabourSourceUpdateRequest(BaseModel):
  name: str | None = Field(default=None, min_length=1, max_length=200)
  contact_name: str | None = None
  contact_phone: str | None = None
  is_active_taxpayer: bool | None = None
  is_active: bool | None = None
  notes: str | None = None

class LabourSourceResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  name: str
  source_type: LabourSourceType
  contact_name: str | None
  contact_phone: str | None
  is_active_taxpayer: bool
  is_active: bool
  notes: str | None

class LabourWorkerCreateRequest(BaseModel):
  source_id: UUID
  name: str = Field(min_length=1, max_length=200)
  trade: str = Field(min_length=1, max_length=100)
  cnic: str | None = None
  phone: str | None = None
  default_daily_rate: Decimal | None = Field(default=None, ge=0)

class LabourWorkerUpdateRequest(BaseModel):
  name: str | None = Field(default=None, min_length=1, max_length=200)
  trade: str | None = Field(default=None, min_length=1, max_length=100)
  cnic: str | None = None
  phone: str | None = None
  default_daily_rate: Decimal | None = Field(default=None, ge=0)
  is_active: bool | None = None

class LabourWorkerResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  source_id: UUID
  name: str
  trade: str
  cnic: str | None
  phone: str | None
  default_daily_rate: Decimal | None
  is_active: bool

class LabourDeploymentCreateRequest(BaseModel):
  source_id: UUID
  worker_id: UUID | None = None
  trade: str = Field(min_length=1, max_length=100)
  daily_rate: Decimal = Field(gt=0)
  start_date: date

class LabourDeploymentUpdateRequest(BaseModel):
  end_date: date | None = None
  status: LabourDeploymentStatus | None = None

class LabourDeploymentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  source_id: UUID
  worker_id: UUID | None
  trade: str
  daily_rate: Decimal
  start_date: date
  end_date: date | None
  status: LabourDeploymentStatus

class AttendanceEntryInput(BaseModel):
  deployment_id: UUID
  attendance_date: date
  units_present: Decimal = Field(ge=0, le=9999)
  notes: str | None = None

class AttendanceBulkCreateRequest(BaseModel):
  entries: list[AttendanceEntryInput] = Field(min_length=1, max_length=500)

class LabourAttendanceResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  deployment_id: UUID
  attendance_date: date
  units_present: Decimal
  notes: str | None

class AttendanceBulkResultResponse(BaseModel):
  created: int
  updated: int
  items: list[LabourAttendanceResponse]

class LabourAdvanceCreateRequest(BaseModel):
  source_id: UUID
  worker_id: UUID | None = None
  amount: Decimal = Field(gt=0)
  advance_date: date
  notes: str | None = None

class LabourAdvanceResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  source_id: UUID
  worker_id: UUID | None
  amount: Decimal
  advance_date: date
  notes: str | None

class LabourPaymentCreateRequest(BaseModel):
  source_id: UUID
  worker_id: UUID | None = None
  period_start: date
  period_end: date
  gross_wage_amount: Decimal = Field(ge=0)
  advance_recovered_amount: Decimal = Field(default=Decimal("0"), ge=0)
  wht_category: "WHTCategory | None" = None
  payment_date: date
  notes: str | None = None

  @model_validator(mode="after")
  def _validate_period(self) -> "LabourPaymentCreateRequest":
    if self.period_end < self.period_start:
      raise ValueError("period_end must be on or after period_start.")
    return self

class LabourPaymentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  source_id: UUID
  worker_id: UUID | None
  period_start: date
  period_end: date
  gross_wage_amount: Decimal
  advance_recovered_amount: Decimal
  wht_category: str | None
  wht_rate_percentage: Decimal | None
  wht_deducted_amount: Decimal
  net_paid_amount: Decimal
  payment_date: date
  notes: str | None

class LabourTradeCostResponse(BaseModel):
  trade: str
  cost: Decimal

class LabourCostResponse(BaseModel):
  period_start: date
  period_end: date
  total_cost: Decimal
  currency: str

class LabourBalanceResponse(BaseModel):
  outstanding_advance_balance: Decimal
  currency: str

class LabourSummaryResponse(BaseModel):
  project_id: UUID
  period_start: date
  period_end: date
  total_accrued_cost: Decimal
  cost_by_trade: list[LabourTradeCostResponse]
  total_advances_given: Decimal
  total_payments_made: Decimal
  outstanding_advance_balance: Decimal
  currency: str

class DayAttendanceSummaryResponse(BaseModel):
  attendance_date: date
  total_present: Decimal
  by_trade: list[LabourTradeCostResponse] 
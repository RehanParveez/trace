from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.modules.bank_guarantees.models import BankGuaranteeHolderType, BankGuaranteePurpose, BankGuaranteeStatus
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime

class BankGuaranteeCreateRequest(BaseModel):
  holder_type: BankGuaranteeHolderType
  project_id: UUID
  boq_version_id: UUID | None = None
  agreement_id: UUID | None = None
  guarantee_number: str = Field(min_length=1, max_length=100)
  issuing_bank: str = Field(min_length=1, max_length=200)
  amount: Decimal = Field(gt=0)
  issue_date: date
  expiry_date: date
  notes: str | None = None

  @model_validator(mode="after")
  def _validate(self) -> "BankGuaranteeCreateRequest":
    if self.holder_type == BankGuaranteeHolderType.CLIENT:
      if self.boq_version_id is None:
        raise ValueError("boq_version_id is required for a client-facing guarantee.")
      if self.agreement_id is not None:
        raise ValueError("agreement_id must not be set for a client-facing guarantee.")
    else:
      if self.agreement_id is None:
        raise ValueError("agreement_id is required for a subcontractor guarantee.")
      if self.boq_version_id is not None:
        raise ValueError("boq_version_id must not be set for a subcontractor guarantee.")
    if self.expiry_date <= self.issue_date:
      raise ValueError("expiry_date must be after issue_date.")
    return self

class BankGuaranteeRenewRequest(BaseModel):
  guarantee_number: str = Field(min_length=1, max_length=100)
  issue_date: date
  expiry_date: date
  amount: Decimal | None = Field(default=None, gt=0)  
  notes: str | None = None

class BankGuaranteeResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  holder_type: BankGuaranteeHolderType
  boq_version_id: UUID | None
  agreement_id: UUID | None
  purpose: BankGuaranteePurpose
  guarantee_number: str
  issuing_bank: str
  amount: Decimal
  currency: str
  issue_date: date
  expiry_date: date
  status: BankGuaranteeStatus
  renewed_from_guarantee_id: UUID | None
  is_expired: bool = False
  is_expiring_soon: bool = False
  notes: str | None
  created_at: datetime

  @model_validator(mode="after")
  def _compute_flags(self) -> "BankGuaranteeResponse":
    from datetime import date as _date
    today = _date.today()
    if self.status == BankGuaranteeStatus.ACTIVE:
      self.is_expired = today > self.expiry_date
      self.is_expiring_soon = not self.is_expired and (self.expiry_date - today).days <= 30
    return self

class ProjectBankGuaranteeSummaryResponse(BaseModel):
  project_id: UUID
  active_count: int
  expiring_soon_count: int
  expired_count: int
  total_active_value: Decimal
  currency: str
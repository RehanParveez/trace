from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

ComponentType = Literal["MATERIAL", "LABOUR", "PLANT", "OTHER"]
ComponentSource = Literal["DIRECT", "RATE_ITEM", "LABOUR_RATE", "MATERIAL_LIBRARY"]

def _clean(value: str | None) -> str | None:
  if value is None:
    return None
  value = value.strip()
  return value or None

class RateBookCreateRequest(BaseModel):
  code: str = Field(min_length=1, max_length=50)
  name: str = Field(min_length=1, max_length=200)
  description: str | None = None
  edition: str | None = Field(default=None, max_length=50)
  currency: str = Field(default="PKR", min_length=3, max_length=3)
  jurisdiction: str | None = Field(default=None, max_length=50)
  province: str | None = Field(default=None, max_length=50)
  city: str | None = Field(default=None, max_length=100)
  effective_from: date | None = None
  effective_to: date | None = None
  copy_from_id: UUID | None = None

  @field_validator("code")
  @classmethod
  def _code(cls, v: str) -> str:
    v = v.strip().upper()
    if not v:
      raise ValueError("code is required")
    return v

  @model_validator(mode="after")
  def _range(self):
    if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
      raise ValueError("effective_to is before effective_from")
    return self

class RateBookUpdateRequest(BaseModel):
  name: str | None = Field(default=None, min_length=1, max_length=200)
  description: str | None = None
  edition: str | None = Field(default=None, max_length=50)
  currency: str | None = Field(default=None, min_length=3, max_length=3)
  jurisdiction: str | None = Field(default=None, max_length=50)
  province: str | None = Field(default=None, max_length=50)
  city: str | None = Field(default=None, max_length=100)
  effective_from: date | None = None
  effective_to: date | None = None

class RateBookResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  organization_id: UUID | None
  code: str
  name: str
  description: str | None = None
  edition: str | None = None
  currency: str
  jurisdiction: str | None = None
  province: str | None = None
  city: str | None = None
  effective_from: date | None = None
  effective_to: date | None = None
  status: str
  immutable_version: int
  published_at: datetime | None = None
  content_hash: str | None = None
  parent_rate_book_id: UUID | None = None
  supersedes_rate_book_id: UUID | None = None
  is_system: bool = False
  item_count: int = 0
  analysis_count: int = 0
  escalation_count: int = 0

class RateItemInput(BaseModel):
  work_item_code: str = Field(min_length=1, max_length=50)
  unit: str = Field(min_length=1, max_length=20)
  rate: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
  description: str | None = Field(default=None, max_length=500)
  trade: str | None = Field(default=None, max_length=80)
  specification: str | None = None
  csr_ref: str | None = Field(default=None, max_length=80)

  @field_validator("work_item_code")
  @classmethod
  def _code(cls, v: str) -> str:
    return v.strip().upper()

  @field_validator("unit")
  @classmethod
  def _unit(cls, v: str) -> str:
    return v.strip().lower()

class RateItemUpdateRequest(BaseModel):
  rate: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
  description: str | None = Field(default=None, max_length=500)
  trade: str | None = Field(default=None, max_length=80)
  specification: str | None = None
  csr_ref: str | None = Field(default=None, max_length=80)
  is_active: bool | None = None

class RateItemBulkRequest(BaseModel):
  items: list[RateItemInput] = Field(min_length=1, max_length=2000)

class RateItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  rate_book_id: UUID
  work_item_code: str
  unit: str
  rate: Decimal
  description: str | None = None
  trade: str | None = None
  specification: str | None = None
  csr_ref: str | None = None
  analysis_id: UUID | None = None
  is_active: bool = True

class ImportResultResponse(BaseModel):
  created: int
  updated: int
  total: int

class EscalationCreateRequest(BaseModel):
  trade_scope: str = Field(default="ALL", min_length=1, max_length=80)
  effective_from: date
  factor: Decimal = Field(gt=0, max_digits=8, decimal_places=4)
  note: str | None = None

  @field_validator("trade_scope")
  @classmethod
  def _scope(cls, v: str) -> str:
    v = v.strip()
    return "ALL" if v.lower() == "all" else v

class EscalationResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  rate_book_id: UUID
  trade_scope: str
  effective_from: date
  factor: Decimal
  note: str | None = None

class AnalysisComponentInput(BaseModel):
  component_type: ComponentType = "MATERIAL"
  description: str = Field(min_length=1, max_length=500)
  work_item_code: str | None = Field(default=None, max_length=50)
  rate_source: ComponentSource = "DIRECT"
  ref_rate_item_id: UUID | None = None
  unit: str = Field(min_length=1, max_length=20)
  coefficient: Decimal = Field(ge=0, max_digits=14, decimal_places=6)
  unit_rate: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

  @model_validator(mode="after")
  def _consistent(self):
    if self.rate_source == "DIRECT" and self.unit_rate is None:
      raise ValueError("a DIRECT component needs unit_rate")
    if self.rate_source == "RATE_ITEM" and self.ref_rate_item_id is None:
      raise ValueError("a RATE_ITEM component needs ref_rate_item_id")
    return self

class AnalysisComponentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  sequence: int
  component_type: str
  description: str
  work_item_code: str | None = None
  rate_source: str
  ref_rate_item_id: UUID | None = None
  unit: str
  coefficient: Decimal
  unit_rate: Decimal | None = None

class AnalysisCreateRequest(BaseModel):
  code: str = Field(min_length=1, max_length=80)
  work_item_code: str = Field(min_length=1, max_length=50)
  description: str = Field(min_length=1, max_length=500)
  unit: str = Field(min_length=1, max_length=20)
  basis_quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=14, decimal_places=4)
  overhead_pct: Decimal = Field(default=Decimal("0"), ge=0, max_digits=6, decimal_places=3)
  profit_pct: Decimal = Field(default=Decimal("0"), ge=0, max_digits=6, decimal_places=3)
  components: list[AnalysisComponentInput] = Field(default_factory=list, max_length=200)

  @field_validator("code", "work_item_code")
  @classmethod
  def _upper(cls, v: str) -> str:
    return v.strip().upper()

  @field_validator("unit")
  @classmethod
  def _unit(cls, v: str) -> str:
    return v.strip().lower()

class AnalysisUpdateRequest(BaseModel):
  description: str | None = Field(default=None, min_length=1, max_length=500)
  unit: str | None = Field(default=None, min_length=1, max_length=20)
  basis_quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)
  overhead_pct: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=3)
  profit_pct: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=3)
  components: list[AnalysisComponentInput] | None = Field(default=None, max_length=200)

class AnalysisResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  rate_book_id: UUID
  code: str
  work_item_code: str
  description: str
  unit: str
  basis_quantity: Decimal
  overhead_pct: Decimal
  profit_pct: Decimal
  computed_rate: Decimal | None = None
  computed_at: datetime | None = None
  is_active: bool = True
  components: list[AnalysisComponentResponse] = Field(default_factory=list)

class AnalysisBreakdownResponse(BaseModel):
  analysis_id: UUID
  lines: list[dict]
  cost_by_type: dict
  cost: str
  overhead: str
  profit: str
  total: str
  basis_quantity: str
  rate: str
  unit: str

class OverrideCreateRequest(BaseModel):
  work_item_code: str = Field(min_length=1, max_length=50)
  unit: str = Field(min_length=1, max_length=20)
  rate: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
  reason: str = Field(min_length=1)
  effective_from: date | None = None
  effective_to: date | None = None

  @field_validator("work_item_code")
  @classmethod
  def _code(cls, v: str) -> str:
    return v.strip().upper()

  @field_validator("unit")
  @classmethod
  def _unit(cls, v: str) -> str:
    return v.strip().lower()

  @field_validator("reason")
  @classmethod
  def _reason(cls, v: str) -> str:
    v = v.strip()
    if not v:
      raise ValueError("reason is required")
    return v

  @model_validator(mode="after")
  def _range(self):
    if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
      raise ValueError("effective_to is before effective_from")
    return self

class OverrideRevokeRequest(BaseModel):
  reason: str = Field(min_length=1)

class OverrideResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  work_item_code: str
  unit: str
  rate: Decimal
  reason: str
  effective_from: date | None = None
  effective_to: date | None = None
  created_by_user_id: UUID | None = None
  created_at: datetime | None = None
  revoked_at: datetime | None = None
  revoked_by_user_id: UUID | None = None
  revoke_reason: str | None = None

class PriceVersionRequest(BaseModel):
  rate_book_ids: list[UUID] | None = Field(default=None, max_length=20)
  as_of: date | None = None
  overwrite_manual: bool = False
  item_ids: list[UUID] | None = Field(default=None, max_length=5000)

class PriceVersionResponse(BaseModel):
  boq_version_id: UUID
  as_of: date
  rate_books: list[dict]
  priced: int
  changed: int
  unpriced: int
  unit_mismatch: int
  skipped_manual: int
  skipped_other: int
  by_source: dict
  total: str
  open_issues: int = 0

class PricingSummaryResponse(BaseModel):
  boq_version_id: UUID
  priced_at: datetime | None = None
  pricing_meta: dict
  item_count: int
  unpriced_count: int
  by_source: dict
  total: str

class RateExplainResponse(BaseModel):
  item_id: UUID
  work_item_code: str | None
  unit: str
  current: dict | None = None
  current_source: str | None = None
  current_unit_rate: Decimal | None = None
  would_resolve_to: dict | None = None
  attempts: list[dict] = Field(default_factory=list)
  stack: list[dict] = Field(default_factory=list)

class DiffLineResponse(BaseModel):
  item_key: str
  status: str
  work_item_code: str | None = None
  material_name: str | None = None
  unit_a: str | None = None
  unit_b: str | None = None
  unit_changed: bool = False
  net_a: Decimal | None = None
  net_b: Decimal | None = None
  quantity_a: Decimal | None = None
  quantity_b: Decimal | None = None
  rate_a: Decimal | None = None
  rate_b: Decimal | None = None
  amount_a: Decimal | None = None
  amount_b: Decimal | None = None
  net_delta: Decimal | None = None
  quantity_delta: Decimal | None = None
  quantity_delta_pct: Decimal | None = None
  rate_delta: Decimal | None = None
  amount_delta: Decimal | None = None
  elements_added: list[dict] = Field(default_factory=list)
  elements_removed: list[dict] = Field(default_factory=list)
  element_counts: dict = Field(default_factory=dict)

class DiffSummaryResponse(BaseModel):
  ADDED: int
  REMOVED: int
  CHANGED: int
  UNCHANGED: int
  total_a: Decimal
  total_b: Decimal
  total_delta: Decimal
  total_delta_pct: Decimal | None = None
  unpriced_a: int
  unpriced_b: int

class DiffResponse(BaseModel):
  version_a_id: UUID
  version_b_id: UUID
  summary: DiffSummaryResponse
  lines: list[DiffLineResponse]
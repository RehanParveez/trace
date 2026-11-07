from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field

class ProfileOption(BaseModel):
  id: str
  label: str

class BillSource(BaseModel):
  element: str
  qty_key: str
  floor: str | None = None
  value: float | None = None
  unit: str
  assumed: bool = False

class BillSpec(BaseModel):
  name: str
  value: str | None = None
  basis: str = Field(description="ANSWER when a decision of the project gave it, ASSUMED when it is the default.")

class BillLineOut(BaseModel):
  code: str
  unit: str
  qty: float | None = None
  spec: BillSpec | None = None
  floor: str | None = None
  sources: list[BillSource] = []

class IncludedOut(BaseModel):
  qty_key: str
  where: str
  value: float | None = None
  unit: str

class RateNeededOut(BaseModel):
  element: str
  qty_key: str
  value: float | None = None
  unit: str
  why: str

class SpecQuestion(BaseModel):
  spec: str
  floor: str | None = None
  default: str | None = None
  question: str

class NotMeasuredOut(BaseModel):
  element: str
  name: str | None = None
  floor: str | None = None
  state: str
  reasons: list[str] = []
  quantity: dict | None = None

class UnavailableOut(BaseModel):
  element: str
  name: str | None = None
  qty: str
  unit: str
  why: str

class BillingCounts(BaseModel):
  measured_entries: int
  assumed_entries: int
  not_measured: int

class RunSource(BaseModel):
  run: dict | None = Field(None, description="The latest completed calculation run the quantities come from; None when the project has none.")
  lines: int = 0
  no_family: int = Field(0, description="Rows of the run that name no line family and are left out.")
  no_unit: list[dict] = []

class BillingResponse(BaseModel):
  project_id: UUID
  has_ledger: bool
  source: RunSource
  profile: str
  profiles: list[ProfileOption]
  lines: list[BillLineOut]
  included: list[IncludedOut]
  rate_needed: list[RateNeededOut]
  questions: list[SpecQuestion]
  not_measured: list[NotMeasuredOut]
  unavailable: list[UnavailableOut]
  counts: BillingCounts
  reconciled: bool = Field(description="True when every measured quantity is in a line, included in another rate or listed as rate needed.")
  lost: dict[str, float | None] = {}

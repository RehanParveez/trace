from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from app.modules.drawings_boq.pricing.billing.schemas import BillingResponse, BillSpec

class PricedLineOut(BaseModel):
  code: str
  description: str | None = None
  unit: str
  qty: float | None = None
  spec: BillSpec | None = None
  floor: str | None = None
  rate: float | None = Field(None, description="The rate per one rate_unit.")
  rate_unit: str | None = None
  amount: float | None = None
  low: float | None = None
  high: float | None = None
  unpriced_why: str | None = None
  assumed_share: float = 0.0
  by_floor: dict[str, float | None] = {}

class PricedTotals(BaseModel):
  grand: float
  measured: float
  assumed: float
  priced: int
  unpriced: int
  by_section: dict[str, float | None] = {}
  by_floor: dict[str, float | None] = {}
  range: dict[str, float | None] | None = None

class RateBookUsed(BaseModel):
  id: UUID
  code: str
  version: int
  edition: str | None = None
  scope: str
  items: int
  content_hash: str | None = None

class MaterialRow(BaseModel):
  code: str
  material: str
  qty: float | None = None
  how: str

class MaterialMissing(BaseModel):
  code: str
  why: str

class MaterialsOut(BaseModel):
  totals: dict[str, float | None] = {}
  rows: list[MaterialRow] = []
  missing: list[MaterialMissing] = []
  coefficient_table: bool = False

class PricedResponse(BillingResponse):
  lines: list[PricedLineOut]
  totals: PricedTotals
  rate_books: list[RateBookUsed]
  rate_notes: list[str]
  materials: MaterialsOut

from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID

class CompareResponse(BaseModel):
  book_a: dict
  book_b: dict
  match_on: str
  counts: dict
  matched: int
  median_change_pct: str | None
  overall_ratio: str | None
  suggested_factors: list[dict]
  lines: list[dict]
  truncated: bool = False

class HistoryResponse(BaseModel):
  work_item_code: str
  unit: str | None
  points: list[dict]

class EscalationFromCompareRequest(BaseModel):
  other_book_id: UUID
  match_on: Literal["csr_ref", "code"] = "code"
  trades: list[str] | None = Field(default=None, max_length=100)
  include_overall: bool = False
  effective_from: date | None = None
  apply: bool = False

class EscalationFromCompareResponse(BaseModel):
  applied: bool
  other: dict
  effective_from: str
  proposals: list[dict]
  created: int

class RefreshRequest(BaseModel):
  source_book_id: UUID
  match_on: Literal["csr_ref", "code"] = "csr_ref"
  trades: list[str] | None = Field(default=None, max_length=100)
  recompute_analyses: bool = True
  apply: bool = False

class RefreshResponse(BaseModel):
  applied: bool
  source: dict
  match_on: str
  updated: int
  unchanged: int
  unmatched: int
  skipped: int
  changes: list[dict]
  unmatched_sample: list[dict]
  analyses: dict

class RateGap(BaseModel):
  work_item_code: str | None
  unit: str
  reason: Literal["NO_CODE", "NO_RATE", "UNIT_MISMATCH"]
  lines: int
  quantity: str
  sample_description: str | None
  available_units: list[str]
  item_ids: list[UUID]

class RateGapsResponse(BaseModel):
  boq_version_id: UUID
  as_of: str
  rate_books: list[dict]
  priced: int
  unpriced: int
  resolvable: int = 0
  gaps: list[RateGap]

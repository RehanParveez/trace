from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class FactIn(BaseModel):
  kind: str = Field(description="TOTAL, COUNT, ROOM_AREA, SLAB_AREA or SCHEDULE.")
  category: str | None = None
  tag: str | None = None
  floor: str | None = None
  count: int | None = Field(default=None, ge=0)
  name: str | None = None
  area_m2: float | None = Field(default=None, gt=0)
  mark: str | None = None
  width_mm: float | None = Field(default=None, gt=0)
  height_mm: float | None = Field(default=None, gt=0)
  tolerance_pct: float | None = Field(default=None, ge=0, le=100)

class FactsCheckRequest(BaseModel):
  facts: list[FactIn] = Field(min_length=1, max_length=200)

class FactResult(BaseModel):
  index: int
  text: str
  status: str = Field(description="PASS (read as you say), FAIL (read, but differently) or MISSING (nothing of the kind was read).")
  expected: object | None = None
  found: object | None = None
  message: str
  pages: list[int] = Field(default_factory=list)

class FactsCheckResponse(BaseModel):
  drawing_id: UUID
  results: list[FactResult]
  passed: int = 0
  failed: int = 0
  missing: int = 0

class TraceRule(BaseModel):
  id: str
  label: str
  basis: str = Field(description="TUNED (thresholds set by looking at one drawing), STANDARD (a standard or common practice) or DEFAULT (a value used because the drawing prints none).")
  items: int = 0
  notes: int = 0
  codes: list[str] = Field(default_factory=list)
  examples: list[str] = Field(default_factory=list)
  thresholds: dict = Field(default_factory=dict)

class TraceScale(BaseModel):
  agreement: str | None = None
  support: int = 0
  trust: float | None = None
  gate: str | None = None
  decided_by: str

class TraceSheet(BaseModel):
  sheet_id: UUID
  page_no: int
  scale: TraceScale
  rules: list[TraceRule]
  silent: list[str] = Field(default_factory=list)

class TraceSummary(BaseModel):
  sheets: int = 0
  tuned_rules_fired: list[str] = Field(default_factory=list)
  default_rules_fired: list[str] = Field(default_factory=list)
  tuned_items: int = 0

class TraceResponse(BaseModel):
  drawing_id: UUID
  sheets: list[TraceSheet]
  summary: TraceSummary
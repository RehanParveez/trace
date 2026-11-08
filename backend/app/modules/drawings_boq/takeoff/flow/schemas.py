from __future__ import annotations
from app.modules.drawings_boq.pricing.priced.schemas import PricedLineOut, PricedResponse
from pydantic import BaseModel
from typing import Literal
from uuid import UUID

class FlowLineOut(PricedLineOut):
  state: str
  label: str
  priced: bool
  measured_amount: float | None = None
  assumed_amount: float | None = None
  low_pct: float | None = None
  high_pct: float | None = None
  elements: list[str] = []
  open_rows: int = 0

class CoverageRow(BaseModel):
  section: str
  MEASURED: int = 0
  ASSUMED: int = 0
  ASKED: int = 0
  NOT_READ: int = 0
  total: int = 0
  with_quantity_pct: float = 0.0

class AssumptionRow(BaseModel):
  input: str
  rule: str | None = None
  value: float | str | None = None
  unit: str | None = None
  range: list[float] | None = None
  source: str | None = None
  items: list[str] = []
  floors: list[str] = []

class FlowBoqResponse(PricedResponse):
  lines: list[FlowLineOut]
  profile_source: Literal["REQUEST", "COMPANY", "DEFAULT"]
  banner: list[str] = []
  open_rows: int = 0
  coverage: list[CoverageRow] = []
  assumptions: list[AssumptionRow] = []

class FlowStep(BaseModel):
  key: str
  state: Literal["DONE", "OPEN", "RUNNING", "FAILED", "READY"]
  detail: str | None = None

class SittingSegment(BaseModel):
  name: str
  start: str
  end: str
  seconds: float | None = None

class SittingStage(BaseModel):
  name: str
  seconds: float
  status: str

class Sitting(BaseModel):
  events: dict[str, str] = {}
  segments: list[SittingSegment] = []
  stages: list[SittingStage] = []
  reader_seconds: float | None = None
  sitting_seconds: float | None = None
  complete: bool = False
  exports: list[dict] = []

class FlowStatus(BaseModel):
  project_id: UUID
  steps: list[FlowStep]
  next: str | None = None
  open_rows: int = 0
  sitting: Sitting
  profile: str
  profile_source: Literal["REQUEST", "COMPANY", "DEFAULT"]
  profiles: list[dict] = []

class SeenRequest(BaseModel):
  step: Literal["review", "boq"]

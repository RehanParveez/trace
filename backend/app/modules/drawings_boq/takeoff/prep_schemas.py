from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from uuid import UUID
from app.modules.drawings_boq.takeoff.schemas import CalibrationResponse, Point, SheetResponse

SnapKind = Literal["ENDPOINT", "INTERSECTION", "MIDPOINT", "EDGE"]

class PrepareRequest(BaseModel):
  sheet_ids: list[UUID] | None = Field(default=None, max_length=300, description="Prepare only these sheets; default is every sheet that needs it.")
  force: bool = False
  budget_seconds: int = Field(default=45, ge=5, le=120, description="Stop starting new pages after this many seconds; call again to continue.")

class PrepareResponse(BaseModel):
  drawing_id: UUID
  prepared: list[UUID]
  skipped: list[UUID]
  failed: list[dict]
  remaining: int
  elapsed_seconds: float
  sheets: list[SheetResponse]

class AnalysisResponse(BaseModel):
  sheet_id: UUID
  prep_status: str
  stale: bool
  content_kind: str
  detected_scale: dict
  meta: dict

class AutoCalibrateRequest(BaseModel):
  use: Literal["RECOMMENDED", "DECLARED", "DIMENSIONS"] = "RECOMMENDED"
  make_default: bool = True
  include_regions: bool = Field(default=False, description="Also create one calibration per extra scale found on a multi-scale sheet.")

class AutoCalibrateResponse(BaseModel):
  calibration: CalibrationResponse
  additional: list[CalibrationResponse] = Field(default_factory=list)
  created: bool
  recommendation: dict
  notes: list[dict] = Field(default_factory=list)

class SnapRequest(BaseModel):
  points: list[Point] = Field(min_length=1, max_length=500)
  radius_pt: float = Field(default=2.0, gt=0, le=25)
  want: list[SnapKind] | None = None

class SnapResult(BaseModel):
  input: list[float]
  snapped: bool
  x: float | None = None
  y: float | None = None
  kind: str | None = None
  distance: float | None = None

class SnapResponse(BaseModel):
  results: list[SnapResult]

class PickRequest(BaseModel):
  point: Point
  radius_pt: float = Field(default=3.0, gt=0, le=25)
  calibration_id: UUID | None = None
  wall: bool = True
  region: bool = True
  label_radius_pt: float = Field(default=30.0, ge=0, le=200)

class PickResponse(BaseModel):
  snap: dict | None = None
  wall: dict | None = None
  region: dict | None = None
  labels: list[dict] = Field(default_factory=list)
  mm_per_pt: str | None = None

class VectorResponse(BaseModel):
  bbox: list[float]
  segments: list[list[float]]
  total: int
  truncated: bool
  note: str = "Each segment is [x1, y1, x2, y2, kind]; kind 0 is a straight line, 1 a curve chord, 2 an arrowhead edge."

class TextResponse(BaseModel):
  total: int
  words: list[dict]
  truncated: bool

class TagSummary(BaseModel):
  tag: str
  count: int
  in_drawing: int

class TagListResponse(BaseModel):
  tags: list[TagSummary]

class CountSuggestion(BaseModel):
  kind: Literal["COUNT"] = "COUNT"
  quantity_mode: Literal["DIRECT"] = "DIRECT"
  geometry: dict
  source: Literal["TAG_SCAN", "VECTOR_SNAP"]
  tag: str | None = None
  label: str

class TagDetailResponse(BaseModel):
  tag: str
  count: int
  in_drawing: int
  points: list[dict]
  suggestion: CountSuggestion
  note: str | None = None

class ShapeSummary(BaseModel):
  id: str
  shape: str
  a_pt: float
  b_pt: float
  a_mm: float | None = None
  b_mm: float | None = None
  count: int
  filled: int

class ShapeListResponse(BaseModel):
  shapes: list[ShapeSummary]
  mm_per_pt: str | None = None

class ShapeDetailResponse(BaseModel):
  shape: ShapeSummary
  points: list[list[float]]
  suggestion: CountSuggestion
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

class DrawingFact(BaseModel):
  kind: str
  scope: str | None = None
  text: str
  count: int
  pages: list[int]
  value_mm: float | None = None
  value2_mm: float | None = None
  value: float | None = None
  unit: str | None = None
  grade: int | None = None
  concrete_class: str | None = None
  mix: str | None = None
  where: str | None = None

class ScheduleOpening(BaseModel):
  mark: str
  type: str
  width_mm: float
  height_mm: float
  area_m2: float
  text: str | None = None
  pages: list[int] = Field(default_factory=list)

class ScheduleArea(BaseModel):
  key: str
  kind: str
  name: str
  value: float
  unit: str
  m2: float
  dims_mm: list[float] | None = None
  dims_text: str | None = None
  pages: list[int] = Field(default_factory=list)

class ScheduleLintel(BaseModel):
  span_max_ft: float
  span_max_mm: float
  width_mm: float
  depth_mm: float
  text: str | None = None
  pages: list[int] = Field(default_factory=list)

class ScheduleTieBand(BaseModel):
  text: str
  pages: list[int] = Field(default_factory=list)

class DrawingSchedule(BaseModel):
  openings: list[ScheduleOpening] = Field(default_factory=list)
  areas: list[ScheduleArea] = Field(default_factory=list)
  lintels: list[ScheduleLintel] = Field(default_factory=list)
  tie_band: ScheduleTieBand | None = None
  conflicts: list[dict] = Field(default_factory=list)

class FloorCheck(BaseModel):
  key: str
  name: str
  covered_m2: float
  status: Literal["OK", "LOW", "HIGH", "NOT_READ"]
  message: str | None = None
  pages: list[int] = Field(default_factory=list)
  rooms: int = 0
  rooms_m2: float = 0.0
  coverage_pct: float | None = None
  doors: int = 0
  windows: int = 0
  ventilators: int = 0
  openings_m2: float = 0.0
  walls_m: float = 0.0
  wall_height_mm: float | None = None
  wall_height_basis: str | None = None
  brick_9_m2: float = 0.0
  brick_45_m2: float = 0.0
  rcc_m2: float = 0.0
  columns: int = 0
  footings: int = 0
  beams: int = 0
  slab_panels: int = 0
  slab_thickness_mm: float | None = None

class StructureMark(BaseModel):
  tag: str | None = None
  count: int = 0
  size_mm: list[float | None] | None = None
  status: str | None = None
  size_source: Literal["SCHEDULE", "DETAIL", "PLAN"] | None = None
  warnings: list[str] = Field(default_factory=list)

class ColumnDetail(BaseModel):
  mark: str
  caption: str | None = None
  page_no: int | None = None
  read: Literal["OCR", "OCR_SQUARE", "PARTIAL", "NONE", "TIMEOUT"] = "NONE"
  w_in: float | None = None
  h_in: float | None = None

class DrawingCheck(BaseModel):
  code: str
  severity: Literal["warning", "info"]
  title: str
  message: str
  marks: list[str] = Field(default_factory=list)
  pages: list[int] = Field(default_factory=list)

class StructureLevel(BaseModel):
  key: str
  name: str
  columns: int = 0
  footings: int = 0
  beams: int = 0
  column_marks: list[StructureMark] = Field(default_factory=list)
  footing_marks: list[StructureMark] = Field(default_factory=list)
  beam_marks: list[StructureMark] = Field(default_factory=list)
  slab_panels: int = 0
  slab_thickness_mm: float | None = None
  pages: list[int] = Field(default_factory=list)

class SheetView(BaseModel):
  page_no: int
  key: str
  kind: str | None = None
  caption: str | None = None
  level_hint: str | None = None
  structural: bool = False
  foundation: bool = False
  scale_ratio: float | None = None
  scale_support: int | None = None
  slab_note_mm: float | None = None
  slab_panels: int = 0

class FactsResponse(BaseModel):
  drawing_id: UUID
  sheets_read: int
  sheets_total: int
  items: list[DrawingFact]
  conflicts: list[dict]
  ladder: dict
  storeys: dict | None = None
  suggest: dict = Field(default_factory=dict)
  schedule: DrawingSchedule = Field(default_factory=DrawingSchedule)
  floors: list[FloorCheck] = Field(default_factory=list)
  views: list[SheetView] = Field(default_factory=list)
  structure: list[StructureLevel] = Field(default_factory=list)
  details: list[ColumnDetail] = Field(default_factory=list)
  details_reader: str | None = None
  checks: list[DrawingCheck] = Field(default_factory=list)

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
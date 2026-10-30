from __future__ import annotations
from typing import Annotated, Literal
from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field, model_validator
from decimal import Decimal
from uuid import UUID
from datetime import datetime

Coord = Annotated[float, Field(allow_inf_nan=False)]
Point = Annotated[list[Coord], Field(min_length=2, max_length=2)]
LengthUnit = Literal["mm", "cm", "m", "ft", "in"]
ContentKind = Literal["VECTOR", "RASTER", "UNKNOWN"]
Kind = Literal["LENGTH", "AREA", "COUNT"]
ReconMode = Literal["AUTO", "ADD", "REPLACE_MODEL", "VERIFY_ONLY"]
Source = Literal["MANUAL", "VECTOR_SNAP", "TAG_SCAN", "PRINTED"]

class KnownDistance(BaseModel):
  p1: Point
  p2: Point
  value: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
  unit: LengthUnit = "mm"

class SheetResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  drawing_id: UUID
  page_no: int
  width_pt: Decimal
  height_pt: Decimal
  rotation: int
  content_kind: str
  label: str | None
  level_id: UUID | None
  scale_text: str | None
  detected_scale: dict = Field(default_factory=dict)
  prep_status: str
  prep_error: str | None
  text_chars: int | None
  vector_ops: int | None
  identity: dict | None = Field(default=None, validation_alias=AliasChoices("identity", AliasPath("prep_meta", "identity")))
  created_at: datetime
  updated_at: datetime

IdentityDiscipline = Literal["ARCHITECTURAL", "STRUCTURAL", "ELECTRICAL", "PLUMBING", "HVAC", "FIRE", "GAS", "SITE"]
IdentityRole = Literal["PLAN", "STRUCTURAL", "COMPOSITE", "SECTION", "ELEVATION", "DETAIL", "SCHEDULE", "SITE", "LEGEND", "SPEC", "COVER", "DIVIDER", "UNKNOWN"]
IdentityPlanKind = Literal["WORKING", "FURNITURE", "OVERLAY", "FRAMING", "FOUNDATION"]
IdentityFloor = Literal["BASEMENT", "GROUND", "FIRST", "SECOND", "THIRD", "FOURTH", "MEZZANINE", "ROOF", "FOUNDATION", "TYPICAL"]
IdentityReadAs = Literal["PLAN_ITEMS", "SYMBOLS_ONLY", "DETAILS_ONLY", "SKIP"]
IdentitySheetType = Literal["PLAN", "POINTS_PLAN", "SECTION", "ELEVATION", "DETAIL", "SCHEDULE", "LEGEND", "SPEC"]

class SheetIdentityOverride(BaseModel):
  discipline: IdentityDiscipline | None = None
  sheet_type: IdentitySheetType | None = None
  role: IdentityRole | None = None
  plan_kind: IdentityPlanKind | None = None
  floor: IdentityFloor | None = None
  read_as: IdentityReadAs | None = None

class SheetUpdateRequest(BaseModel):
  label: str | None = Field(default=None, max_length=200)
  level_id: UUID | None = None
  scale_text: str | None = Field(default=None, max_length=60)
  content_kind: ContentKind | None = None
  identity: SheetIdentityOverride | None = None

class CalibrationCreateRequest(BaseModel):
  method: Literal["TWO_POINT", "SCALE_RATIO"]
  reference: KnownDistance | None = None
  scale_text: str | None = Field(default=None, max_length=60, description='Printed scale, e.g. "1:100" or 1/8" = 1\'-0"')
  ratio: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)
  check: KnownDistance | None = None
  label: str | None = Field(default=None, max_length=120)
  make_default: bool = True

  @model_validator(mode="after")
  def _shape(self):
    if self.method == "TWO_POINT" and self.reference is None:
      raise ValueError("TWO_POINT calibration needs a reference (two points and the real distance).")
    if self.method == "SCALE_RATIO" and self.ratio is None and not (self.scale_text or "").strip():
      raise ValueError("SCALE_RATIO calibration needs a ratio or a scale text.")
    return self

class CalibrationUpdateRequest(BaseModel):
  reference: KnownDistance | None = None
  scale_text: str | None = Field(default=None, max_length=60)
  ratio: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)
  check: KnownDistance | None = None
  label: str | None = Field(default=None, max_length=120)

class CalibrationResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  sheet_id: UUID
  method: str
  ref: dict
  check_ref: dict | None
  ratio: Decimal | None
  label: str | None
  is_default: bool
  usable: bool
  reason: str | None
  mm_per_pt: Decimal | None
  check_error_pct: Decimal | None
  baseline_pt: Decimal | None
  quality_factor: Decimal
  warnings: list = Field(default_factory=list)
  created_at: datetime
  updated_at: datetime
  measurements_recomputed: int = 0
  measurements_reverted_to_draft: int = 0

class OpeningParam(BaseModel):
  role: Literal["DOOR", "WINDOW", "OPENING"] = "OPENING"
  width_mm: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
  height_mm: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
  nos: int = Field(default=1, ge=1, le=10000)
  label: str | None = Field(default=None, max_length=120)
  deduct: bool | None = Field(default=None, description="Whether this opening comes off the wall, decided when the sheet was read (IS 1200 rules per work item). None: the measuring rule set decides.")

class AdjustmentParam(BaseModel):
  op: Literal["LESS", "ADD"]
  value: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
  label: str | None = Field(default=None, max_length=120)

def _one_size(m):
  if (m.bar is None) == (m.dia_mm is None):
    raise ValueError("give either a bar number or a diameter in millimetres")
  return m

class BarGroupParam(BaseModel):
  n: int = Field(ge=1, le=30)
  bar: int | None = Field(default=None, ge=2, le=12, description="Bar number: the diameter in eighths of an inch.")
  dia_mm: Decimal | None = Field(default=None, ge=6, le=40, max_digits=6, decimal_places=2, description="Diameter of a metric bar.")
  _check = model_validator(mode="after")(_one_size)

class RingParam(BaseModel):
  bar: int | None = Field(default=None, ge=2, le=12)
  dia_mm: Decimal | None = Field(default=None, ge=6, le=40, max_digits=6, decimal_places=2)
  spacing_mm: Decimal = Field(gt=0, le=1000, max_digits=9, decimal_places=2)
  dense_spacing_mm: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=9, decimal_places=2, description="Closer spacing at the ends of a member.")
  dense_zone_mm: Decimal | None = Field(default=None, gt=0, le=3000, max_digits=9, decimal_places=2, description="How far from each end the closer spacing runs.")
  _check = model_validator(mode="after")(_one_size)

class MeshAcrossParam(BaseModel):
  bar: int | None = Field(default=None, ge=2, le=12)
  dia_mm: Decimal | None = Field(default=None, ge=6, le=40, max_digits=6, decimal_places=2)
  spacing_mm: Decimal = Field(gt=0, le=1000, max_digits=9, decimal_places=2)
  _check = model_validator(mode="after")(_one_size)

class MeshParam(BaseModel):
  bar: int | None = Field(default=None, ge=2, le=12)
  dia_mm: Decimal | None = Field(default=None, ge=6, le=40, max_digits=6, decimal_places=2)
  spacing_mm: Decimal = Field(gt=0, le=1000, max_digits=9, decimal_places=2)
  ways: Literal[1, 2] = 2
  layers: Literal[1, 2] = 1
  layer: Literal["top", "bottom"] | None = None
  across: MeshAcrossParam | None = Field(default=None, description="The bar and spacing of the second way where it differs from the first (a tank wall: horizontal and vertical bars).")
  _check = model_validator(mode="after")(_one_size)

class SteelParam(BaseModel):
  bottom: BarGroupParam | None = None
  top: BarGroupParam | None = None
  bars: BarGroupParam | None = None
  vertical: BarGroupParam | None = None
  extra: BarGroupParam | None = None
  ring: RingParam | None = None
  mesh: MeshParam | None = None
  slab_mesh: MeshParam | None = Field(default=None, description="A tank: the mesh of the top and bottom slabs. The mesh above is that of the walls.")

class RoofParam(BaseModel):
  fall_mm: Decimal | None = Field(default=None, gt=0, le=1000, description="Average thickness of the coba that gives the roof its fall, from the thin and the thick end printed on the drawing.")
  fall_min_mm: Decimal | None = Field(default=None, gt=0, le=1000)
  fall_max_mm: Decimal | None = Field(default=None, gt=0, le=1000)
  edge_m: Decimal | None = Field(default=None, gt=0, le=2000, description="Length of the roof edge, where the parapet stands and the membrane turns up.")

class MeasurementParams(BaseModel):
  height_mm: Decimal | None = Field(default=None, gt=0)
  thickness_mm: Decimal | None = Field(default=None, gt=0)
  width_mm: Decimal | None = Field(default=None, gt=0)
  depth_mm: Decimal | None = Field(default=None, gt=0)
  length_mm: Decimal | None = Field(default=None, gt=0)
  openings: list[OpeningParam] = Field(default_factory=list, max_length=200)
  adjustments: list[AdjustmentParam] = Field(default_factory=list, max_length=50)
  repeat: int = Field(default=1, ge=1, le=1000)
  dims_basis: Literal["DRAWN", "SPECIFIED", "ASSUMED"] = "DRAWN"
  steel: SteelParam | None = None
  member: Literal["foundation", "frame", "wall", "pile"] | None = None
  roof: RoofParam | None = None

class MeasurementCreateRequest(BaseModel):
  kind: Kind
  quantity_mode: str = Field(default="DIRECT", max_length=40)
  geometry: dict
  params: MeasurementParams = Field(default_factory=MeasurementParams)
  calibration_id: UUID | None = None
  work_item_code: str | None = Field(default=None, max_length=50)
  level_id: UUID | None = None
  label: str | None = Field(default=None, max_length=200)
  tag: str | None = Field(default=None, max_length=60)
  material_grade: str | None = Field(default=None, max_length=50)
  recon_mode: ReconMode = "AUTO"
  source: Source = "MANUAL"
  role: str = Field(default="", max_length=24)

class MeasurementUpdateRequest(BaseModel):
  quantity_mode: str | None = Field(default=None, max_length=40)
  geometry: dict | None = None
  params: MeasurementParams | None = None
  calibration_id: UUID | None = None
  work_item_code: str | None = Field(default=None, max_length=50)
  level_id: UUID | None = None
  label: str | None = Field(default=None, max_length=200)
  tag: str | None = Field(default=None, max_length=60)
  material_grade: str | None = Field(default=None, max_length=50)
  recon_mode: ReconMode | None = None

class MeasurementResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  sheet_id: UUID
  project_id: UUID
  calibration_id: UUID | None
  kind: str
  quantity_mode: str
  geometry: dict
  params: dict
  work_item_code: str | None
  level_id: UUID | None
  label: str | None
  tag: str | None
  material_grade: str | None
  recon_mode: str
  source: str
  status: str
  geometry_hash: str | None
  computed: dict | None
  last_result: dict | None
  confirmed_at: datetime | None
  created_at: datetime
  updated_at: datetime

class PreviewRequest(BaseModel):
  sheet_id: UUID
  kind: Kind
  quantity_mode: str = Field(default="DIRECT", max_length=40)
  geometry: dict
  params: MeasurementParams = Field(default_factory=MeasurementParams)
  calibration_id: UUID | None = None
  source: Source = "MANUAL"
  rule_set_code: str | None = Field(default=None, max_length=60)

class PreviewResponse(BaseModel):
  ok: bool
  quantity: str | None = None
  unit: str | None = None
  formula: str | None = None
  confidence: str | None = None
  uncertainty_pct: str | None = None
  warnings: list[str] = Field(default_factory=list)
  steps: list[dict] = Field(default_factory=list)
  inputs: dict = Field(default_factory=dict)
  error: dict | None = None

class BulkConfirmRequest(BaseModel):
  ids: list[UUID] = Field(min_length=1, max_length=500)

class BulkConfirmResponse(BaseModel):
  confirmed: list[UUID]
  failed: list[dict]

class TakeoffOverviewResponse(BaseModel):
  drawing_id: UUID
  sheets: list[SheetResponse]
  calibrations: list[CalibrationResponse]
  measurements: list[MeasurementResponse]
  summary: dict

class ModeOption(BaseModel):
  kind: str
  quantity_mode: str
  output_unit: str
  required_params: list[str]
  formula_code: str

class ReconciliationResponse(BaseModel):
  run_id: UUID | None
  stats: dict
  measurements: list[dict]

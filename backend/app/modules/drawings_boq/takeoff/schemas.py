from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from decimal import Decimal
from uuid import UUID
from datetime import datetime

Coord = Annotated[float, Field(allow_inf_nan=False)]
Point = Annotated[list[Coord], Field(min_length=2, max_length=2)]
LengthUnit = Literal["mm", "cm", "m", "ft", "in"]
ContentKind = Literal["VECTOR", "RASTER", "UNKNOWN"]
Kind = Literal["LENGTH", "AREA", "COUNT"]
ReconMode = Literal["AUTO", "ADD", "REPLACE_MODEL", "VERIFY_ONLY"]
Source = Literal["MANUAL", "VECTOR_SNAP", "TAG_SCAN"]

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
  created_at: datetime
  updated_at: datetime

class SheetUpdateRequest(BaseModel):
  label: str | None = Field(default=None, max_length=200)
  level_id: UUID | None = None
  scale_text: str | None = Field(default=None, max_length=60)
  content_kind: ContentKind | None = None

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

class AdjustmentParam(BaseModel):
  op: Literal["LESS", "ADD"]
  value: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
  label: str | None = Field(default=None, max_length=120)

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
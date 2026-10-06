from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from decimal import Decimal
from datetime import datetime

Surface = Literal["FLOOR", "WALL", "CEILING", "SKIRTING", "DADO"]
ScheduleKind = Literal["DOOR", "WINDOW", "FINISH", "FIXTURE", "GENERAL"]
RowDecision = Literal["PENDING", "CONFIRMED", "REJECTED"]

class SpaceResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  drawing_id: UUID | None
  level_id: UUID | None
  source: str
  ifc_global_id: str | None
  number: str | None
  name: str | None
  long_name: str | None
  category: str
  usage_text: str | None
  is_external: bool
  is_active: bool
  gross_floor_area_mm2: Decimal | None
  net_floor_area_mm2: Decimal | None
  perimeter_mm: Decimal | None
  height_mm: Decimal | None
  geometry_kind: str
  normalization_status: str
  normalization_issues: list[dict] = Field(default_factory=list)
  finish_count: int = 0
  boundary_count: int = 0

class SpaceFinishResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  space_id: UUID
  surface: str
  work_item_code: str
  finish_name: str | None
  height_mm: Decimal | None
  source: str
  schedule_row_id: UUID | None
  confidence: Decimal
  review_status: str
  is_active: bool

class BoundaryResponse(BaseModel):
  element_id: UUID
  name: str | None
  ifc_type: str
  structural_role: str | None
  boundary_kind: str
  side: str
  source: str

class SpaceDetailResponse(SpaceResponse):
  boundaries: list[BoundaryResponse] = Field(default_factory=list)
  finishes: list[SpaceFinishResponse] = Field(default_factory=list)

class SpaceCreateRequest(BaseModel):
  number: str | None = Field(default=None, max_length=100)
  name: str | None = Field(default=None, max_length=300)
  long_name: str | None = Field(default=None, max_length=500)
  usage_text: str | None = Field(default=None, max_length=300)
  category: str = Field(default="UNKNOWN", max_length=40)
  level_id: UUID | None = None
  is_external: bool = False
  floor_area_m2: Decimal | None = Field(default=None, gt=0)
  perimeter_m: Decimal | None = Field(default=None, gt=0)
  height_m: Decimal | None = Field(default=None, gt=0)

class SpaceUpdateRequest(BaseModel):
  number: str | None = Field(default=None, max_length=100)
  name: str | None = Field(default=None, max_length=300)
  long_name: str | None = Field(default=None, max_length=500)
  usage_text: str | None = Field(default=None, max_length=300)
  category: str | None = Field(default=None, max_length=40)
  level_id: UUID | None = None
  is_external: bool | None = None
  is_active: bool | None = None
  floor_area_m2: Decimal | None = Field(default=None, gt=0)
  perimeter_m: Decimal | None = Field(default=None, gt=0)
  height_m: Decimal | None = Field(default=None, gt=0)

class SpaceBoundariesRequest(BaseModel):
  element_ids: list[UUID] = Field(max_length=500)

class SpaceFinishCreateRequest(BaseModel):
  surface: Surface
  work_item_code: str = Field(min_length=1, max_length=50)
  finish_name: str | None = Field(default=None, max_length=200)
  height_mm: Decimal | None = Field(default=None, gt=0)

class FinishPreviewLine(BaseModel):
  surface: str
  work_item_code: str
  unit: str
  quantity: Decimal
  confidence: Decimal
  formula_code: str
  source_kind: str
  warnings: list[str]
  steps: list[dict]

class FinishPreviewResponse(BaseModel):
  space_id: UUID
  rule_set_code: str
  resolved: list[dict]
  lines: list[FinishPreviewLine]
  skipped: dict

class ScheduleRowResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  schedule_import_id: UUID
  row_no: int
  schedule_kind: str
  page_no: int | None
  raw_text: str | None
  mark: str | None
  description: str | None
  location_text: str | None
  level_id: UUID | None
  space_id: UUID | None
  unit: str | None
  quantity: Decimal | None
  width_mm: Decimal | None
  height_mm: Decimal | None
  work_item_code: str | None
  canonical_unit: str | None
  canonical_quantity: Decimal | None
  confidence: Decimal
  review_status: str
  review_note: str | None
  matched_element_count: int
  surface: str | None = None
  finish_name: str | None = None
  notes: list[str] = Field(default_factory=list)
  quantity_defaulted: bool = False

class ScheduleImportResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  drawing_id: UUID | None
  source: str
  schedule_kind: str
  status: str
  file_name: str | None
  row_count: int
  confirmed_count: int
  notes: str | None
  extraction_meta: dict
  created_at: datetime
  confirmed_at: datetime | None

class ScheduleImportDetailResponse(ScheduleImportResponse):
  rows: list[ScheduleRowResponse]
  summary: dict

class ScheduleFromPdfRequest(BaseModel):
  drawing_id: UUID
  schedule_kind: ScheduleKind
  notes: str | None = Field(default=None, max_length=2000)
  method: Literal["AUTO", "TEXT", "AI"] = "AUTO"

class ScheduleManualCreateRequest(BaseModel):
  schedule_kind: ScheduleKind
  notes: str | None = Field(default=None, max_length=2000)

class ScheduleRowCreateRequest(BaseModel):
  mark: str | None = Field(default=None, max_length=100)
  description: str | None = Field(default=None, max_length=500)
  location_text: str | None = Field(default=None, max_length=300)
  level_id: UUID | None = None
  space_id: UUID | None = None
  unit: str | None = Field(default=None, max_length=20)
  quantity: Decimal | None = Field(default=None, ge=0)
  width_mm: Decimal | None = Field(default=None, gt=0)
  height_mm: Decimal | None = Field(default=None, gt=0)
  work_item_code: str | None = Field(default=None, max_length=50)
  surface: Surface | None = None
  finish_name: str | None = Field(default=None, max_length=200)

class ScheduleRowUpdateRequest(ScheduleRowCreateRequest):
  review_status: RowDecision | None = None
  review_note: str | None = Field(default=None, max_length=1000)

class BulkReviewRequest(BaseModel):
  row_ids: list[UUID] = Field(min_length=1, max_length=1000)
  review_status: RowDecision

class BulkReviewResponse(BaseModel):
  updated: int
  failed: list[dict]

class ConfirmImportRequest(BaseModel):
  reject_pending: bool = False

class NoteRequest(BaseModel):
  note: str | None = Field(default=None, max_length=1000)

class ConfirmImportResponse(BaseModel):
  schedule_import: ScheduleImportResponse
  finishes_created: int
  finishes_updated: int
  finish_conflicts: list[dict]
  ledger_lines: int
  model_matched_rows: int
  unlinked_finish_rows: int
  count_mismatches: list[dict]
  rerun_recommended: bool
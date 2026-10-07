from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.drawings_boq.models import BOQItemStatus, BOQItemType, BOQVersionStatus, DrawingFormat, DrawingStatus, BOQItemRateSource
from typing import Literal

class DrawingResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  original_filename: str
  format: DrawingFormat
  status: DrawingStatus
  file_size_bytes: int
  error_message: str | None
  parsed_at: datetime | None
  created_at: datetime
  revision_group_id: UUID
  revision_label: str | None
  is_current_revision: bool
  superseded_at: datetime | None
  ingestion_meta: dict
  latest_audit_id: UUID | None

class DrawingElementResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  ifc_global_id: str | None
  ifc_type: str
  name: str | None
  raw_material_text: str | None
  unit: str | None
  quantity: Decimal
  properties: dict
  discipline: str | None = None
  structural_role: str | None = None
  classification_source: str | None = None
  classification_confidence: Decimal | None = None
  quantity_source: str | None = None
  level_id: UUID | None = None
  length_mm: Decimal | None = None
  width_mm: Decimal | None = None
  height_mm: Decimal | None = None
  thickness_mm: Decimal | None = None
  elevation_base_mm: Decimal | None = None
  elevation_top_mm: Decimal | None = None
  area_mm2: Decimal | None = None
  volume_mm3: Decimal | None = None
  geometry_kind: str | None = None
  normalization_status: str = "PENDING"
  normalization_issues: list[dict] = Field(default_factory=list)

class BOQVersionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  drawing_id: UUID | None
  label: str
  created_at: datetime
  status: BOQVersionStatus
  covered_area_sqft: Decimal | None
  export_meta: dict
  lifecycle: str = "DRAFT"
  origin: str = "LEGACY"
  calculation_run_id: UUID | None = None
  snapshot_id: UUID | None = None
  rule_set_id: UUID | None = None
  audit_score: Decimal | None = None
  approved_at: datetime | None = None
  issued_at: datetime | None = None
  
class ProjectBOQCountResponse(BaseModel):
  project_id: UUID
  latest_boq_item_count: int

class BOQItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  boq_version_id: UUID
  drawing_element_id: UUID | None
  material_name: str
  category: str | None
  unit: str
  quantity: Decimal
  unit_rate: Decimal | None
  rate_source: str | None
  status: BOQItemStatus
  version: int
  approved_at: datetime | None
  item_type: BOQItemType
  created_by_user_id: UUID | None
  work_item_code: str | None = None
  description: str | None = None
  net_quantity: Decimal | None = None
  adjustment_total: Decimal = Decimal("0")
  gross_quantity: Decimal | None = None
  waste_factor_applied: Decimal | None = None
  confidence: Decimal | None = None
  review_status: str = "OK"
  source_kind: str = "LEGACY"
  is_manual: bool = False
  canonical_unit: str | None = None
  unit_factor: Decimal | None = None
  level_id: UUID | None = None
  item_key: str | None = None
  calculation_run_id: UUID | None = None

class BOQItemUpdateRequest(BaseModel):
  version: int = Field(
    ...,
    description="Version last read by the client; enforces optimistic locking.",
  )
  material_name: str | None = Field(
    default=None,
    min_length=1,
    max_length=300,
  )
  category: str | None = Field(
    default=None,
    max_length=150,
  )
  unit: str | None = Field(
    default=None,
    min_length=1,
    max_length=20,
  )
  quantity: Decimal | None = None
  
  adjustment_reason: str | None = Field(
      default=None, max_length=2000,
      description="Required when changing the quantity of an engine-calculated line.",
  )
  unit_rate: Decimal | None = None
  save_as_library_default: bool = Field(
    default=False,
    description="If true and unit_rate is set, save this rate as the org's default for this material going forward.",
  )
  adjustment_reason: str | None = Field(default=None, max_length=1000)

class MaterialLibraryCreateRequest(BaseModel):
  raw_text: str = Field(
    min_length=1,
    max_length=300,
  )
  normalized_name: str = Field(
    min_length=1,
    max_length=300,
  )
  category: str | None = Field(
    default=None,
    max_length=150,
  )
  default_unit: str | None = Field(
    default=None,
    max_length=20,
  )
  default_rate: Decimal | None = None

class MaterialLibraryResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  raw_text: str
  normalized_name: str
  category: str | None
  default_unit: str | None
  default_rate: Decimal | None
  
class PDFExtractionResultResponse(BaseModel):
  boq_version_id: UUID
  created_item_count: int
  items: list[BOQItemResponse]
  
class MaterialLibraryUpdateRequest(BaseModel):
  normalized_name: str | None = Field(default=None, min_length=1, max_length=300)
  category: str | None = Field(default=None, max_length=150)
  default_unit: str | None = Field(default=None, max_length=20)
  default_rate: Decimal | None = None

class LabourRateCreateRequest(BaseModel):
  trade: str = Field(min_length=1, max_length=150)
  unit: str = Field(min_length=1, max_length=20)
  rate: Decimal

class LabourRateUpdateRequest(BaseModel):
  trade: str | None = Field(default=None, min_length=1, max_length=150)
  unit: str | None = Field(default=None, min_length=1, max_length=20)
  rate: Decimal | None = None

class LabourRateResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  trade: str
  unit: str
  rate: Decimal

class BOQCustomItemCreateRequest(BaseModel):
  material_name: str = Field(min_length=1, max_length=300)
  category: str | None = Field(default=None, max_length=150)
  unit: str = Field(min_length=1, max_length=20)
  quantity: Decimal
  unit_rate: Decimal | None = None

class BOQVersionUpdateRequest(BaseModel):
  covered_area_sqft: Decimal | None = None
  export_meta: dict | None = None
  
class BOQVersionCreateRequest(BaseModel):
  label: str = Field(min_length=1, max_length=200)

class BOQSummaryResponse(BaseModel):
  boq_version_id: UUID
  materials_total: Decimal
  labour_total: Decimal
  custom_total: Decimal
  grand_total: Decimal
  cost_per_sqft: Decimal | None
  covered_area_sqft: Decimal | None
  amount_in_words: str
  unpriced_item_count: int
  unapproved_item_count: int
  item_count: int
  
class BuildingLevelResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  elevation_mm: Decimal | None
  ifc_storey_id: str | None
  sequence: int

class ModelAuditResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  drawing_id: UUID
  overall_score: Decimal
  issues: list[dict]
  element_count: int
  missing_material_count: int
  zero_quantity_count: int
  unclassified_proxy_count: int
  extra_stats: dict
  created_at: datetime
  
class CalculationRunCreateRequest(BaseModel):
  drawing_ids: list[UUID] | None = None
  rule_set_code: str | None = Field(default=None, max_length=50)
  convention_code: str | None = Field(default=None, max_length=80)

class CalculationRunResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  rule_set_id: UUID
  convention_code: str | None
  drawing_revision_ids: list[UUID]
  engine_version: str
  fingerprint: str
  status: str
  progress_pct: int
  started_at: datetime | None
  completed_at: datetime | None
  error_code: str | None
  error_message: str | None
  stats: dict
  created_at: datetime

class RunStageResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  stage: str
  status: str
  attempt: int
  started_at: datetime | None
  finished_at: datetime | None
  counts: dict
  error: str | None

class QuantitySolidResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  element_id: UUID | None
  level_id: UUID | None
  role: str
  component_type: str
  geometry_kind: str
  gross_volume_m3: Decimal | None
  gross_area_m2: Decimal | None
  gross_length_m: Decimal | None
  count: int | None
  status: str
  issues: list[dict]

class LedgerRowResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  solid_id: UUID
  element_id: UUID | None
  level_id: UUID | None
  work_item_code: str
  quantity_net: Decimal
  unit: str
  material_grade: str | None
  source_kind: str
  confidence: Decimal
  formula_code: str
  trace: dict
  warnings: list
  engine_version: str
  
class DeductionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  from_solid_id: UUID
  to_solid_id: UUID | None
  deduction_type: str
  quantity: Decimal
  unit: str
  rule_code: str
  rule_version: str | None
  geometry: dict
  explanation: str | None
  engine_version: str
  
class AdjustmentCreateRequest(BaseModel):
  kind: Literal["DELTA", "REPLACE"]
  value: Decimal
  reason: str = Field(min_length=1, max_length=1000)

class ReasonRequest(BaseModel):
  reason: str = Field(min_length=1, max_length=1000)

class AdjustmentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  boq_item_id: UUID
  kind: str
  value: Decimal
  reason: str
  created_by_user_id: UUID | None
  created_at: datetime
  revoked_at: datetime | None
  revoke_reason: str | None

class TransitionRequest(BaseModel):
  note: str | None = Field(default=None, max_length=1000)

class BOQBuildResponse(BaseModel):
  boq_version_id: UUID
  items_created: int
  items_updated: int
  items_removed: int
  orphaned_items: int
  open_issues: int

class ReviewIssueResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  boq_version_id: UUID | None
  boq_item_id: UUID | None
  drawing_element_id: UUID | None
  code: str
  severity: str
  blocks: str
  message: str
  suggested_fix: str | None
  details: dict
  status: str
  resolution_note: str | None
  resolved_at: datetime | None
  created_at: datetime

class ReviewIssueUpdateRequest(BaseModel):
  status: Literal["RESOLVED", "WAIVED"]
  note: str | None = Field(default=None, max_length=1000)

class SnapshotResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  boq_version_id: UUID
  version_no: int
  purpose: str
  content_hash: str
  item_count: int
  totals: dict
  rule_set_code: str | None
  rule_set_version: int | None
  convention_code: str | None
  engine_version: str | None
  note: str | None
  created_at: datetime

class SnapshotItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  line_no: int
  source_item_id: UUID | None
  work_item_code: str | None
  material_name: str
  description: str | None
  item_type: str
  unit: str
  net_quantity: Decimal | None
  adjustment_total: Decimal
  quantity: Decimal
  gross_quantity: Decimal | None
  unit_rate: Decimal | None
  amount: Decimal | None
  confidence: Decimal | None
  review_status: str
  source_kind: str
  ledger_row_count: int
  ledger_hash: str | None

class ItemTraceResponse(BaseModel):
  item: BOQItemResponse
  ledger: list[LedgerRowResponse]
  deductions: list[DeductionResponse]
  adjustments: list[AdjustmentResponse]
  bar_marks: list[BarMarkResponse] = Field(default_factory=list)
  
class RebarShapeResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  code: str
  name: str
  description: str | None
  standard: str | None
  segments: list
  bend_spec: list
  bend_count: int
  hook_ends: int
  is_system: bool
  is_active: bool

class RebarShapeCreateRequest(BaseModel):
  code: str = Field(min_length=1, max_length=40)
  name: str = Field(min_length=1, max_length=200)
  description: str | None = None
  standard: str | None = Field(default=None, max_length=60)
  segments: list = Field(default_factory=list)
  bend_spec: list = Field(default_factory=list)
  hook_ends: int = Field(default=0, ge=0)

class BarSizeResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  standard: str
  designation: str
  grade: str
  nominal_dia_mm: Decimal
  unit_weight_kg_m: Decimal
  is_system: bool
  is_active: bool

class BarSizeCreateRequest(BaseModel):
  standard: str = Field(min_length=1, max_length=60)
  designation: str = Field(min_length=1, max_length=20)
  grade: str = Field(default="ALL", max_length=30)
  nominal_dia_mm: Decimal = Field(gt=0)
  unit_weight_kg_m: Decimal = Field(gt=0)

class ReinforcementRuleResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  rule_set_id: UUID
  element_scope: str
  bar_role: str
  lap_basis: str | None
  lap_coefficient: Decimal | None
  hook_rules: dict
  bend_rules: dict
  dev_length_method: str | None
  splice_constraints: dict
  stock_length_mm: Decimal | None
  cover_mm: Decimal | None
  min_lap_mm: Decimal | None
  use_couplers: bool
  weight_tolerance_pct: Decimal

class ReinforcementRuleUpsertRequest(BaseModel):
  element_scope: str = Field(default="ALL", max_length=50)
  bar_role: str = Field(min_length=1, max_length=50)
  lap_basis: str | None = Field(default=None, max_length=30)
  lap_coefficient: Decimal | None = Field(default=None, ge=0)
  hook_rules: dict = Field(default_factory=dict)
  bend_rules: dict = Field(default_factory=dict)
  dev_length_method: str | None = Field(default=None, max_length=40)
  splice_constraints: dict = Field(default_factory=dict)
  stock_length_mm: Decimal | None = Field(default=None, gt=0)
  cover_mm: Decimal | None = Field(default=None, ge=0)
  min_lap_mm: Decimal | None = Field(default=None, ge=0)
  use_couplers: bool = False
  weight_tolerance_pct: Decimal = Field(default=Decimal("2.0"), ge=0)

class BarMarkResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  run_id: UUID
  solid_id: UUID
  element_id: UUID | None
  level_id: UUID | None
  mark: str
  role: str
  shape_code: str
  shape_params: dict
  designation: str | None
  dia_mm: Decimal
  grade: str | None
  count: int
  spacing_mm: Decimal | None
  cut_len_mm: Decimal
  stock_len_mm: Decimal | None
  pieces: int
  lap_count: int
  lap_len_mm: Decimal | None
  total_len_m: Decimal
  unit_weight_kg_m: Decimal
  total_kg: Decimal
  provenance: str
  confidence: Decimal
  review_status: str
  schedule_row_id: UUID | None
  trace: dict
  warnings: list
  engine_version: str
  warnings: list[str]
  
class RebarScheduleRowResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  schedule_import_id: UUID
  row_no: int
  page_no: int | None
  raw_text: str | None
  member_mark: str | None
  mark: str | None
  role: str | None
  shape_code: str | None
  shape_params: dict
  designation: str | None
  dia_mm: Decimal | None
  grade: str | None
  count: int | None
  spacing_mm: Decimal | None
  cut_len_mm: Decimal | None
  declared_total_kg: Decimal | None
  level_id: UUID | None
  matched_element_id: UUID | None
  confidence: Decimal
  review_status: str
  review_note: str | None

class RebarScheduleRowUpdateRequest(BaseModel):
  member_mark: str | None = Field(default=None, max_length=100)
  mark: str | None = Field(default=None, max_length=50)
  role: str | None = Field(default=None, max_length=50)
  shape_code: str | None = Field(default=None, max_length=40)
  shape_params: dict | None = None
  designation: str | None = Field(default=None, max_length=20)
  dia_mm: Decimal | None = Field(default=None, gt=0)
  grade: str | None = Field(default=None, max_length=30)
  count: int | None = Field(default=None, ge=0)
  spacing_mm: Decimal | None = Field(default=None, gt=0)
  cut_len_mm: Decimal | None = Field(default=None, ge=0)
  level_id: UUID | None = None
  matched_element_id: UUID | None = None
  review_status: Literal["PENDING", "CONFIRMED", "REJECTED"] | None = None
  review_note: str | None = Field(default=None, max_length=1000)

class RebarImportResponse(BaseModel):
  schedule_import_id: UUID
  row_count: int
  matched_count: int
  unmatched_count: int
  rows: list[RebarScheduleRowResponse]

class RebarConfirmResponse(BaseModel):
  schedule_import_id: UUID
  confirmed_count: int
  rejected_count: int
  pending_count: int

class RebarSummaryRow(BaseModel):
  dia_mm: Decimal
  designation: str | None
  grade: str | None
  total_len_m: Decimal
  total_kg: Decimal
  mark_count: int

class RebarSummaryResponse(BaseModel):
  boq_version_id: UUID
  rows: list[RebarSummaryRow]
  total_kg: Decimal
  tier1_kg: Decimal
  tier2_kg: Decimal
  tier3_estimate_kg: Decimal
  bbs_exportable: bool        

class BarMarkOverrideRequest(BaseModel):
  cut_len_mm: Decimal | None = Field(default=None, ge=0)
  count: int | None = Field(default=None, ge=0)
  reason: str = Field(min_length=1, max_length=1000)
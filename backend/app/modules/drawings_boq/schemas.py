from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.drawings_boq.models import BOQItemStatus, BOQItemType, BOQVersionStatus, DrawingFormat, DrawingStatus
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
  bbox_min_x_mm: Decimal | None = None
  bbox_min_y_mm: Decimal | None = None
  bbox_min_z_mm: Decimal | None = None
  bbox_max_x_mm: Decimal | None = None
  bbox_max_y_mm: Decimal | None = None
  bbox_max_z_mm: Decimal | None = None
  area_mm2: Decimal | None = None
  volume_mm3: Decimal | None = None
  geometry_kind: str | None = None
  normalization_status: str = "PENDING"
  normalization_issues: list[dict] = Field(default_factory=list)
  level_name: str | None = None
  level_sequence: int | None = None
  measured_as: str | None = None
  predefined_type: str | None = None
  measure_mode: str | None = None

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
  priced_at: datetime | None = None
  pricing_meta: dict = Field(default_factory=dict)
  
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
  rate_book_id: UUID | None = None
  base_rate: Decimal | None = None
  escalation_factor: Decimal | None = None
  spec_key: str | None = None
  spec: dict | None = None
  work_stage: str | None = None
  quantity_range: dict | None = None

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
  quantity: Decimal | None = Field(default=None, ge=0)
  
  adjustment_reason: str | None = Field(
      default=None, max_length=2000,
      description="Required when changing the quantity of an engine-calculated line.",
  )
  unit_rate: Decimal | None = Field(default=None, ge=0)
  save_as_library_default: bool = Field(
    default=False,
    description="If true and unit_rate is set, save this rate as the org's default for this material going forward.",
  )

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
  work_item_code: str | None = Field(default=None, max_length=50)
  effective_from: date | None = None

class MaterialLibraryResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  raw_text: str
  normalized_name: str
  category: str | None
  default_unit: str | None
  default_rate: Decimal | None
  work_item_code: str | None = None
  effective_from: date | None = None
  
class PDFExtractionResultResponse(BaseModel):
  boq_version_id: UUID
  created_item_count: int
  items: list[BOQItemResponse]
  
class MaterialLibraryUpdateRequest(BaseModel):
  normalized_name: str | None = Field(default=None, min_length=1, max_length=300)
  category: str | None = Field(default=None, max_length=150)
  default_unit: str | None = Field(default=None, max_length=20)
  default_rate: Decimal | None = None
  work_item_code: str | None = Field(default=None, max_length=50)
  effective_from: date | None = None

class LabourRateCreateRequest(BaseModel):
  trade: str = Field(min_length=1, max_length=150)
  unit: str = Field(min_length=1, max_length=20)
  rate: Decimal
  work_item_code: str | None = Field(default=None, max_length=50)
  effective_from: date | None = None

class LabourRateUpdateRequest(BaseModel):
  trade: str | None = Field(default=None, min_length=1, max_length=150)
  unit: str | None = Field(default=None, min_length=1, max_length=20)
  rate: Decimal | None = None
  work_item_code: str | None = Field(default=None, max_length=50)
  effective_from: date | None = None

class LabourRateResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  trade: str
  unit: str
  rate: Decimal
  work_item_code: str | None = None
  effective_from: date | None = None

class BOQCustomItemCreateRequest(BaseModel):
  material_name: str = Field(min_length=1, max_length=300)
  category: str | None = Field(default=None, max_length=150)
  unit: str = Field(min_length=1, max_length=20)
  quantity: Decimal = Field(ge=0)
  unit_rate: Decimal | None = Field(default=None, ge=0)

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
  
class DerivedParamsRequest(BaseModel):
  working_space_mm: float | None = Field(default=None, ge=0, le=3000)
  pcc_projection_mm: float | None = Field(default=None, ge=0, le=1000)
  pcc_thickness_mm: float | None = Field(default=None, ge=0, le=600)
  ngl_below_ffl_mm: float | None = Field(default=None, ge=-2000, le=3000)
  ballast_thickness_mm: float | None = Field(default=None, ge=0, le=1500)
  ballast_clearance_mm: float | None = Field(default=None, ge=0, le=1000)
  wall_bed: float | None = Field(default=None, ge=0, le=1, description="1 puts a PCC bed under masonry foundation walls instead of brick ballast.")
  shoring: float | None = Field(default=None, ge=0, le=1, description="1 adds shoring to the trench sides.")
  footing_bottom_below_ngl_mm: float | None = Field(default=None, ge=1, le=10000, description="Depth of the footing bottom below natural ground, for footings read from a drawing.")
  footing_formwork: float | None = Field(default=None, ge=0, le=1, description="1 shutters the four sides of footings read from a drawing.")
  slab_edge_formwork: float | None = Field(default=None, ge=0, le=1, description="0 leaves the slab edges out of the formwork, 1 includes them.")
  formwork_shared_faces: float | None = Field(default=None, ge=0, le=1, description="1 takes off the column faces that a slab of the same floor covers, once the views of the drawing are placed on the building frame.")
  tank_base_formwork: float | None = Field(default=None, ge=0, le=1, description="1 shutters the soffit of the base slab of a tank read from a drawing; 0 takes the base as cast on the earth or on a slab.")
  steel_cover_mm: float | None = Field(default=None, ge=10, le=100, description="Concrete cover at the ends of the bars of a member whose steel is read from a drawing.")
  ring_hook_dia: float | None = Field(default=None, ge=0, le=40, description="Length added to a ring for its hooks, in bar diameters.")
  bar_lap_dia: float | None = Field(default=None, ge=0, le=80, description="Lap of a column's vertical bars with the lift above, in bar diameters.")
  bar_anchor_dia: float | None = Field(default=None, ge=0, le=80, description="Anchorage added at each end of a beam bar, and as a dowel (starter bar) at the foot of a column bar, in bar diameters. 40 unless set; the drawing prints none.")
  steel_wastage_pct: float | None = Field(default=None, ge=0, le=15, description="Percent added to the steel weight of members read from a drawing. 0 leaves the bare weight.")
  steel_cover_slab_mm: float | None = Field(default=None, ge=10, le=100, description="Concrete cover of the bars of a slab. Left out, the general cover applies.")
  steel_cover_beam_mm: float | None = Field(default=None, ge=10, le=100, description="Concrete cover of the bars of a beam or lintel. Left out, the general cover applies.")
  steel_cover_column_mm: float | None = Field(default=None, ge=10, le=100, description="Concrete cover of the bars of a column. Left out, the general cover applies.")
  steel_cover_footing_mm: float | None = Field(default=None, ge=10, le=100, description="Concrete cover of the bars of a footing. Left out, the general cover applies.")
  steel_cover_wall_mm: float | None = Field(default=None, ge=10, le=100, description="Concrete cover of the bars of an RCC wall. Left out, the general cover applies.")
  fill_layer_mm: float | None = Field(default=None, ge=50, le=600, description="Thickness of a compacted fill layer, for the earth filling under floors.")
  earth_swell_pct: float | None = Field(default=None, ge=0, le=50, description="Percent that dug earth swells when loose, for the earth that is carted away or reused. 0 leaves the bank volume.")
  fill_compaction_pct: float | None = Field(default=None, ge=0, le=40, description="Percent of loose earth needed over the finished volume of the filling under floors. 0 takes none.")
  fill_from_excavation: float | None = Field(default=None, ge=0, le=1, description="1 reuses the surplus of the dig for the filling under floors before earth is brought in; 0 treats all the filling as brought in.")
  floor_works_from_spaces: float | None = Field(default=None, ge=0, le=1, description="1 takes the concrete or kacha bed and the anti-termite treatment under the floor of the lowest storey from the rooms of a model; 0 leaves them out.")
  beam_depth_includes_slab: float | None = Field(default=None, ge=0, le=1, description="1 takes the depth of a beam read from a drawing as its overall depth, so the part inside the slab is counted with the slab; 0 takes it as the web below the slab.")
  tie_band_replaces_lintel: float | None = Field(default=None, ge=0, le=1, description="1 leaves out the lintels a measured tie band at lintel level runs over; 0 counts both.")
  stair_formwork_soffit_only: float | None = Field(default=None, ge=0, le=1, description="1 shutters only the soffit of the waist slab of a stair; 0 adds the risers and the sides.")
  beam_lintel_qs_rate: float | None = Field(default=None, ge=0, le=1, description="1 takes the formwork of a beam as 0.75 ft per running foot and of a lintel as 0.5 ft, the QS rate; 0 measures the soffit and both sides.")
  formwork_shared_walls: float | None = Field(default=None, ge=0, le=1, description="1 takes off the column faces that an RCC wall covers, once the views are placed; 0 leaves them.")
  formwork_shared_beams: float | None = Field(default=None, ge=0, le=1, description="1 takes off the column faces that a beam covers, for beams that sit between two columns of the placed view; 0 leaves them.")
  formwork_joints: float | None = Field(default=None, ge=0, le=1, description="1 takes off the formwork where a lintel rests on the wall (its soffit over the bearing), where a chajja is cast with its lintel and where a balcony slab is cast with the floor slab, matched by floor; 0 leaves the faces whole.")
  formwork_lintel_bearing_mm: float | None = Field(default=None, ge=0, le=400, description="Bearing of a lintel on the wall at each end (mm), whose soffit takes no form when formwork_joints is on.")
  rcc_wall_reveals: float | None = Field(default=None, ge=0, le=1, description="1 adds the sides of the doors and windows in an RCC wall to its formwork; 0 takes the two faces only, as the QS sheet does.")
  wall_foundation_works: float | None = Field(default=None, ge=0, le=1, description="1 works out the brick steps of the foundation and the termite treatment of the trench under the masonry walls of a model that has none; 0 leaves them out.")
  wall_membrane: float | None = Field(default=None, ge=0, le=1, description="1 adds the damp-proof membrane along the top of the plinth under the walls (with wall_foundation_works); 0 leaves it out.")
  wall_finishes_from_walls: float | None = Field(default=None, ge=0, le=1, description="1 takes plaster and paint from the walls of a model that has no rooms; 0 leaves them out.")
  steel_estimate_from_volume: float | None = Field(default=None, ge=0, le=1, description="1 estimates the steel of a beam, column, footing or slab whose bars the drawing does not print (flagged, with a range); 0 leaves those members without steel.")
  slab_steel_kg_per_m2: float | None = Field(default=None, ge=0, le=200, description="Kilograms of steel per square metre of a slab whose bars are not printed (the QS rule is 1.5 kg per sq ft = 16.1459); 0 uses the usual kg per m3 instead.")
  one_total: float | None = Field(default=None, ge=0, le=1, description="1 decides each member of the drawings against the model (the same member counted once); 0 keeps the old rule, which sets a drawing measurement aside whenever the model has the work item on that storey.")
  one_total_prefer: float | None = Field(default=None, ge=0, le=2, description="Which source is kept for a member found in both: 0 the more exact one (narrower range), 1 the drawing, 2 the model.")
  one_total_position_tol_mm: float | None = Field(default=None, ge=10, le=1000, description="How far apart (mm) a drawing member and a model member may stand and still be the same member, once the drawing is placed on the model.")
  one_total_trust_pct: float | None = Field(default=None, ge=0, le=100, description="The share of the members of a kind on a storey that must find a partner before the matching is trusted; below it the model is kept and the drawing set aside, as before.")
  opening_area_from_model: float | None = Field(default=None, ge=0, le=1, description="1 adds the area of each door and window of the model (JOI-DOOR-AREA, JOI-WIN-AREA); 0 leaves it out.")
  roof_treatment_from_slabs: float | None = Field(default=None, ge=0, le=1, description="1 adds the treatment of the roof (FIN-ROOF-TREAT) from the plan area of the roof slabs of the model; 0 leaves it out.")
  roof_deck_assembly: float | None = Field(default=None, ge=0, le=1, description="1 adds the layers of the roof deck (membrane, coba, screed) over every roof treatment area; 0 leaves them out.")
  roof_coba_thickness_mm: float | None = Field(default=None, ge=0, le=600, description="Average thickness of the coba (mm) that gives the roof its fall; 0 leaves the coba out. A fall printed on the drawing (thin and thick end) is used instead of the standard value, unless this is set.")
  roof_membrane: float | None = Field(default=None, ge=0, le=1, description="1 adds the waterproofing membrane over the roof area (with roof_deck_assembly); 0 leaves it out.")
  roof_screed: float | None = Field(default=None, ge=0, le=1, description="1 adds the cement screed over the coba (with roof_deck_assembly); 0 leaves it out.")
  roof_turnup_mm: float | None = Field(default=None, ge=0, le=1500, description="Height the membrane and the screed are turned up the parapet along the roof edge (mm), with roof_deck_assembly; 0 leaves the turn-up out.")
  steel_binding_wire: float | None = Field(default=None, ge=0, le=1, description="1 adds binding wire to the steel of every storey; 0 leaves it out.")
  steel_binding_wire_pct: float | None = Field(default=None, ge=0, le=5, description="Binding wire as a percentage of the weight of the reinforcement. The drawings do not print it.")
  steel_chairs: float | None = Field(default=None, ge=0, le=1, description="1 adds chairs under the top steel of slabs; 0 leaves them out.")
  steel_chairs_kg_per_m2: float | None = Field(default=None, ge=0, le=5, description="Kilograms of chairs per square metre of slab. The drawings do not print it.")
  ring_dense_default: float | None = Field(default=None, ge=0, le=1, description="1 gives a column or beam whose drawing prints one ring spacing a closer zone at each end; 0 counts every ring at the printed spacing.")
  ring_dense_spacing_mm: float | None = Field(default=None, ge=50, le=300, description="Ring spacing (mm) in the closer zone when the drawing prints none; 101.6 is 4 in.")
  shoring_from_depth_mm: float | None = Field(default=None, ge=0, le=10000, description="Shore only the part of a trench deeper than this (mm) and switch shoring on by itself; 0 keeps shoring to the switch and the whole depth.")
  plaster_thickness_mm: float | None = Field(default=None, ge=0, le=40, description="Thickness of the plaster (mm). When set, the mortar behind the plaster (area x thickness, m3) is added as FIN-PLASTER-MORTAR; 0 leaves it out. Taken from the drawing note when one is printed.")
  soil_stabilisation: float | None = Field(default=None, ge=0, le=1, description="1 adds cement-stabilised soil under the filled floor (EXC-SOIL-STAB) once the layer depth is known; 0 leaves it out. Whether the soil is loose is a finding made on site, so it is never switched on by itself.")
  soil_stab_depth_mm: float | None = Field(default=None, ge=0, le=1500, description="Depth (mm) of the stabilised soil layer. Taken from the drawing note when one prints it; never guessed.")
  soil_stab_cement_pct: float | None = Field(default=None, ge=0, le=20, description="Cement as a percentage of the weight of the soil, carried on the row. Taken from the drawing note when one prints it.")
  one_total: float | None = Field(default=None, ge=0, le=1, description="1 decides each member of the drawings against the model (the same member counted once); 0 keeps the old rule, which sets a drawing measurement aside whenever the model has the work item on that storey.")
  one_total_prefer: float | None = Field(default=None, ge=0, le=2, description="Which source is kept for a member found in both: 0 the more exact one (narrower range), 1 the drawing, 2 the model.")
  one_total_position_tol_mm: float | None = Field(default=None, ge=10, le=1000, description="How far apart (mm) a drawing member and a model member may stand and still be the same member, once the drawing is placed on the model.")
  one_total_trust_pct: float | None = Field(default=None, ge=0, le=100, description="The share of the members of a kind on a storey that must find a partner before the matching is trusted; below it the model is kept and the drawing set aside, as before.")
  opening_area_from_model: float | None = Field(default=None, ge=0, le=1, description="1 adds the area of each door and window of the model (JOI-DOOR-AREA, JOI-WIN-AREA); 0 leaves it out.")
  
class CalculationRunCreateRequest(BaseModel):
  drawing_ids: list[UUID] | None = None
  rule_set_code: str | None = Field(default=None, max_length=50)
  convention_code: str | None = Field(default=None, max_length=80)
  force_full: bool = Field(default=False, description="Recompute everything instead of only what changed since the last run.")
  verify: bool = Field(default=False,
    description="After an incremental run, also run the full allocation and compare. Slower; a mismatch falls back to the full result.")
  confirm_overlap: bool = Field(default=False,
    description="Go ahead although the chosen drawings share model elements, which would then be counted in each drawing.")
  derived_params: DerivedParamsRequest | None = Field(default=None,
    description="Site assumptions for the derived works (excavation, PCC bed, backfill). Left out, the engine uses its defaults and says so."
  )
  
class RunScopeDrawingResponse(BaseModel):
  drawing_id: UUID
  filename: str
  format: str
  revision_label: str | None = None
  revision_group_id: UUID | None = None
  file_size_bytes: int = 0
  uploaded_at: datetime | None = None
  parsed_at: datetime | None = None

class RunScopeOverlapResponse(BaseModel):
  drawing_a_id: UUID
  drawing_a_name: str
  drawing_b_id: UUID
  drawing_b_name: str
  shared_elements: int
  share: float

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
  mode: str = "FULL"
  baseline_run_id: UUID | None = None
  force_full: bool = False
  verify: bool = False
  attempts: int = 0
  scope_drawings: list[RunScopeDrawingResponse] = []
  scope_overlaps: list[RunScopeOverlapResponse] = []

class RunStageResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  stage: str
  status: str
  attempt: int
  started_at: datetime | None
  finished_at: datetime | None
  counts: dict
  error: str | None
  duration_ms: int | None = None
  peak_rss_mb: int | None = None

class StageTimingResponse(BaseModel):
  stage: str
  status: str
  duration_ms: int | None
  peak_rss_mb: int | None

class RunBudgetResponse(BaseModel):
  name: str
  limit: float
  actual: float | None
  unit: str
  ok: bool | None

class RunMetricsResponse(BaseModel):
  run_id: UUID
  organization_id: UUID
  project_id: UUID
  status: str
  mode: str
  baseline_run_id: UUID | None
  engine_version: str
  fingerprint: str
  attempts: int
  started_at: datetime | None
  completed_at: datetime | None
  duration_ms: int | None
  stages: list[StageTimingResponse]
  timings_ms: dict
  counts: dict
  allocation: dict
  verify: dict | None
  peak_rss_mb: int | None
  failure: dict | None
  budgets: list[RunBudgetResponse]

class OrgCalcMetricsResponse(BaseModel):
  organization_id: UUID
  window_days: int
  runs_total: int
  runs_by_status: dict
  runs_by_mode: dict
  failure_codes: dict
  active_now: int
  duration_seconds: dict
  elements_processed: int
  warnings_total: int
  incremental_share: float
  slowest_runs: list[dict]
  usage: dict

class CalcUsageResponse(BaseModel):
  quota: dict | None
  concurrent: dict
  rate_limits: list[dict]

class ImpactElementResponse(BaseModel):
  element_id: UUID
  ifc_type: str | None
  name: str | None
  ifc_global_id: str | None
  overlap_mm3: float | None

class ImpactLedgerResponse(BaseModel):
  element_id: UUID | None
  work_item_code: str
  quantity_net: Decimal
  unit: str
  ledger_id: UUID

class ImpactResponse(BaseModel):
  run_id: UUID
  element_id: UUID
  touching: list[ImpactElementResponse]
  affected_ledger: list[ImpactLedgerResponse]
  truncated: bool

class ExportJobResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  boq_version_id: UUID
  snapshot_id: UUID
  kind: str
  format: str
  status: str
  parameters: dict
  file_size_bytes: int | None
  error_code: str | None
  error_message: str | None
  started_at: datetime | None
  finished_at: datetime | None
  created_at: datetime

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
  spec_key: str | None = None
  spec: dict | None = None
  work_stage: str | None = None
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
  rate_source: str | None = None
  base_rate: Decimal | None = None
  escalation_factor: Decimal | None = None
  amount: Decimal | None
  confidence: Decimal | None
  review_status: str
  source_kind: str
  ledger_row_count: int
  ledger_hash: str | None
  work_stage: str | None = None
  spec_key: str | None = None
  spec: dict | None = None
  quantity_range: dict | None = None

class StageReportResponse(BaseModel):
  stages: list[dict]
  totals: list[dict]
  
class RangeDriversResponse(BaseModel):
  stale: dict = Field(default_factory=dict)
  units: list[dict]

class ValueAtRiskResponse(BaseModel):
  totals: dict
  by_grade: list[dict]
  top_swing: list[dict]
  top_open: list[dict]
  unpriced: list[dict]
  flags: list[dict]
  left_out: list[dict] = []

class MaterialBreakUpResponse(BaseModel):
  lines: list[dict]
  totals: list[dict]
  not_broken: list[dict]
  assumptions: list[str]

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

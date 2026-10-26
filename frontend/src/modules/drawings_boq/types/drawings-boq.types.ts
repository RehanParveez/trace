export type DrawingFormat = "IFC" | "PDF" | "DWG" | "DXF" | "RVT";
export type DrawingStatus = "UPLOADED" | "PROCESSING" | "PARSED" | "FAILED";
export type BOQItemStatus = "DRAFT" | "APPROVED";
export type BOQItemType = "MATERIAL" | "LABOUR" | "CUSTOM";
export type BOQVersionStatus = "ACTIVE" | "SUPERSEDED";
export type BOQItemRateSource = "LIBRARY" | "AI_SUGGESTED" | "MANUAL" | "PROJECT_OVERRIDE" | "RATE_BOOK";
export type Num = number | string;
export type EngineSeverity = "error" | "warning" | "info";
export type EngineBlocks = "NONE" | "APPROVAL" | "ISSUE";
export type EngineIssueStatus = "OPEN" | "RESOLVED" | "WAIVED";
export type ModelAuditResponse = ModelAudit;
export type ItemTraceResponse = ItemTrace;
export type Surface = "FLOOR" | "WALL" | "CEILING" | "SKIRTING" | "DADO";
export type ScheduleKind = "DOOR" | "WINDOW" | "FINISH" | "FIXTURE" | "GENERAL";
export type RowDecision = "PENDING" | "CONFIRMED" | "REJECTED";
export type ScheduleImportStatus = "PENDING_REVIEW" | "CONFIRMED" | "REJECTED" | "ARCHIVED";
export type ScheduleSource = "PDF_AI" | "PDF_TEXT" | "CSV" | "MANUAL";
export type RebarRole = "COLUMN" | "BEAM" | "LINTEL" | "SLAB" | "FOOTING" | "PILE" | "WALL" | "STAIR";

export interface Drawing {
  id: string;
  project_id: string;
  original_filename: string;
  format: DrawingFormat;
  status: DrawingStatus;
  file_size_bytes: number;
  error_message: string | null;
  parsed_at: string | null;
  created_at: string;
  revision_group_id: string;
  revision_label: string | null;
  is_current_revision: boolean;
  superseded_at: string | null;
  latest_audit_id?: string | null;
  ingestion_meta?: DrawingIngestionMeta;
}

export interface DrawingElement {
  id: string;
  drawing_id?: string;
  ifc_global_id: string | null;
  ifc_type: string;
  name: string | null;
  raw_material_text: string | null;
  unit: string | null;
  quantity: number | string;
  properties: Record<string, unknown>;
  discipline?: string | null;
  structural_role?: string | null;
  classification_source?: string | null;
  classification_confidence?: number | string | null;
  quantity_source?: string | null;
  level_id?: string | null;
  length_mm?: number | string | null;
  width_mm?: number | string | null;
  height_mm?: number | string | null;
  thickness_mm?: number | string | null;
  elevation_base_mm?: number | string | null;
  elevation_top_mm?: number | string | null;
  area_mm2?: number | string | null;
  volume_mm3?: number | string | null;
  bbox_min_x_mm?: number | string | null;
  bbox_min_y_mm?: number | string | null;
  bbox_min_z_mm?: number | string | null;
  bbox_max_x_mm?: number | string | null;
  bbox_max_y_mm?: number | string | null;
  bbox_max_z_mm?: number | string | null;
  geometry_kind?: string | null;
  profile?: Record<string, unknown> | null;
  placement?: Record<string, unknown> | null;
  type_mark?: string | null;
  type_name?: string | null;
  normalization_status?: NormalizationStatus;
  normalization_issues?: unknown[];
  level_name?: string | null;
  level_sequence?: number | null;
  measured_as?: string | null;
  predefined_type?: string | null;
  measure_mode?: "EXACT" | "APPROXIMATE" | "NONE" | "PDF_MEASURED" | "PDF_FOUND" | null;
  frame?: { xM: number | null; yM: number | null; label: string } | null;
}

export interface BuildingLevel {
  id: string;
  drawing_id: string;
  name: string;
  elevation_mm: number | string | null;
  ifc_storey_id: string | null;
  sequence: number;
}

export interface BuildingLevelResponse {
  id: string;
  name: string;
  elevation_mm: number | string | null;
  ifc_storey_id: string | null;
  sequence: number;
}

export interface ModelAudit {
  id: string;
  drawing_id: string;
  overall_score: number | string;
  issues: ModelAuditIssue[];
  element_count: number;
  missing_material_count: number;
  zero_quantity_count: number;
  unclassified_proxy_count: number;
  extra_stats: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface DrawingElementFilters {
  limit?: number;
  cursor?: string | null;
  structural_role?: string | null;
  discipline?: string | null;
  level_id?: string | null;
  normalization_status?: NormalizationStatus | null;
  ifc_type?: string | null;
}

export interface CursorPage<T> {
  items: T[];
  nextCursor: string | null;
  total?: number | null;
}

export interface BOQVersion {
  id: string;
  project_id: string;
  drawing_id: string | null;
  label: string;
  status: BOQVersionStatus;
  covered_area_sqft: number | string | null;
  export_meta: BOQExportMeta;
  rule_set_id?: string | null;
  audit_score?: number | string | null;
  generation_meta?: Record<string, unknown>;
  lifecycle?: BOQLifecycle;
  origin?: BOQVersionOrigin;
  calculation_run_id?: string | null;
  snapshot_id?: string | null;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  issued_by_user_id?: string | null;
  issued_at?: string | null;
  priced_at?: string | null;
  pricing_meta?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

export interface BOQVersionResponse {
  id: string;
  project_id: string;
  drawing_id: string | null;
  label: string;
  created_at: string;
  status: BOQVersionStatus;
  covered_area_sqft: number | string | null;
  export_meta: Record<string, unknown>;
  lifecycle: BOQLifecycle;
  origin: BOQVersionOrigin;
  calculation_run_id: string | null;
  snapshot_id: string | null;
  rule_set_id: string | null;
  audit_score: number | string | null;
  approved_at: string | null;
  issued_at: string | null;
  priced_at: string | null;
  pricing_meta: Record<string, unknown>;
}

export interface BOQExportMeta {
  company_name?: string | null;
  client_name?: string | null;
  project_title?: string | null;
  location?: string | null;
  plot_size?: string | null;
  storeys?: string | null;
  prepared_by?: string | null;
  checked_by?: string | null;
}

export interface BOQItem {
  id: string;
  boq_version_id: string;
  drawing_element_id: string | null;
  material_name: string;
  category: string | null;
  unit: string;
  quantity: number | string;
  unit_rate: number | string | null;
  rate_source?: BOQItemRateSource | null;
  item_type: BOQItemType;
  created_by_user_id: string | null;
  status: BOQItemStatus;
  version: number;
  approved_by_user_id?: string | null;
  approved_at: string | null;
  work_item_code?: string | null;
  description?: string | null;
  calculation_formula?: string | null;
  confidence?: number | string | null;
  rule_set_id?: string | null;
  recipe_id?: string | null;
  gross_quantity?: number | string | null;
  net_quantity?: number | string | null;
  waste_factor_applied?: number | string | null;
  source_element_count?: number;
  item_key?: string | null;
  level_id?: string | null;
  material_grade?: string | null;
  spec_key?: string | null;
  spec?: BOQItemSpec | null;
  work_stage?: string | null;
  quantity_range?: QuantityRange | null;
  canonical_unit?: string | null;
  unit_factor?: number | string | null;
  adjustment_total?: number | string;
  review_status?: ItemReviewStatus;
  source_kind?: BOQItemSourceKind;
  is_manual?: boolean;
  calculation_run_id?: string | null;
  engine_version?: string | null;
  rate_book_id?: string | null;
  base_rate?: number | string | null;
  escalation_factor?: number | string | null;
}

export interface BOQItemResponse {
  id: string;
  boq_version_id: string;
  drawing_element_id: string | null;
  material_name: string;
  category: string | null;
  unit: string;
  quantity: number | string;
  unit_rate: number | string | null;
  rate_source: BOQItemRateSource | null;
  status: BOQItemStatus;
  version: number;
  approved_at: string | null;
  item_type: BOQItemType;
  created_by_user_id: string | null;
  work_item_code: string | null;
  description: string | null;
  net_quantity: number | string | null;
  adjustment_total: number | string;
  gross_quantity: number | string | null;
  waste_factor_applied: number | string | null;
  confidence: number | string | null;
  review_status: ItemReviewStatus;
  source_kind: BOQItemSourceKind;
  is_manual: boolean;
  canonical_unit: string | null;
  unit_factor: number | string | null;
  level_id: string | null;
  item_key: string | null;
  calculation_run_id: string | null;
  spec_key?: string | null;
  spec?: BOQItemSpec | null;
  work_stage?: string | null;
  quantity_range?: QuantityRange | null;
  rate_book_id: string | null;
  base_rate: number | string | null;
  escalation_factor: number | string | null;
}

export interface BOQItemUpdateRequest {
  version: number;
  material_name?: string;
  category?: string | null;
  unit?: string;
  quantity?: number;
  unit_rate?: number | null;
  adjustment_reason?: string;
}

export interface BOQCustomItemCreateRequest {
  material_name: string;
  category?: string | null;
  unit: string;
  quantity: number;
  unit_rate?: number | null;
}

export interface BOQVersionUpdateRequest {
  covered_area_sqft?: number | null;
  export_meta?: Partial<BOQExportMeta>;
}

export interface BOQSummary {
  boq_version_id: string;
  materials_total: number | string;
  labour_total: number | string;
  custom_total: number | string;
  grand_total: number | string;
  cost_per_sqft: number | string | null;
  covered_area_sqft: number | string | null;
  amount_in_words: string;
  unpriced_item_count: number;
  unapproved_item_count: number;
  item_count: number;
}

export interface MaterialLibraryEntry {
  id: string;
  raw_text: string;
  normalized_name: string;
  category: string | null;
  default_unit: string | null;
  default_rate: number | string | null;
  work_item_code?: string | null;
  effective_from?: string | null;
}

export interface MaterialLibraryCreateRequest {
  raw_text: string;
  normalized_name: string;
  category?: string | null;
  default_unit?: string | null;
  default_rate?: number | null;
  work_item_code?: string | null;
  effective_from?: string | null;
}

export interface MaterialLibraryUpdateRequest {
  normalized_name?: string;
  category?: string | null;
  default_unit?: string | null;
  default_rate?: number | null;
  work_item_code?: string | null;
  effective_from?: string | null;
}

export interface LabourRate {
  id: string;
  trade: string;
  unit: string;
  rate: number | string;
  work_item_code: string | null;
  effective_from: string | null;
}

export interface LabourRateCreateRequest {
  trade: string;
  unit: string;
  rate: number;
  work_item_code?: string | null;
  effective_from?: string | null;
}

export interface LabourRateUpdateRequest {
  trade?: string;
  unit?: string;
  rate?: number;
  work_item_code?: string | null;
  effective_from?: string | null;
}

export interface PDFExtractionResult {
  boq_version_id: string;
  created_item_count: number;
  items: BOQItem[];
}

export interface ProjectBOQCount {
  project_id: string;
  latest_boq_item_count: number;
}

export interface DrawingOrganizationSummary {
  drawing_count: number;
}

export interface CalculationRunCreateRequest {
  drawing_ids?: string[];
  rule_set_code?: string | null;
  convention_code?: string | null;
  force_full?: boolean;
  verify?: boolean;
  confirm_overlap?: boolean;
  derived_params?: DerivedParams;
}

export interface RunScopeOverlap {
  drawing_a_id: string;
  drawing_a_name: string;
  drawing_b_id: string;
  drawing_b_name: string;
  shared_elements: number;
  share: number;
}

export interface RunScopeDrawing {
  drawing_id: string;
  filename: string;
  format: string;
  revision_label: string | null;
  revision_group_id?: string | null;
  file_size_bytes: number;
  uploaded_at?: string | null;
  parsed_at?: string | null;
}

export interface CalculationRun {
  id: string;
  organization_id?: string;
  project_id: string;
  requested_by_user_id?: string | null;
  rule_set_id?: string;
  convention_code?: string | null;
  drawing_revision_ids?: string[];
  scope_drawings?: RunScopeDrawing[];
  scope_overlaps?: RunScopeOverlap[];
  engine_version: string;
  fingerprint?: string;
  status: CalculationRunStatus;
  progress_pct: number;
  started_at?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  settings?: Record<string, unknown>;
  stats?: RunStats;
  created_at?: string;
  updated_at?: string;
  mode?: "FULL" | "INCREMENTAL";
  baseline_run_id?: string | null;
  force_full?: boolean;
  verify?: boolean;
  attempts?: number;
}

export interface CalculationRunResponse {
  id: string;
  project_id: string;
  rule_set_id: string;
  convention_code: string | null;
  drawing_revision_ids: string[];
  engine_version: string;
  fingerprint: string;
  status: CalculationRunStatus;
  progress_pct: number;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  stats: RunStats;
  created_at: string;
  mode: "FULL" | "INCREMENTAL";
  baseline_run_id: string | null;
  force_full: boolean;
  verify: boolean;
  attempts: number;
}

export interface RunStage {
  id: string;
  organization_id?: string;
  run_id: string;
  stage: string;
  status: RunStageStatus;
  attempt: number;
  started_at?: string | null;
  finished_at?: string | null;
  counts: Record<string, unknown>;
  error?: string | null;
  created_at?: string;
  updated_at?: string;
  duration_ms?: number | null;
  peak_rss_mb?: number | null;
}

export interface RunStageResponse {
  stage: string;
  status: RunStageStatus;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  counts: Record<string, unknown>;
  error: string | null;
  duration_ms: number | null;
  peak_rss_mb: number | null;
}

export interface QuantitySolid {
  id: string;
  organization_id?: string;
  run_id: string;
  element_id: string | null;
  level_id: string | null;
  role: string;
  component_type: string;
  geometry_kind: string;
  material_grade: string | null;
  gross_volume_m3: number | string | null;
  gross_area_m2: number | string | null;
  gross_length_m: number | string | null;
  count: number | null;
  status: SolidStatus;
  issues: unknown[];
  engine_version: string;
}

export interface QuantitySolidResponse {
  id: string;
  element_id: string | null;
  level_id: string | null;
  role: string;
  component_type: string;
  geometry_kind: string;
  gross_volume_m3: number | string | null;
  gross_area_m2: number | string | null;
  gross_length_m: number | string | null;
  count: number | null;
  status: SolidStatus;
  issues: Record<string, unknown>[];
}

export interface LedgerRow {
  id: string;
  organization_id?: string;
  run_id?: string;
  solid_id?: string;
  element_id?: string | null;
  level_id?: string | null;
  work_item_code: string;
  quantity_net: number | string;
  unit: string;
  material_grade?: string | null;
  spec_key?: string | null;
  spec?: BOQItemSpec | null;
  work_stage?: string | null;
  source_kind: LedgerSourceKind;
  confidence: number | string;
  formula_code: string;
  trace: LedgerTrace;
  warnings: unknown[];
  engine_version: string;
}

export interface LedgerRowResponse {
  id: string;
  solid_id: string;
  element_id: string | null;
  level_id: string | null;
  work_item_code: string;
  quantity_net: number | string;
  unit: string;
  material_grade: string | null;
  source_kind: string;
  spec_key?: string | null;
  spec?: BOQItemSpec | null;
  work_stage?: string | null;
  confidence: number | string;
  formula_code: string;
  trace: LedgerTrace;
  warnings: string[];
  engine_version: string;
}

export interface Deduction {
  id: string;
  organization_id?: string;
  run_id: string;
  from_solid_id: string;
  to_solid_id?: string | null;
  deduction_type: DeductionType;
  quantity: number | string;
  unit: string;
  rule_code: string;
  rule_version?: string | null;
  geometry: Record<string, unknown>;
  explanation?: string | null;
  engine_version: string;
}

export interface DeductionResponse {
  id: string;
  from_solid_id: string;
  to_solid_id: string | null;
  deduction_type: DeductionKind;
  quantity: number | string;
  unit: string;
  rule_code: string;
  rule_version: string | null;
  geometry: Record<string, unknown>;
  explanation: string | null;
  engine_version: string;
}

export interface BOQBuildResponse {
  boq_version_id?: string;
  calculation_run_id?: string;
  created_item_count?: number;
  updated_item_count?: number;
  review_issue_count?: number;
  lifecycle?: BOQLifecycle;
  version?: BOQVersion;
  items?: BOQItem[];
  [key: string]: unknown;
  items_created: number;
  items_updated: number;
  items_removed: number;
  orphaned_items: number;
  open_issues: number;
}

export interface EngineBOQBuildResponse {
  boq_version_id: string;
  items_created: number;
  items_updated: number;
  items_removed: number;
  orphaned_items: number;
  open_issues: number;
}

export interface TransitionRequest {
  note?: string | null;
}

export interface Snapshot {
  id: string;
  organization_id?: string;
  boq_version_id: string;
  version_no: number;
  purpose: SnapshotPurpose;
  content_hash: string;
  item_count: number;
  totals: Record<string, unknown>;
  calculation_run_id?: string | null;
  rule_set_id?: string | null;
  rule_set_code?: string | null;
  rule_set_version?: number | null;
  convention_code?: string | null;
  engine_version?: string | null;
  note?: string | null;
  created_by_user_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface SnapshotItem {
  id: string;
  organization_id?: string;
  snapshot_id: string;
  line_no: number;
  source_item_id?: string | null;
  item_key?: string | null;
  work_item_code?: string | null;
  material_name: string;
  description?: string | null;
  category?: string | null;
  item_type: string;
  level_id?: string | null;
  material_grade?: string | null;
  unit: string;
  canonical_unit?: string | null;
  unit_factor?: number | string | null;
  net_quantity?: number | string | null;
  adjustment_total: number | string;
  quantity: number | string;
  waste_factor_applied?: number | string | null;
  gross_quantity?: number | string | null;
  unit_rate?: number | string | null;
  rate_source?: string | null;
  base_rate?: number | string | null;
  escalation_factor?: number | string | null;
  amount?: number | string | null;
  confidence?: number | string | null;
  review_status: string;
  source_kind: string;
  is_manual: boolean;
  ledger_row_count: number;
  ledger_hash?: string | null;
}

export interface Adjustment {
  id: string;
  organization_id?: string;
  boq_item_id: string;
  kind: AdjustmentKind;
  value: number | string;
  reason: string;
  created_by_user_id?: string | null;
  revoked_at?: string | null;
  revoked_by_user_id?: string | null;
  revoke_reason?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AdjustmentResponse {
  id: string;
  boq_item_id: string;
  kind: AdjustmentKind;
  value: number | string;
  reason: string;
  created_by_user_id: string | null;
  created_at: string;
  revoked_at: string | null;
  revoke_reason: string | null;
}

export interface AdjustmentCreateRequest {
  kind: "DELTA" | "REPLACE";
  value: number;
  reason: string;
}

export interface ItemTrace {
  [key: string]: unknown;
  item: BOQItemResponse;
  ledger: LedgerRowResponse[];
  deductions: DeductionResponse[];
  adjustments: AdjustmentResponse[];
  bar_marks?: BarMarkResponse[];
}

export interface ReviewIssue {
  id: string;
  organization_id?: string;
  project_id: string;
  boq_version_id?: string | null;
  calculation_run_id?: string | null;
  drawing_element_id?: string | null;
  ledger_id?: string | null;
  boq_item_id?: string | null;
  adjustment_id?: string | null;
  code: string;
  severity: ReviewSeverity;
  blocks: ReviewBlocks;
  message: string;
  suggested_fix?: string | null;
  details: Record<string, unknown>;
  dedupe_key?: string;
  status: ReviewStatus;
  resolution_note?: string | null;
  resolved_by_user_id?: string | null;
  resolved_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ReviewIssueResponse {
  id: string;
  project_id: string;
  boq_version_id: string | null;
  boq_item_id: string | null;
  drawing_element_id: string | null;
  code: string;
  severity: ReviewSeverity;
  blocks: ReviewBlocks;
  message: string;
  suggested_fix: string | null;
  details: Record<string, unknown>;
  status: ReviewStatus;
  resolution_note: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface ReviewIssueUpdateRequest {
  status: "RESOLVED" | "WAIVED";
  note?: string | null;
}

export interface ReasonRequest {
  reason: string;
}

export interface IfcHeader {
  authoring_tool?: string;
  application?: string;
  application_version?: string;
  application_identifier?: string;
  developer?: string;
  originating_system?: string;
  preprocessor_version?: string;
  organization?: string;
  author?: string;
  file_time_stamp?: string;
}

export interface DrawingIngestionMeta {
  reader_version?: string;
  ifc_schema?: string;
  length_unit_scale?: number;
  header?: IfcHeader;
  model_issues?: {
    code: string;
    severity: string;
    message: string;
  }[];
  stats?: {
    space_count?: number;
    element_count?: number;
    by_status?: Record<string, number>;
    by_geometry_kind?: Record<string, number>;
    by_role?: Record<string, number>;
    by_discipline?: Record<string, number>;
    excluded?: Record<string, number>;
  };
}

export interface ModelAuditIssue {
  code: string;
  severity: EngineSeverity | string;
  message: string;
  count: number;
  element_ids: string[];
  scope?: "model";
}

export interface SnapshotTotals {
  materials?: string;
  labour?: string;
  custom?: string;
  grand?: string;
  item_count?: number;
  unpriced_item_count?: number;
}

export interface SnapshotResponse {
  id: string;
  boq_version_id: string;
  version_no: number;
  purpose: SnapshotPurpose;
  content_hash: string;
  item_count: number;
  totals: SnapshotTotals;
  rule_set_code: string | null;
  rule_set_version: number | null;
  convention_code: string | null;
  engine_version: string | null;
  note: string | null;
  created_at: string;
}

export interface SnapshotItemResponse {
  id: string;
  line_no: number;
  source_item_id: string | null;
  work_item_code: string | null;
  material_name: string;
  description: string | null;
  item_type: string;
  unit: string;
  net_quantity: number | string | null;
  adjustment_total: number | string;
  quantity: number | string;
  gross_quantity: number | string | null;
  unit_rate: number | string | null;
  rate_source: string | null;
  base_rate: number | string | null;
  escalation_factor: number | string | null;
  amount: number | string | null;
  confidence: number | string | null;
  review_status: string;
  source_kind: string;
  ledger_row_count: number;
  ledger_hash: string | null;
  work_stage?: string | null;
  spec_key?: string | null;
  quantity_range?: QuantityRange | null;
}

export interface NormalizationIssue {
  code: string;
  severity: string;
  message: string;
}

export interface SpaceResponse {
  id: string;
  project_id: string;
  drawing_id: string | null;
  level_id: string | null;
  source: "IFC" | "MANUAL";
  ifc_global_id: string | null;
  number: string | null;
  name: string | null;
  long_name: string | null;
  category: string;
  usage_text: string | null;
  is_external: boolean;
  is_active: boolean;
  gross_floor_area_mm2: Num | null;
  net_floor_area_mm2: Num | null;
  perimeter_mm: Num | null;
  height_mm: Num | null;
  geometry_kind: string;
  normalization_status: string;
  normalization_issues: NormalizationIssue[];
  finish_count: number;
  boundary_count: number;
}

export interface SpaceFinishResponse {
  id: string;
  space_id: string;
  surface: Surface;
  work_item_code: string;
  finish_name: string | null;
  height_mm: Num | null;
  source: "IFC_PSET" | "SCHEDULE_IMPORT" | "MANUAL" | "RULE_DEFAULT" | string;
  schedule_row_id: string | null;
  confidence: Num;
  review_status: string;
  is_active: boolean;
  deduct_openings: boolean;
}

export interface BoundaryResponse {
  element_id: string;
  name: string | null;
  ifc_type: string;
  structural_role: string | null;
  boundary_kind: string;
  side: string;
  source: string;
}

export interface SpaceDetailResponse extends SpaceResponse {
  boundaries: BoundaryResponse[];
  finishes: SpaceFinishResponse[];
}

export interface SpaceCreateRequest {
  number?: string | null;
  name?: string | null;
  long_name?: string | null;
  usage_text?: string | null;
  category?: string;
  level_id?: string | null;
  is_external?: boolean;
  floor_area_m2?: number | null;
  perimeter_m?: number | null;
  height_m?: number | null;
}

export interface SpaceUpdateRequest {
  number?: string | null;
  name?: string | null;
  long_name?: string | null;
  usage_text?: string | null;
  category?: string | null;
  level_id?: string | null;
  is_external?: boolean | null;
  is_active?: boolean | null;
  floor_area_m2?: number | null;
  perimeter_m?: number | null;
  height_m?: number | null;
}

export interface SpaceFinishCreateRequest {
  surface: Surface;
  work_item_code: string;
  finish_name?: string | null;
  height_mm?: number | null;
  deduct_openings?: boolean;
}

export interface FinishPreviewLine {
  surface: string;
  work_item_code: string;
  unit: string;
  quantity: Num;
  confidence: Num;
  formula_code: string;
  source_kind: string;
  warnings: string[];
  steps: TraceStep[];
}

export interface FinishPreviewResolved {
  surface: string;
  work_item_code: string;
  source: string;
  height_mm: string | null;
  deduct_openings: boolean;
}

export interface FinishPreviewResponse {
  space_id: string;
  rule_set_code: string;
  resolved: FinishPreviewResolved[];
  lines: FinishPreviewLine[];
  skipped: Record<string, unknown>;
}

export interface ScheduleRowResponse {
  id: string;
  schedule_import_id: string;
  row_no: number;
  schedule_kind: ScheduleKind;
  page_no: number | null;
  raw_text: string | null;
  mark: string | null;
  description: string | null;
  location_text: string | null;
  level_id: string | null;
  space_id: string | null;
  unit: string | null;
  quantity: Num | null;
  width_mm: Num | null;
  height_mm: Num | null;
  work_item_code: string | null;
  canonical_unit: string | null;
  canonical_quantity: Num | null;
  confidence: Num;
  review_status: RowDecision;
  review_note: string | null;
  matched_element_count: number;
  surface: Surface | null;
  finish_name: string | null;
  notes: string[];
  quantity_defaulted: boolean;
}

export interface ScheduleImportResponse {
  id: string;
  project_id: string;
  drawing_id: string | null;
  source: ScheduleSource;
  schedule_kind: ScheduleKind;
  status: ScheduleImportStatus;
  file_name: string | null;
  row_count: number;
  confirmed_count: number;
  notes: string | null;
  extraction_meta: Record<string, unknown>;
  created_at: string;
  confirmed_at: string | null;
}

export interface ScheduleCountMismatch {
  row_id: string;
  mark: string | null;
  schedule_quantity: string;
  model_count: number;
}

export interface ScheduleImportSummary {
  pending: number;
  confirmed: number;
  rejected: number;
  model_matched: number;
  finish_rows_linked: number;
  finish_rows_unlinked: number;
  count_mismatches: ScheduleCountMismatch[];
}

export interface ScheduleImportDetailResponse extends ScheduleImportResponse {
  rows: ScheduleRowResponse[];
  summary: ScheduleImportSummary;
}

export interface ScheduleFromPdfRequest {
  drawing_id: string;
  schedule_kind: ScheduleKind;
  notes?: string | null;
}

export interface ScheduleManualCreateRequest {
  schedule_kind: ScheduleKind;
  notes?: string | null;
}

export interface ScheduleRowCreateRequest {
  mark?: string | null;
  description?: string | null;
  location_text?: string | null;
  level_id?: string | null;
  space_id?: string | null;
  unit?: string | null;
  quantity?: number | null;
  width_mm?: number | null;
  height_mm?: number | null;
  work_item_code?: string | null;
  surface?: Surface | null;
  finish_name?: string | null;
}

export interface SpaceListFilters {
  drawing_id?: string;
  level_id?: string;
  category?: string;
  include_inactive?: boolean;
  current_only?: boolean;
}

export interface ScheduleRowUpdateRequest extends ScheduleRowCreateRequest {
  review_status?: RowDecision | null;
  review_note?: string | null;
}

export interface BulkReviewResponse {
  updated: number;
  failed: { row_id: string; code: string; message: string }[];
}

export interface FinishConflict {
  row_id: string;
  space_id: string;
  surface: string;
  work_item_code: string | null;
  reason: string;
}

export interface ConfirmImportResponse {
  schedule_import: ScheduleImportResponse;
  finishes_created: number;
  finishes_updated: number;
  finish_conflicts: FinishConflict[];
  ledger_lines: number;
  model_matched_rows: number;
  unlinked_finish_rows: number;
  count_mismatches: ScheduleCountMismatch[];
  rerun_recommended: boolean;
}

export interface RematchResponse {
  rows_changed: number;
  rerun_recommended: boolean;
}

export interface LevelOption {
  id: string;
  name: string;
  elevation_mm: Num | null;
  ifc_storey_id: string | null;
  sequence: number;
}

export interface BoundaryCandidate {
  id: string;
  name: string | null;
  ifc_type: string;
  structural_role: string | null;
  level_id: string | null;
}

export interface LedgerTrace {
  formula_code: FormulaCode | string;
  engine_version: string;
  convention: string | null;
  rule_set: { code: string; version: number };
  inputs: Record<string, unknown>;
  steps: TraceStep[];
  net: Record<string, string>;
  rounding: string;
  label?: string;
}

export interface ElementPlacement {
  depth_mm?: Num | null;
  plan_mm?: [Num, Num][] | null;
  z_min_mm?: Num | null;
  z_max_mm?: Num | null;
  [key: string]: unknown;
}

export type ElementProfile =
  | { kind: "RECT"; x_dim: Num; y_dim: Num }
  | { kind: "CIRCLE"; radius: Num }
  | { kind: "POLYGON"; points_mm: [Num, Num][] };

export interface OpeningStats {
  hosted: number; deducted: number; ignored: number;
  size_missing: number; unhosted: number; qto_walls_skipped: number;
}

export interface AllocationStats {
  convention?: string;
  participating?: number;
  overlaps?: number;
  approximate_solids?: number;
  components_checked?: number;
  conservation_failures?: number;
  openings?: OpeningStats;
}

export interface RebarBand {
  elements: number;
  m3: Num;
  low_kg: Num;
  likely_kg: Num;
  high_kg: Num;
}

export interface RebarStats {
  schedule_rows?: number; schedule_marks?: number; matched?: number; unmatched?: number;
  estimated_marks?: number; estimate_suppressed?: number;
  total_kg?: string; tier2_kg?: string; tier3_kg?: string; covered_families?: string[];
  estimated_elements?: number;
  total_low_kg?: Num;
  total_high_kg?: Num;
  measured_share_pct?: Num;
  estimate_bands?: Record<string, RebarBand>;
  by_dia_kg?: Record<string, Num>;
}

export interface SteelRoleStats {
  count: number;
  kg: Num;
}

export interface SteelStats {
  elements?: number;
  measured?: number;
  not_measured?: number;
  sections_kg?: Num;
  sections_tonnes?: Num;
  piles?: number;
  pile_length_m?: Num;
  suspected_solid_sections?: number;
  duplicates_suspected?: number;
  uncertain_material?: number;
  density_kg_m3?: Num;
  by_role?: Record<string, SteelRoleStats>;
}

export interface RunStats {
  convention?: string;
  promoted?: unknown;
  spaces?: number;
  rejected_total?: number;
  rejected_sample?: { element_id: string; ifc_type: string; code: string }[];
  finishes_skipped?: Record<string, number>;
  boq?: Record<string, string>;
  boq_error?: string;
  elements_in?: number;
  participating?: number;
  overlaps?: number;
  approximate_solids?: number;
  components_checked?: number;
  conservation_failures?: number;
  openings?: OpeningStats;
  schedule_rows?: number; schedule_marks?: number; matched?: number; unmatched?: number;
  estimated_marks?: number; estimate_suppressed?: number;
  total_kg?: string; tier2_kg?: string; tier3_kg?: string; covered_families?: string[];
  allocation?: AllocationStats;
  skipped_by_role?: Record<string, number>;
  unmapped_by_type?: Record<string, number>;
  rejected?: { element_id: string; ifc_type: string; code: string; message: string }[];
  [key: string]: unknown;
  rebar?: RebarStats;
  steel?: SteelStats;
  rebar_skipped?: Record<string, number>;
  finish_skipped?: Record<string, number>
  wall_material?: WallMaterialStats
  spec?: SpecStats;
  stages?: StageStats;
  layers?: LayerStats;
  derived?: DerivedStats;
  ranges?: RangeStampStats;
  pdf_takeoff?: PdfTakeoffStats;
  material?: MaterialStats;
  coverage?: CoverageStats;
  confidence?: ConfidenceStats;
  ifc_rebar?: IfcRebarStats;
}

export interface CoverageStats {
  elements: number;
  measured: number;
  rejected: number;
  skipped_by_role: number;
  unmapped: number;
  other_unmeasured: number;
  skipped_roles?: Record<string, number>;
  unmapped_types?: Record<string, number>;
  rejected_codes?: Record<string, number>;
}

export interface IfcRebarStats {
  bars?: number;
  bars_without_data?: number;
  measured?: number;
  no_diameter?: number;
  no_length?: number;
  kg?: string;
  tonnes?: string;
  length_m?: string;
  hosts?: number;
  no_host?: number;
  length_from_geometry?: number;
  diameter_derived?: number;
  area_mismatch?: number;
  file_weight_mismatch?: number;
  by_dia?: Record<string, { bars: number; kg: string; length_m: string }>;
  by_family_kg?: Record<string, string>;
  file_weight?: { bars: number; file_kg: string; computed_kg: string; difference_pct: string | null };
}

export interface ConfidenceStats {
  rows: number;
  bands: { HIGH: number; MEDIUM: number; LOW: number };
  volume_m3: { HIGH: string; MEDIUM: string; LOW: string };
  by_geometry: Record<string, { rows: number; m3: string }>;
}

export interface BOQItemSpec {
  kind: "MASONRY" | "CONCRETE" | "DERIVED";
  thickness_mm?: number;
  mortar?: string;
  grade?: string;
  basis?: Record<string, string>;
  recipe?: string;
  item?: string;
  category?: string;
  params?: Record<string, number>;
  ngl_z_mm?: number;
}

export interface SpecStats {
  enabled: boolean;
  rows_with_spec?: number;
  masonry_rows?: number;
  concrete_rows?: number;
  mix_missing?: number;
  mortar_missing?: number;
  thickness_missing?: number;
  distinct_spec_keys?: number;
}

export interface StageDatum {
  name: string;
  z_mm: number;
  source: "model" | "drawing" | "param" | "default" | "typed";
  note: string;
}

export interface StageBand {
  stage: string;
  from_mm: number | null;
  to_mm: number | null;
  defaulted: boolean;
  soft: boolean;
}

export interface StageStats {
  enabled: boolean;
  resolved?: boolean;
  reason?: string;
  datums?: StageDatum[];
  bands?: StageBand[];
  unused_overrides?: string[];
  rows_split?: number;
  rows_tagged?: number;
  rows_not_split?: number;
  rows_unresolved?: number;
  rows_by_stage?: Record<string, number>;
}

export interface DerivedParams {
  working_space_mm?: number;
  pcc_projection_mm?: number;
  pcc_thickness_mm?: number;
  ngl_below_ffl_mm?: number;
  ballast_thickness_mm?: number;
  ballast_clearance_mm?: number;
  wall_bed?: number;
  shoring?: number;
  footing_bottom_below_ngl_mm?: number;
  footing_formwork?: number;
  slab_edge_formwork?: number;
  formwork_shared_faces?: number;
  tank_base_formwork?: number;
  steel_cover_mm?: number;
  ring_hook_dia?: number;
  bar_lap_dia?: number;
  bar_anchor_dia?: number;
  steel_wastage_pct?: number;
  beam_depth_includes_slab?: number;
  tie_band_replaces_lintel?: number;
  dpc_thickness_mm?: number;
  dpc_door_deduction?: number;
  steel_cover_slab_mm?: number;
  steel_cover_beam_mm?: number;
  steel_cover_column_mm?: number;
  steel_cover_footing_mm?: number;
  steel_cover_wall_mm?: number;
  fill_layer_mm?: number;
  earth_swell_pct?: number;
  fill_compaction_pct?: number;
  fill_from_excavation?: number;
  floor_works_from_spaces?: number;
  wall_foundation_works?: number;
  wall_membrane?: number;
  wall_finishes_from_walls?: number;
  steel_estimate_from_volume?: number;
  slab_steel_kg_per_m2?: number;
  one_total?: number;
  one_total_prefer?: number;
  one_total_position_tol_mm?: number;
  one_total_trust_pct?: number;
  opening_area_from_model?: number;
  roof_treatment_from_slabs?: number;
  roof_deck_assembly?: number;
  roof_coba_thickness_mm?: number;
  roof_membrane?: number;
  roof_screed?: number;
  roof_turnup_mm?: number;
  steel_binding_wire?: number;
  steel_binding_wire_pct?: number;
  steel_chairs?: number;
  steel_chairs_kg_per_m2?: number;
  ring_dense_default?: number;
  ring_dense_spacing_mm?: number;
  shoring_from_depth_mm?: number;
  stair_formwork_soffit_only?: number;
  formwork_shared_walls?: number;
  formwork_shared_beams?: number;
  formwork_joints?: number;
  formwork_lintel_bearing_mm?: number;
  rcc_wall_reveals?: number;
  beam_lintel_qs_rate?: number;
  plaster_thickness_mm?: number;
  soil_stabilisation?: number;
  soil_stab_depth_mm?: number;
  soil_stab_cement_pct?: number;
}

export type DerivedParamName = keyof DerivedParams;

export interface DerivedParamUsed {
  value: number;
  source: "user" | "convention" | "qs" | "default";
}

export interface DerivedClaimWaiting {
  measurement_id: string;
  candidate_id: string;
  tag: string | null;
  marks: number;
  page_no: number;
}

export interface DerivedClaims {
  used: number;
  waiting: number;
  ignored: Record<string, number>;
  waiting_list: DerivedClaimWaiting[];
  footing_bottom_below_ngl_mm: number | null;
  footing_bottom_below_ngl_source?: "user" | "convention" | null;
}

export interface DerivedPdfSource {
  measurement_id: string;
  candidate_id: string;
  sheet_id: string;
  page_no: number;
  tag: string | null;
  instance: number;
  instances: number;
  position_basis: "MARK";
  position_mm: [number, number];
  size_mm: [number, number, number];
  bottom_below_ngl_mm: number;
  view: string;
}

export interface FormworkSource {
  measurement_id: string;
  candidate_id: string;
  sheet_id: string;
  page_no: number;
  category: string;
  tag: string | null;
  instance: number;
  instances: number;
  size_mm: [number, number, number];
  faces: { name: string; m2: string }[];
  shared_faces?: { face: string; by: string; m2: string }[];
  model_element?: boolean;
}

export interface SteelLine {
  kind: "bars" | "rings" | "mesh";
  role: string;
  bar?: number | null;
  dia_mm: string;
  count: number;
  cut_length_m: string;
  kg_per_m: string;
  length_m: string;
  kg: string;
}

export interface SteelSource {
  measurement_id: string;
  candidate_id: string;
  sheet_id: string;
  page_no: number;
  category: string;
  tag: string | null;
  instance: number;
  instances: number;
  size_mm: [number, number, number];
  steel?: Record<string, unknown>;
  lines?: SteelLine[];
  bare_kg?: string;
  wastage_pct?: string;
  concrete_m3?: string;
  bars?: { role: string; n: number; bar: number; length_m: string; kg: string }[];
  rings?: { bar: number; spacing_mm: string; count: number; cut_length_m: string; kg: string } | null;
}

export interface DerivedSteelStats {
  enabled: boolean;
  ran?: boolean;
  reason?: string;
  rows?: number;
  kg?: string;
  code?: string;
  by_category?: Record<string, { marks: number; kg: string; bare_kg?: string }>;
  by_diameter?: Record<string, { kg: string; length_m: string }>;
  intensity?: Record<string, SteelIntensity>;
  bare_kg?: string;
  wastage_pct?: string;
  with_5pct_kg?: string;
  skipped?: Record<string, number>;
  params?: Record<string, DerivedParamUsed>;
  assumed?: string[];
  lap_and_wastage_not_added?: boolean;
  estimate?: SteelEstimateStats;
  ring_zone?: SteelRingZoneStats;
  measured_kg?: string;
  total_low_kg?: string;
  total_high_kg?: string;
  estimated_share_pct?: string;
}

export interface SteelEstimateStats {
  enabled: boolean;
  members?: number;
  kg?: string;
  kg_low?: string;
  kg_high?: string;
  by_family?: Record<string, { members: number; kg: string; kg_low: string; kg_high: string; concrete_m3?: string; area_m2?: string }>;
  skipped?: Record<string, number>;
  slab_rule_kg_per_m2?: string | null;
  slab_rule_source?: string | null;
}

export interface SteelIntensity {
  kg: string;
  concrete_m3: string;
  kg_per_m3: string;
  range: [string, string];
  status: "IN_RANGE" | "BELOW_RANGE" | "ABOVE_RANGE";
}

export interface DerivedFormworkStats {
  enabled: boolean;
  ran?: boolean;
  reason?: string;
  rows?: number;
  area_m2?: string;
  code?: string;
  by_category?: Record<string, { marks: number; m2: string; gross_m2?: string }>;
  skipped?: Record<string, number>;
  params?: Record<string, DerivedParamUsed>;
  assumed?: string[];
  contact_not_deducted?: boolean;
  comparison?: { gross_m2: string; slab_soffit_only_m2: string; beam_per_rft_m2: string; beam_net_m2: string };
  joints?: { enabled?: boolean; reason?: string | null; lintels?: number; chajjas_matched?: number; chajjas_unmatched?: number; balconies_matched?: number; balconies_unmatched?: number; uncertain_members?: number; removed_m2?: string; removed_by?: Record<string, string> };
  beam_slab?: { enabled?: boolean; beams_matched?: number; beams_adjusted?: number; beams_unmatched?: number; slabs_with_removal?: number; capped_slabs?: number; uncertain_members?: number; removed_m2?: string };
  shared_faces?: { enabled?: boolean; placed_columns?: number; unplaced_columns?: number; removed_m2?: string; members_with_removal?: number; uncertain_members?: number;
    placed_walls?: number; unplaced_walls?: number; walls_not_square?: number; matched_beams?: number; unmatched_beams?: number; unplaced_beams?: number; removed_by?: Record<string, string> };
  model?: { members?: number; not_box?: number; skipped?: Record<string, number>;
    shared?: { enabled?: boolean; columns_with_removal?: number; beams_matched?: number; beams_adjusted?: number; slabs_with_removal?: number; removed_m2?: string; removed_by?: Record<string, string> } };
}

export interface EarthBalance {
  excavation_m3: string;
  backfill_m3: string;
  buried_m3: string;
  carted_m3: string;
  gap_m3: string;
  closes: boolean;
  structure_below_ground_m3: string;
  structure_outside_trench_m3: string;
  negative_backfill_rows: number;
  floor_fill_m3?: string;
  floor_fill_need_m3?: string;
  surplus_loose_m3?: string;
  fill_reused_m3?: string;
  fill_imported_m3?: string;
  carted_loose_m3?: string;
  fill_reuse_on?: boolean;
  fill_assumed?: string[];
  fill_note?: "NO_FILL_ITEM" | "FILL_REPORTED";
}

export interface DerivedFoundationParam {
  value: number;
  source: "user" | "convention" | "default" | "qs" | "element";
}

export interface DerivedFoundationEntry {
  element_id: string;
  label: string | null;
  role: string;
  bed: string;
  mark: boolean;
  page_no: number | null;
  params: Record<string, DerivedFoundationParam>;
}

export interface DpcStats {
  enabled: boolean;
  ran?: boolean;
  reason?: "NO_PROFILE" | "ALL_ITEMS_IN_MODEL" | "NO_WALL_ON_DPC" | "NO_DPC_LEVEL";
  vertical?: string;
  rows?: number;
  area_m2?: string;
  params?: Record<string, DerivedParamUsed>;
  model?: { walls?: number; doors_taken_out?: number; gross_m2?: string; net_m2?: string; level?: { z_mm: number; source: string }; reason?: string };
  pdf?: { walls?: number; doors_taken_out?: number; net_m2?: string; no_level?: number; no_height?: number };
}

export interface FloorWorksStats {
  enabled: boolean;
  ran?: boolean;
  reason?: string;
  param_source?: string;
  level_id?: string;
  level_how?: "ONLY_LEVEL" | "LOWEST_MEMBERS";
  rooms?: number;
  area_m2?: string;
  rows?: number;
  skipped?: Record<string, string>;
}

export interface WallFoundationStats {
  enabled: boolean;
  ran?: boolean;
  reason?: string;
  param_source?: string;
  rows?: number;
  walls?: number;
  left_alone_going_below_dpc?: number;
  no_footprint?: number;
  length_m?: string;
  brick_steps_m3?: string;
  termite_trench_m2?: string;
  membrane_m2?: string;
  classes?: Record<string, { walls: number; length_m: number }>;
  level?: { z_mm: number; source: string };
  step_offset_mm?: number;
  step_heights_mm?: Record<string, number[]>;
  pcc_projection_mm?: number;
  skipped?: Record<string, string>;
}

export interface WallFinishStats {
  enabled: boolean;
  ran?: boolean;
  reason?: string;
  param_source?: string;
  rows?: number;
  walls?: number;
  openings?: number;
  openings_given_to_a_wall?: number;
  plaster_inside_m2?: string;
  plaster_outside_m2?: string;
  openings_deducted_m2?: string;
  sides_from_geometry?: number;
  no_height?: number;
  dpc_level?: { z_mm: number; source: string } | null;
  skipped?: Record<string, string>;
}

export interface RangeStampStats {
  rows: number;
  grades: Record<string, number>;
  stamped: number;
  unbounded: number;
}

export interface RoofDeckStats {
  enabled: boolean;
  ran?: boolean;
  reason?: string;
  param_source?: string;
  rows?: number;
  roofs?: number;
  layers?: string[];
  skipped?: Record<string, string>;
  roof_area_m2?: string;
  membrane_m2?: string;
  coba_m3?: string;
  screed_m2?: string;
  coba_thickness_mm?: string | null;
  coba_thickness_source?: string | null;
  coba_from_drawing_roofs?: number;
  turnup_mm?: string | null;
  turnup_source?: string | null;
  turnup_m2?: string | null;
  turnup_roofs?: number;
  turnup_roofs_without_edge?: number;
}

export interface SteelAllowanceStats {
  enabled: boolean;
  ran?: boolean;
  wire_on?: boolean;
  chairs_on?: boolean;
  reason?: string;
  rows?: number;
  levels?: number;
  reinforcement_kg?: string;
  wire_kg?: string;
  wire_pct?: string | null;
  wire_source?: string | null;
  chairs_kg?: string;
  chairs_kg_per_m2?: string | null;
  chairs_source?: string | null;
  slab_area_m2?: string;
  kg?: string;
  skipped?: Record<string, number>;
  share_of_reinforcement_pct?: string;
}

export interface SteelRingZoneStats {
  enabled: boolean;
  marks?: number;
  dense_spacing_mm?: string | null;
  skipped?: Record<string, number>;
}

export interface AreaWorksStats {

  enabled: boolean;
  ran?: boolean;
  reason?: string;
  param_source?: string;
  rows?: number;
  skipped?: Record<string, string>;
  doors?: number;
  windows?: number;
  door_area_m2?: string;
  window_area_m2?: string;
  no_size?: number;
  roof_slabs?: number;
  no_plan?: number;
  area_m2?: string;
}

export interface OneTotalDecision {
  measurement_id: string;
  tag?: string | null;
  category: string;
  level_id?: string | null;
  members: number;
  matched: number;
  drawing_m3: string;
  state: "COMPLETE" | "PARTIAL" | "NOT_MATCHED";
  used: "MODEL" | "DRAWING" | "BOTH";
  level_name?: string | null;
  rule?: "DRAWING" | "MODEL" | "BOTH" | null;
  reason: string;
  conflict: boolean;
  size_differs: boolean;
  model_m3: string | null;
  drawing_matched_m3?: string;
  difference_pct: string | null;
  by: string | null;
  element_ids: string[];
}

export interface OneTotalDrawingOnly {
  measurement_id: string;
  tag?: string | null;
  category: string;
  members: number;
  drawing_m3: string;
  why: string;
}

export interface OneTotalModelOnly {
  element_id: string;
  mark?: string | null;
  category: string;
  level_id?: string | null;
  model_m3: string;
}

export interface OneTotalNotTrusted {
  category: string;
  level_id?: string | null;
  drawing_members: number;
  model_members: number;
  matched: number;
  share_pct: number;
}

export interface OneTotalKindTotal {
  model_m3: string;
  drawing_m3: string;
  total_m3: string;
  low_m3: string;
  high_m3: string;
  bounded: boolean;
  unbounded_rows?: number;
}

export interface OneTotalStats {
  enabled: boolean;
  ran?: boolean;
  reason?: string;
  prefer?: string;
  tolerance_pct?: string;
  position_tolerance_mm?: number;
  trusted_share_pct?: number;
  pairs_found?: number;
  marks?: number;
  model_members?: number;
  complete?: number;
  partial?: number;
  set_aside_not_matched?: number;
  drawing_only_marks?: number;
  model_only_members?: number;
  conflicts_total?: number;
  used_model?: number;
  used_drawing?: number;
  used_both?: number;
  rules_given?: number;
  rules_applied?: number;
  truncated?: boolean;
  decisions?: OneTotalDecision[];
  conflicts?: OneTotalDecision[];
  drawing_only?: OneTotalDrawingOnly[];
  model_only?: OneTotalModelOnly[];
  not_trusted?: OneTotalNotTrusted[];
  totals?: Record<string, OneTotalKindTotal>;
  alignment?: { group: string; method: string; supporters?: number; compared?: number; [key: string]: unknown }[];
}

export interface PdfVariance {
  work_item_code: string;
  level_id: string | null;
  level_name?: string | null;
  unit: string;
  pdf_quantity: string;
  model_quantity: string;
  variance_pct: string;
  over_tolerance: boolean;
  tolerance_pct?: string;
  rule?: "DRAWING" | "MODEL" | "BOTH" | null;
}

export interface PdfTakeoffStats {
  one_total?: OneTotalStats;
  variances?: PdfVariance[];
  [key: string]: unknown;
}

export interface DerivedStats {
  enabled: boolean;
  balance?: EarthBalance;
  dpc?: DpcStats;
  foundation_list?: DerivedFoundationEntry[];
  element_overrides?: { given: number; applied: number; unmatched: string[] };
  ran?: boolean;
  reason?: string;
  skipped_items?: Record<string, string>;
  params?: Record<string, DerivedParamUsed>;
  ngl?: { z_mm: number; source: "user" | "convention" | "default" | "claim"; note: string };
  skipped?: Record<string, number>;
  foundations?: number;
  rows?: number;
  excavation_m3?: string;
  pcc_m3?: string;
  backfill_m3?: string;
  ballast_m3?: string;
  shoring_m2?: string;
  wall_foundations?: number;
  buried_m3?: string;
  assumed?: string[];
  ngl_assumed?: boolean;
  box_footprints?: number;
  mark_positions?: number;
  claims?: DerivedClaims;
  formwork?: DerivedFormworkStats;
  steel?: DerivedSteelStats;
  floor_works?: FloorWorksStats;
  wall_foundation?: WallFoundationStats;
  wall_finishes?: WallFinishStats;
  opening_area?: AreaWorksStats;
  roof_treatment?: AreaWorksStats;
  roof_deck?: RoofDeckStats;
  steel_allowances?: SteelAllowanceStats;
  shoring_from_depth_mm?: number | null;
  plaster_mortar?: PlasterMortarStats;
  soil_stabilisation?: SoilStabilisationStats;
}

export interface PlasterMortarStats {
  enabled: boolean;
  ran: boolean;
  reason?: string;
  thickness_mm?: string | null;
  thickness_source?: string;
  rows?: number;
  mortar_m3?: string;
}

export interface SoilStabilisationStats {
  enabled: boolean;
  ran: boolean;
  reason?: string;
  depth_mm?: string | null;
  depth_source?: string;
  cement_pct?: number | null;
  rows?: number;
  area_m2?: string;
  volume_m3?: string;
}

export interface LayerStats {
  enabled: boolean;
  rows_split?: number;
  rows_merged?: number;
  rows_not_split?: number;
  rows_mismatch?: number;
  finish_excluded_m3?: string;
  unpriced_m3?: string;
  unpriced_by_family?: Record<string, string>;
}

export interface MaterialStats {
  generic_elements: number;
}

export interface LayerSplitTrace {
  of_m3: string;
  total_thickness_mm: string;
  declared_thickness_mm: string | null;
  excluded_m3: string;
  layers: { material: string; family: string; thickness_mm: string }[];
  family: string;
  billed_thickness_mm: string;
  share: string;
}

export interface WallMaterialStats {
  walls: number;
  concrete: number;
  masonry: number;
  material_unknown: number;
  billed_as_concrete: number;
}

export interface BarMarkResponse {
  id?: string;
  solid_id: string;
  element_id: string | null;
  level_id: string | null;
  mark: string;
  role: string;
  shape_code: string;
  shape_params: Record<string, Num>;
  designation: string | null;
  dia_mm: Num;
  grade: string | null;
  count: number;
  spacing_mm: Num | null;
  cut_len_mm: Num;
  stock_len_mm: Num | null;
  pieces: number;
  lap_count: number;
  lap_len_mm: Num | null;
  total_len_m: Num;
  unit_weight_kg_m: Num;
  total_kg: Num;
  provenance: RebarProvenance;
  confidence: Num;
  review_status: ItemReviewStatus;
  schedule_row_id: string | null;
  trace: { steps: TraceStep[]; row_no?: number; member_mark?: string | null };
  warnings: string[];
}

export type BOQLifecycle =
  | "DRAFT"
  | "CALCULATING"
  | "CALCULATED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "ISSUED"
  | "SUPERSEDED"
  | "ARCHIVED";

export type BOQVersionOrigin = "LEGACY" | "MANUAL" | "ENGINE";

export type BOQItemSourceKind =
  | "LEGACY"
  | "MODEL"
  | "SCHEDULE_IMPORT"
  | "MANUAL"
  | "ESTIMATE"

export type ItemReviewStatus = "OK" | "REVIEW_REQUIRED" | "WAIVED";

export type AdjustmentKind = "DELTA" | "REPLACE";

export type ReviewSeverity = "error" | "warning" | "info";
export type ReviewBlocks = "NONE" | "APPROVAL" | "ISSUE";
export type ReviewStatus = "OPEN" | "RESOLVED" | "WAIVED";

export type CalculationRunStatus =
  | "QUEUED"
  | "RUNNING"
  | "STAGED"
  | "PROMOTED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "SUPERSEDED";

export type RunStageStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "SKIPPED";

export type SolidStatus = "OK" | "REVIEW_REQUIRED" | "REJECTED";

export type LedgerSourceKind =
  | "MODEL"
  | "SCHEDULE_IMPORT"
  | "MANUAL"
  | "ESTIMATE"
  | "DERIVED"
  | "PDF_TAKEOFF";

export type DeductionType =
  | "OVERLAP_ALLOCATION"
  | "EXTENT_TRIMMING"
  | "VOID_DEDUCTION"
  | "MATERIAL_SUBSTITUTION"
  | "MEASUREMENT_CONVENTION";

export type SnapshotPurpose = "APPROVAL" | "ISSUE" | "MANUAL";

export type ExportKind =
  | "MEASUREMENT_SHEET"
  | "STAGE_REPORT"
  | "CONTRACT_BOQ"
  | "PROCUREMENT"
  | "MEASUREMENT_BOOK"
  | "AUDIT_REPORT"
  | "REVISION_COMPARISON"
  | "BBS";

export type NormalizationStatus =
  | "PENDING"
  | "VALID"
  | "WARNING"
  | "INVALID";

export type DeductionKind =
  | "OVERLAP_ALLOCATION"
  | "EXTENT_TRIMMING"
  | "VOID_DEDUCTION"
  | "MATERIAL_SUBSTITUTION"
  | "MEASUREMENT_CONVENTION";

export type TransitionAction =
  | "submit-review"
  | "reopen"
  | "approve"
  | "issue"
  | "archive";

export type Page<T> = CursorPage<T>;

export type GeometryKind =
  | "EXTRUDED_PROFILE" | "AXIS_SWEPT" | "BOX_ONLY" | "QTO_ONLY" | "UNSUPPORTED";

export type FormulaCode =
  | "SOLID_NET_VOLUME" | "OPENING_COUNT"
  | "FINISH_FLOOR_AREA" | "FINISH_CEILING_AREA" | "FINISH_WALL_AREA_NET"
  | "FINISH_DADO_AREA_NET" | "FINISH_SKIRTING_LENGTH_NET"
  | "SCHEDULE_LINE_M3" | "SCHEDULE_LINE_M2" | "SCHEDULE_LINE_M"
  | "SCHEDULE_LINE_KG" | "SCHEDULE_LINE_NOS"
  | "REBAR_BBS_WEIGHT" | "REBAR_RULE_ESTIMATE";

export type DeductionRuleCode =
  | "OPENING_DEDUCT" | "OPENING_PARTIAL" | "OPENING_IGNORED" | "OPENING_SIZE_MISSING"
  | (string & {});

export type RebarProvenance = "IFC_EXACT" | "SCHEDULE_IMPORT" | "MANUAL" | "RULE_ESTIMATE";

export interface TraceStep {
  op: string; 
  [key: string]: unknown;
}

export interface RebarScheduleRow {
  id: string;
  schedule_import_id: string;
  row_no: number;
  page_no: number | null;
  raw_text: string | null;
  member_mark: string | null;
  mark: string | null;
  role: string | null;
  shape_code: string | null;
  shape_params: Record<string, Num>;
  designation: string | null;
  dia_mm: Num | null;
  grade: string | null;
  count: number | null;
  spacing_mm: Num | null;
  cut_len_mm: Num | null;
  declared_total_kg: Num | null;
  level_id: string | null;
  matched_element_id: string | null;
  confidence: Num;
  review_status: RowDecision;
  review_note: string | null;
}

export interface RebarImportDetail {
  schedule_import_id: string;
  row_count: number;
  matched_count: number;
  unmatched_count: number;
  rows: RebarScheduleRow[];
}

export interface RebarRowUpdateRequest {
  member_mark?: string | null;
  mark?: string | null;
  role?: string | null;
  shape_code?: string | null;
  shape_params?: Record<string, number> | null;
  designation?: string | null;
  dia_mm?: number | null;
  grade?: string | null;
  count?: number | null;
  spacing_mm?: number | null;
  cut_len_mm?: number | null;
  level_id?: string | null;
  matched_element_id?: string | null;
  review_status?: RowDecision | null;
  review_note?: string | null;
}

export interface RebarConfirmResponse {
  schedule_import_id: string;
  confirmed_count: number;
  rejected_count: number;
  pending_count: number;
}

export interface RebarShape {
  id: string;
  code: string;
  name: string;
  description: string | null;
  standard: string | null;
  segments: string[];
  bend_spec: number[];
  bend_count: number;
  hook_ends: number;
  is_system: boolean;
  is_active: boolean;
}

export interface BarSize {
  id: string;
  standard: string;
  designation: string;
  grade: string;
  nominal_dia_mm: Num;
  unit_weight_kg_m: Num;
  is_system: boolean;
  is_active: boolean;
}

export interface RebarSummaryRow {
  dia_mm: Num;
  designation: string | null;
  grade: string | null;
  total_len_m: Num;
  total_kg: Num;
  mark_count: number;
}

export interface RebarSummary {
  boq_version_id: string;
  rows: RebarSummaryRow[];
  total_kg: Num;
  tier1_kg: Num;
  tier2_kg: Num;
  tier3_estimate_kg: Num;
  bbs_exportable: boolean;
}

export interface QuantityRange {
  likely: number;
  low: number;
  high: number;
  low_pct: number | null;
  high_pct: number | null;
  rows: number;
  bounded_rows: number;
  unbounded_rows: number;
  leaves_out_rows: number;
  complete: boolean;
  weakest: string | null;
  mix: Record<string, number>;
}

export interface RangeTotal {
  unit: string;
  likely: number;
  low: number;
  high: number;
  items: number;
  unbounded: number;
  leaves_out: number;
}

export interface StageReportItem {
  name: string | null;
  code: string | null;
  unit: string;
  quantity: string;
  quantity_range: QuantityRange | null;
  derived: boolean;
  weakest: string | null;
  review_status: string;
  item_id: string;
}

export interface StageReportTrade {
  trade: string;
  items: StageReportItem[];
  totals: RangeTotal[];
}

export interface StageReportStage {
  stage: string;
  label: string;
  trades: StageReportTrade[];
  totals: RangeTotal[];
}

export interface StageReport {
  stages: StageReportStage[];
  totals: RangeTotal[];
}

export type MarkState = "confirmed" | "reopened" | "changed" | "gone";

export interface DriverMark {
  measurement_id: string;
  sheet_id: string | null;
  drawing_id: string | null;
  project_id: string | null;
  candidate_id: string | null;
  page_no: number | null;
  tag: string | null;
  rows: number;
  item_count: number;
  items: string[];
  state: MarkState;
  weight: number;
}

export interface ConfirmMark extends Omit<DriverMark, "weight"> {
  share_pct: number;
  low_after: number;
  high_after: number;
  narrows_pct: number;
  cum_low: number;
  cum_high: number;
}

export interface OpenMark extends Omit<DriverMark, "weight"> {
  quantity: number;
  share_of_quantity_pct: number | null;
}

export interface ConfirmFirst {
  marks: ConfirmMark[];
  total_marks: number;
  halved_after: number | null;
  unmarked_share_pct: number;
}

export interface OpenMarks {
  marks: OpenMark[];
  total_marks: number;
  unmarked_quantity: number;
}

export interface RangeStale {
  marks: number;
  gone: number;
  reopened: number;
  changed: number;
}

export interface RangeDriverItem {
  item_id: string;
  name: string | null;
  swing: number;
}

export interface RangeDriver {
  name: string;
  basis: string;
  rows: number;
  items: number;
  swing_down: number;
  swing_up: number;
  share_pct: number;
  low_after: number;
  high_after: number;
  marks?: DriverMark[];
  top_items: RangeDriverItem[];
}

export interface RangeOpenInput {
  name: string;
  rows: number;
  items: number;
  quantity: number;
  share_of_quantity_pct: number | null;
  marks?: DriverMark[];
  top_items: RangeDriverItem[];
}

export interface RangeDriversUnit {
  unit: string;
  likely: number;
  low: number;
  high: number;
  rows: number;
  bounded_rows: number;
  unbounded_rows: number;
  no_range_rows: number;
  leaves_out_rows: number;
  drivers: RangeDriver[];
  open_inputs: RangeOpenInput[];
  confirm_first?: ConfirmFirst;
  open_marks?: OpenMarks;
}

export interface RangeDrivers {
  units: RangeDriversUnit[];
  stale?: RangeStale;
}

export interface ValueAtRiskTotals {
  likely: number;
  low: number;
  high: number;
  worst_low: number;
  worst_high: number;
  swing_down: number;
  swing_up: number;
  priced_items: number;
  unpriced_items: number;
  behind_assumption: number;
  behind_assumption_pct: number | null;
  open_amount: number;
  open_amount_pct: number | null;
  minimum_amount: number;
  ungraded_amount: number;
  typed_amount: number;
  labour_left_out: number;
}

export interface ValueAtRiskGrade {
  grade: string;
  amount: number;
  items: number;
  share_pct: number | null;
}

export interface ValueAtRiskLine {
  item_id: string;
  name: string | null;
  unit?: string | null;
  amount?: number;
  down?: number;
  up?: number;
  weakest?: string;
  quantity?: number;
}

export interface ValueAtRiskFlag {
  code: string;
  text: string;
  items: number;
  amount: number | null;
  top_items: ValueAtRiskLine[];
}

export interface ValueAtRisk {
  totals: ValueAtRiskTotals;
  by_grade: ValueAtRiskGrade[];
  top_swing: ValueAtRiskLine[];
  top_open: ValueAtRiskLine[];
  unpriced: ValueAtRiskLine[];
  flags: ValueAtRiskFlag[];
}


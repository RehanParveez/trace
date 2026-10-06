export type DrawingFormat = "IFC" | "PDF" | "DWG" | "DXF" | "RVT";
export type DrawingStatus = "UPLOADED" | "PROCESSING" | "PARSED" | "FAILED";
export type BOQItemStatus = "DRAFT" | "APPROVED";
export type BOQItemType = "MATERIAL" | "LABOUR" | "CUSTOM";
export type BOQVersionStatus = "ACTIVE" | "SUPERSEDED";
export type BOQItemRateSource = "LIBRARY" | "AI_SUGGESTED" | "MANUAL";
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
  canonical_unit?: string | null;
  unit_factor?: number | string | null;
  adjustment_total?: number | string;
  review_status?: ItemReviewStatus;
  source_kind?: BOQItemSourceKind;
  is_manual?: boolean;
  calculation_run_id?: string | null;
  engine_version?: string | null;
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
}

export interface BOQItemUpdateRequest {
  version: number;
  material_name?: string;
  category?: string | null;
  unit?: string;
  quantity?: number;
  unit_rate?: number | null;
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
}

export interface MaterialLibraryCreateRequest {
  raw_text: string;
  normalized_name: string;
  category?: string | null;
  default_unit?: string | null;
  default_rate?: number | null;
}

export interface MaterialLibraryUpdateRequest {
  normalized_name?: string;
  category?: string | null;
  default_unit?: string | null;
  default_rate?: number | null;
}

export interface LabourRate {
  id: string;
  trade: string;
  unit: string;
  rate: number | string;
}

export interface LabourRateCreateRequest {
  trade: string;
  unit: string;
  rate: number;
}

export interface LabourRateUpdateRequest {
  trade?: string;
  unit?: string;
  rate?: number;
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
}

export interface CalculationRun {
  id: string;
  organization_id?: string;
  project_id: string;
  requested_by_user_id?: string | null;
  rule_set_id?: string;
  convention_code?: string | null;
  drawing_revision_ids?: string[];
  engine_version: string;
  fingerprint?: string;
  status: CalculationRunStatus;
  progress_pct: number;
  started_at?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  settings?: Record<string, unknown>;
  stats?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
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
  stats: Record<string, unknown>;
  created_at: string;
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
}

export interface RunStageResponse {
  stage: string;
  status: RunStageStatus;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  counts: Record<string, unknown>;
  error: string | null;
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
  source_kind: LedgerSourceKind;
  confidence: number | string;
  formula_code: string;
  trace: Record<string, unknown>;
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
  confidence: number | string;
  formula_code: string;
  trace: Record<string, unknown>;
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

export interface DrawingIngestionMeta {
  reader_version?: string;
  ifc_schema?: string;
  length_unit_scale?: number;
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
  amount: number | string | null;
  confidence: number | string | null;
  review_status: string;
  source_kind: string;
  ledger_row_count: number;
  ledger_hash: string | null;
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
  steps: Record<string, unknown>[];
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
  | "ESTIMATE";

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
  | "ESTIMATE";

export type DeductionType =
  | "OVERLAP_ALLOCATION"
  | "EXTENT_TRIMMING"
  | "VOID_DEDUCTION"
  | "MATERIAL_SUBSTITUTION"
  | "MEASUREMENT_CONVENTION";

export type SnapshotPurpose = "APPROVAL" | "ISSUE" | "MANUAL";

export type ExportKind =
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
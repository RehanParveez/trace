export type Pt = [number, number];
export type LengthUnit = "mm" | "cm" | "m" | "ft" | "in";
export type ContentKind = "VECTOR" | "RASTER" | "UNKNOWN";
export type PrepStatus = "PENDING" | "READY" | "FAILED";
export type MeasureKind = "LENGTH" | "AREA" | "COUNT";
export type ReconMode = "AUTO" | "ADD" | "REPLACE_MODEL" | "VERIFY_ONLY";
export type MeasureSource = "MANUAL" | "VECTOR_SNAP" | "TAG_SCAN";
export type MeasureStatus = "DRAFT" | "CONFIRMED";
export type SnapKind = "ENDPOINT" | "INTERSECTION" | "MIDPOINT" | "EDGE";
export type DimsBasis = "DRAWN" | "SPECIFIED" | "ASSUMED";
export type OpeningRole = "DOOR" | "WINDOW" | "OPENING";

export interface LengthGeometry { points: Pt[]; closed: boolean }
export interface AreaGeometry { outer: Pt[]; holes: Pt[][] }
export interface CountGeometry { points: Pt[] }
export type Geometry = LengthGeometry | AreaGeometry | CountGeometry;

export interface KnownDistance { p1: Pt; p2: Pt; value: string; unit: LengthUnit }

export interface TakeoffSheet {
  id: string;
  drawing_id: string;
  page_no: number;
  width_pt: string;
  height_pt: string;
  rotation: number;
  content_kind: ContentKind;
  label: string | null;
  level_id: string | null;
  scale_text: string | null;
  detected_scale: Record<string, unknown>;
  prep_status: PrepStatus;
  prep_error: string | null;
  text_chars: number | null;
  vector_ops: number | null;
  stale?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CalibrationWarning { code?: string; message?: string; [key: string]: unknown }

export interface TakeoffCalibration {
  id: string;
  sheet_id: string;
  method: "TWO_POINT" | "SCALE_RATIO";
  ref: Record<string, unknown>;
  check_ref: Record<string, unknown> | null;
  ratio: string | null;
  label: string | null;
  is_default: boolean;
  usable: boolean;
  reason: string | null;
  mm_per_pt: string | null;
  check_error_pct: string | null;
  baseline_pt: string | null;
  quality_factor: string;
  warnings: Array<string | CalibrationWarning>;
  created_at: string;
  updated_at: string;
  measurements_recomputed?: number;
  measurements_reverted_to_draft?: number;
}

export interface OpeningParam { role: OpeningRole; width_mm: string | number; height_mm: string | number; nos: number; label?: string | null }
export interface AdjustmentParam { op: "LESS" | "ADD"; value: string | number; label?: string | null }

export interface MeasurementParams {
  height_mm?: string | number | null;
  thickness_mm?: string | number | null;
  width_mm?: string | number | null;
  depth_mm?: string | number | null;
  length_mm?: string | number | null;
  openings?: OpeningParam[];
  adjustments?: AdjustmentParam[];
  repeat?: number;
  dims_basis?: DimsBasis;
}

export interface ComputedResult {
  quantity?: string;
  unit?: string;
  formula?: string;
  confidence?: string;
  uncertainty_pct?: string;
  warnings?: string[];
  steps?: Array<Record<string, unknown>>;
  inputs?: Record<string, unknown>;
  error?: { code: string; message: string };
}

export interface TakeoffMeasurement {
  id: string;
  sheet_id: string;
  project_id: string;
  calibration_id: string | null;
  kind: MeasureKind;
  quantity_mode: string;
  geometry: Geometry;
  params: MeasurementParams;
  work_item_code: string | null;
  level_id: string | null;
  label: string | null;
  tag: string | null;
  material_grade: string | null;
  recon_mode: ReconMode;
  source: MeasureSource;
  status: MeasureStatus;
  geometry_hash: string | null;
  computed: ComputedResult | null;
  last_result: Record<string, unknown> | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TakeoffOverview {
  drawing_id: string;
  sheets: TakeoffSheet[];
  calibrations: TakeoffCalibration[];
  measurements: TakeoffMeasurement[];
  summary: { sheets: number; calibrated_sheets: number; measurements: number; confirmed: number; draft: number };
}

export interface ModeOption { kind: MeasureKind; quantity_mode: string; output_unit: string; required_params: string[]; formula_code: string }

export interface PreviewRequest {
  sheet_id: string;
  kind: MeasureKind;
  quantity_mode: string;
  geometry: Geometry;
  params: MeasurementParams;
  calibration_id?: string | null;
  source?: MeasureSource;
}

export interface PreviewResult extends ComputedResult {
  ok: boolean;
  quantity?: string;
  error?: { code: string; message: string };
}

export interface MeasurementCreate {
  kind: MeasureKind;
  quantity_mode: string;
  geometry: Geometry;
  params: MeasurementParams;
  calibration_id?: string | null;
  work_item_code?: string | null;
  level_id?: string | null;
  label?: string | null;
  tag?: string | null;
  material_grade?: string | null;
  recon_mode?: ReconMode;
  source?: MeasureSource;
}

export type MeasurementUpdate = Partial<Omit<MeasurementCreate, "kind" | "source">>;

export interface CalibrationCreate {
  method: "TWO_POINT" | "SCALE_RATIO";
  reference?: KnownDistance | null;
  scale_text?: string | null;
  ratio?: string | number | null;
  check?: KnownDistance | null;
  label?: string | null;
  make_default?: boolean;
}

export interface BulkConfirmResult { confirmed: string[]; failed: Array<{ id?: string; measurement_id?: string; code?: string; message?: string }> }

export interface PrepareResult {
  drawing_id: string;
  prepared: string[];
  skipped: string[];
  failed: Array<{ sheet_id?: string; message?: string; code?: string }>;
  remaining: number;
  elapsed_seconds: number;
  sheets: TakeoffSheet[];
}

export interface ScalePair {
  text: string;
  p1: Pt;
  p2: Pt;
  length_pt: number;
  value_mm: number;
  reading_unit?: string;
  quality: number;
  ends?: string;
  inlier: boolean;
  drawn_mm?: number;
  deviation_pct?: number;
}

export interface ScaleCluster { ratio: number; support: number; spread_pct: number; weight: number; bbox?: number[] }

export interface ScaleRecommendation {
  method: "SCALE_RATIO" | "TWO_POINT";
  ratio: number;
  scale_text: string;
  basis: string;
  trust: number;
  check?: { p1: Pt; p2: Pt; value: string; unit: string; text?: string; length_pt?: number } | null;
  support?: number;
}

export interface ScaleNote { code: string; severity?: string; message?: string; [key: string]: unknown }

export interface DetectedScale {
  version?: number;
  declared?: {
    candidates?: Array<{ text: string; ratio: number; labelled?: boolean; zone?: string }>;
    primary?: { text: string; ratio: number; trust?: number; ambiguous?: boolean } | null;
    multi_scale?: boolean;
    not_to_scale?: boolean;
  };
  measured?: { pairs_found?: number; clusters?: ScaleCluster[]; pairs?: ScalePair[] };
  agreement?: string;
  recommended?: ScaleRecommendation | null;
  notes?: ScaleNote[];
  units_hint?: string;
  paper?: { name?: string; width_mm?: number; height_mm?: number; orientation?: string; standard?: boolean; nearest?: string; error_pct?: number };
}

export interface SheetAnalysis {
  sheet_id: string;
  prep_status: PrepStatus;
  stale: boolean;
  content_kind: ContentKind;
  detected_scale: DetectedScale;
  meta: Record<string, unknown>;
}

export interface AutoCalibrateResult {
  calibration: TakeoffCalibration;
  additional: TakeoffCalibration[];
  created: boolean;
  recommendation: Record<string, unknown>;
  notes: ScaleNote[];
}

export type VectorSegment = [number, number, number, number, number];

export interface VectorResult { bbox: number[]; segments: VectorSegment[]; total: number; truncated: boolean }

export interface SnapResult { input: number[]; snapped: boolean; x?: number; y?: number; kind?: SnapKind; distance?: number }

export interface WallPick {
  run: Pt[];
  partner: boolean | null;
  centreline?: Pt[];
  overlap?: number;
  offset_pt?: number;
  thickness_mm?: number;
  suggested_thickness_mm?: number;
  note?: string;
}

export interface RegionPick { outer: Pt[]; area_pt2: number; perimeter_pt: number; holes: Array<{ ring: Pt[]; area_pt2: number }> }

export interface PickResult {
  snap: { x: number; y: number; kind: SnapKind; distance: number } | null;
  wall: WallPick | null;
  region: RegionPick | null;
  labels: Array<{ text: string; x: number; y: number; distance: number }>;
  mm_per_pt: string | null;
}

export interface TextWord { text: string; x: number; y: number; angle: number; size: number }
export interface TextResult { total: number; words: TextWord[]; truncated: boolean }

export interface TagSummary { tag: string; count: number; in_drawing: number }

export interface CountSuggestion {
  kind: "COUNT";
  quantity_mode: "DIRECT";
  geometry: CountGeometry;
  source: "TAG_SCAN" | "VECTOR_SNAP";
  tag: string | null;
  label: string;
}

export interface TagDetail { tag: string; count: number; in_drawing: number; points: Array<{ x: number; y: number }>; suggestion: CountSuggestion; note: string | null }

export interface ShapeSummary { id: string; shape: string; a_pt: number; b_pt: number; a_mm: number | null; b_mm: number | null; count: number; filled: number }
export interface ShapeList { shapes: ShapeSummary[]; mm_per_pt: string | null }
export interface ShapeDetail { shape: ShapeSummary; points: number[][]; suggestion: CountSuggestion }

export interface ProjectTakeoffDrawing {
  drawing_id: string;
  original_filename: string;
  revision_label: string | null;
  is_current_revision: boolean;
  sheets: number;
  prepared_sheets: number;
  calibrated_sheets: number;
  draft: number;
  confirmed: number;
}

export interface ReconciliationRow {
  measurement_id: string;
  sheet_id?: string;
  label?: string | null;
  tag?: string | null;
  kind?: string;
  decision?: "COUNTED" | "VERIFIED" | "REPLACED_MODEL" | "SKIPPED";
  reason?: string | null;
  message?: string | null;
  work_item_code?: string | null;
  quantity?: string;
  unit?: string;
  model_quantity?: string | null;
  variance_pct?: string | null;
  confidence?: string;
  warnings?: string[];
  mode?: string;
}

export interface ReconciliationStats {
  measurements?: number;
  counted?: number;
  verified?: number;
  skipped?: Record<string, number>;
  variances?: unknown;
  not_counted?: Array<{ work_item_code: string; level_id: string | null; measurements: number }>;
  replaced?: Array<{ work_item_code: string; level_id: string | null; rows_dropped: number; model_quantity: string }>;
  tolerance_pct?: string;
}

export interface Reconciliation { run_id: string | null; stats: ReconciliationStats; measurements: ReconciliationRow[] }

export type CandidateCategory = "COLUMN" | "FOOTING" | "BEAM" | "DOOR" | "WINDOW" | "WALL" | "ROOM";
export type CandidateStatus = "VALID" | "WARNING" | "INVALID";
export type CandidateDecision = "NEW" | "ACCEPTED" | "REJECTED";

export interface CandidateNote { code: string; severity: "info" | "warning" | "error"; message: string; [extra: string]: unknown }

export interface TakeoffCandidate {
  id: string;
  sheet_id: string;
  category: CandidateCategory;
  kind: MeasureKind;
  quantity_mode: string;
  label: string;
  tag: string | null;
  geometry: Geometry;
  params: Record<string, unknown>;
  missing: string[];
  suggested_work_item: string | null;
  count: number;
  status: CandidateStatus;
  confidence: string;
  facts: Record<string, unknown>;
  notes: CandidateNote[];
  source: MeasureSource;
  decision: CandidateDecision;
  measurement_id: string | null;
  decided_at: string | null;
  mm_per_pt: string | null;
}

export type StaleReason = "SCALE_CHANGED" | "SHEET_READ_AGAIN" | "NEWER_LOGIC";

export interface ExtractionMeta {
  sheet_id: string;
  ran: boolean;
  ran_at?: string | null;
  stale: boolean;
  stale_reasons: StaleReason[];
  mm_per_pt?: string | null;
  scale_unverified: boolean;
  stats: Record<string, unknown>;
  unmapped_tags: Array<{ tag: string; count: number }>;
  notes: CandidateNote[];
}

export interface CandidateSummary {
  total: number;
  new: number;
  accepted: number;
  rejected: number;
  warnings: number;
  by_category: Record<string, { found: number; new: number; accepted: number; rejected: number }>;
}

export interface CandidateList { sheet_id: string; extraction: ExtractionMeta; candidates: TakeoffCandidate[]; summary: CandidateSummary }
export interface ExtractResult extends CandidateList { added: number; updated: number; removed: number; calibration_created: boolean }

export interface AcceptBody {
  ids: string[];
  wall_height_mm?: number | null;
  column_height_mm?: number | null;
  footing_depth_mm?: number | null;
  work_items?: Record<string, string>;
}
export interface CandidateFailure { id: string; code: string; message: string }
export interface AcceptResult { accepted: Array<{ id: string; measurement_id: string; work_item_code: string | null }>; failed: CandidateFailure[] }
export interface DecideResult { changed: string[]; failed: CandidateFailure[] }
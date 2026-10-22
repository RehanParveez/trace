export type Pt = [number, number];
export type LengthUnit = "mm" | "cm" | "m" | "ft" | "in";
export type ContentKind = "VECTOR" | "RASTER" | "UNKNOWN";
export type PrepStatus = "PENDING" | "READY" | "FAILED";
export type MeasureKind = "LENGTH" | "AREA" | "COUNT";
export type ReconMode = "AUTO" | "ADD" | "REPLACE_MODEL" | "VERIFY_ONLY";
export type MeasureSource = "MANUAL" | "VECTOR_SNAP" | "TAG_SCAN" | "PRINTED";
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

export interface ApproveReadyBody {
  accept_assumed?: boolean;
  accept_warned?: boolean;
  accept_added?: boolean;
  confirm?: boolean;
  dry_run?: boolean;
  batch?: number;
  exclude_ids?: string[];
  typed?: Record<string, number>;
}

export interface ApproveReadyResult {
  drawing_id: string;
  dry_run: boolean;
  floors_chosen: Array<{ floor: string; sheet_id?: string; page_no?: number; set_aside?: number; restored?: number }>;
  floors_pending: number;
  would_accept: number;
  would_confirm: number | null;
  accepted: number;
  accept_failed: Array<{ id: string; code: string; message: string }>;
  failed_ids: string[];
  failed_by_code: Record<string, number>;
  confirmed: number;
  confirm_failed: Array<{ id?: string; code?: string; message?: string }>;
  already_decided: number;
  skipped_by_reason: Record<string, number>;
  remaining: number;
  confirmed_total: number;
  draft_total: number;
}

export interface PrepareResult {
  drawing_id: string;
  prepared: string[];
  skipped: string[];
  failed: Array<{ sheet_id?: string; page_no?: number; message?: string; code?: string }>;
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

export type CandidateCategory = "COLUMN" | "FOOTING" | "BEAM" | "DOOR" | "WINDOW" | "WALL" | "ROOM" | "SLAB" | "LINTEL" | "STAIR" | "SITE";
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
export interface ExtractResult extends CandidateList { added: number; updated: number; removed: number; calibration_created: boolean;
  
  floors_chosen?: Array<{ floor: string; sheet_id: string; page_no: number; set_aside: number; restored: number }> }

export interface AcceptBody {
  ids: string[];
  steel?: Record<string, import("../utils/steel").SteelSet>;
  wall_height_mm?: number | null;
  tank_wall_height_mm?: number | null;
  column_height_mm?: number | null;
  neck_height_mm?: number | null;
  section_picks?: Record<string, string>;
  footing_depth_mm?: number | null;
  slab_thickness_mm?: number | null;
  beam_depth_mm?: number | null;
  plinth_beam_depth_mm?: number | null;
  tie_band_depth_mm?: number | null;
  excavation_depth_mm?: number | null;
  fill_depth_mm?: number | null;
  trench_depth_mm?: number | null;
  pcc_thickness_mm?: number | null;
  pcc_strip_width_mm?: number | null;
  pcc_strip_width_thin_mm?: number | null;
  brick_step_1_height_mm?: number | null;
  brick_step_2_height_mm?: number | null;
  brick_step_3_height_mm?: number | null;
  brick_step_4_height_mm?: number | null;
  brick_step_offset_mm?: number | null;
  membrane_width_mm?: number | null;
  door_frame_width_mm?: number | null;
  door_frame_width_thin_mm?: number | null;
  stair_waist_mm?: number | null;
  site_length_mm?: number | null;
  site_width_mm?: number | null;
  site_height_mm?: number | null;
  site_thickness_mm?: number | null;
  work_items?: Record<string, string>;
}

export interface CandidateFailure { id: string; code: string; message: string }
export interface AcceptResult { accepted: Array<{ id: string; measurement_id: string; work_item_code: string | null }>; failed: CandidateFailure[] }
export interface DecideResult { changed: string[]; failed: CandidateFailure[] }
export interface DrawingExtractSkipped { sheet_id: string; page_no: number; code: string; message: string }
export interface DrawingExtractResult { drawing_id: string; done: ExtractResult[]; skipped: DrawingExtractSkipped[] }

export type SheetAction = "READ_SHEETS" | "CONFIRM_SCALE" | "MEASURE_BY_HAND" | "REPORT_PROBLEM" | "NONE";
export interface RegisterWaiting { page_no: number; sheet_id: string; reason: "NOT_PREPARED" | "NOT_READ" ; error?: string | null; code?: string | null; message?: string | null; action?: SheetAction }
export interface RegisterSetAside { page_no: number; sheet_id: string; code: string | null; message: string | null }
export type SheetReadStatus = "READ" | "SET_ASIDE" | "WAITING" | "NOT_PREPARED";

export interface RegisterSheetStatus {
  page_no: number;
  sheet_id: string;
  title: string | null;
  level: string | null;
  status: SheetReadStatus;
  items: number;
  code: string | null;
  message: string | null;
  severity: "INFO" | "ACTION" | null;
  action?: SheetAction;
  composite: boolean;
}
export type FactKind = "SLAB_THICKNESS" | "RCC_WALL_THICKNESS" | "BRICK_COLUMN" | "CONCRETE_CLASS" | "STEEL_GRADE" | "CLEAR_COVER" | "BEARING_CAPACITY" | "PLASTER_THICKNESS" | "FILL_LAYER" | "STAIR_WIDTH" | "SOIL_STABILISATION";
export interface DrawingFact {
  kind: FactKind;
  scope: string | null;
  text: string;
  count: number;
  pages: number[];
  value_mm?: number | null;
  value2_mm?: number | null;
  value?: number | null;
  unit?: string | null;
  grade?: number | null;
  concrete_class?: string | null;
  mix?: string | null;
  where?: string | null;
  cement_pct?: number | null;
  loose?: boolean | null;
}
export interface DrawingFactConflictValue {
  value_mm: number | null;
  value: number | null;
  unit: string | null;
  scopes: string[];
  pages: number[];
  text: string;
}
export interface DrawingFactConflict { kind: FactKind; name: string; values: DrawingFactConflictValue[] }
export type ScheduleOpeningType = "DOOR" | "WINDOW" | "VENTILATOR" | "OPENING";

export interface ScheduleOpening {
  mark: string;
  type: ScheduleOpeningType | string;
  width_mm: number;
  height_mm: number;
  area_m2: number;
  text?: string | null;
  pages: number[];
}

export interface ScheduleArea { key: string; kind: string; name: string; value: number; unit: string; m2: number; pages: number[]; dims_mm?: number[] | null; dims_text?: string | null }
export interface ScheduleConflict { kind: "OPENING_SIZE" | "FLOOR_AREA" | "LINTEL_SIZE" | string; name: string; values: Array<{ width_mm?: number; height_mm?: number; depth_mm?: number; m2?: number; value?: number; pages: number[] }> }
export interface LintelBars { n: number; bar: number }
export interface LintelSteel { bottom?: LintelBars; top?: LintelBars; bars?: LintelBars; ring?: { bar: number; spacing_mm: number } }
export interface ScheduleLintel { span_max_ft: number; span_max_mm: number; width_mm: number; depth_mm: number; text?: string | null; steel?: LintelSteel | null; pages: number[] }
export interface ScheduleStair { riser_mm?: number | null; tread_mm?: number | null; width_mm?: number | null; steps?: number | null; waist_mm?: number | null; text?: string | null; pages: number[] }
export interface ScheduleTieBand { text: string; pages: number[] }
export interface ProjectionSide { width_mm: number; text?: string | null; pages: number[] }
export interface FloorProjections {
  sides: Record<string, ProjectionSide>;
  unplaced: Array<{ text: string; width_mm: number; page: number }>;
  conflicts: Array<{ side: string; widths_mm: number[]; pages: number[] }>;
  dims: Array<{ mm: number; axis: "H" | "V"; pages: number[] }>;
}
export interface DrawingSchedule { openings: ScheduleOpening[]; areas: ScheduleArea[]; lintels?: ScheduleLintel[]; tie_band?: ScheduleTieBand | null; stair?: ScheduleStair | null; projections?: Record<string, FloorProjections>; conflicts: ScheduleConflict[] }
export type FloorCheckStatus = "OK" | "LOW" | "HIGH" | "NOT_READ";

export interface FloorCheck {
  key: string;
  name: string;
  covered_m2: number;
  status: FloorCheckStatus;
  message: string | null;
  pages: number[];
  rooms: number;
  rooms_m2: number;
  coverage_pct: number | null;
  doors: number;
  windows: number;
  ventilators: number;
  openings_m2: number;
  walls_m: number;
  wall_height_mm: number | null;
  wall_height_basis: string | null;
  brick_9_m2: number;
  brick_45_m2: number;
  rcc_m2: number;
  columns: number;
  footings: number;
  beams: number;
  slab_panels: number;
  slab_thickness_mm: number | null;
}

export interface StructureMark {
  tag: string | null;
  count: number;
  size_mm: Array<number | null> | null;
  status?: string | null;
  size_source?: "SCHEDULE" | "DETAIL" | "PLAN" | null;
  warnings?: string[];
}
export interface ColumnDetail {
  mark: string;
  caption?: string | null;
  page_no?: number | null;
  read: "OCR" | "OCR_SQUARE" | "PARTIAL" | "NONE";
  w_in: number | null;
  h_in: number | null;
}
export type PictureReadState = "TEXT" | "TEXT+OCR" | "OCR" | "PARTIAL" | "NONE" | "TIMEOUT" | "FAILED";
export interface BeamSectionRead {
  mark: string | null;
  kind: string | null;
  page_no: number | null;
  read: PictureReadState;
  depth_in: number | null;
  steel_text: string | null;
  from_text: boolean;
}
export interface TankSizeRead { text: string | null; source: "TEXT" | "PICTURE"; votes: number | null }
export interface TankDrawingRead {
  kind: string | null;
  view: string | null;
  caption: string | null;
  page_no: number | null;
  read: PictureReadState;
  sizes: TankSizeRead[];
  bar_notes: string[];
  from_text: boolean;
}
export interface PictureReaderStatus { installed: boolean; version: string | null; packages: boolean; usable: boolean }
export interface DrawingCheck {
  code: string;
  severity: "warning" | "info";
  title: string;
  message: string;
  marks: string[];
  pages: number[];
}

export interface StructureLevel {
  key: string;
  name: string;
  columns: number;
  footings: number;
  beams: number;
  column_marks: StructureMark[];
  footing_marks: StructureMark[];
  beam_marks: StructureMark[];
  slab_panels: number;
  slab_thickness_mm: number | null;
  pages: number[];
}
export interface SheetView {
  page_no: number;
  key: string;
  kind: string | null;
  caption: string | null;
  level_hint: string | null;
  structural: boolean;
  foundation: boolean;
  scale_ratio: number | null;
  scale_support: number | null;
  slab_note_mm: number | null;
  slab_panels: number;
}
export interface SuggestedWallHeight {
  value_mm: number;
  floor_to_floor_mm: number;
  slab_mm: number;
  basis: string;
  alternatives: Array<{ slab_mm: number; value_mm: number; pages: number[] }>;
}

export interface FloorWallHeight { clear_mm: number; floor_to_floor_mm: number | null; basis: "SECTION" | "LEVEL_MARKS" | "TYPICAL" | string; level_mm?: number | null }
export interface DrawingStoreys { consistent: boolean; page_no?: number; clusters: Array<{ clear_mm: number; count: number; agree: number; below_ground: boolean }> }
export interface DrawingSuggest { wall_height?: SuggestedWallHeight | null; wall_height_by_floor?: Record<string, FloorWallHeight> }

export interface DrawingFacts {
  drawing_id: string;
  sheets_read: number;
  sheets_total: number;
  items: DrawingFact[];
  conflicts: DrawingFactConflict[];
  ladder: { levels_mm: number[]; gaps_mm: number[]; typical_floor_to_floor_mm: number | null };
  storeys?: DrawingStoreys | null;
  suggest?: DrawingSuggest;
  schedule?: DrawingSchedule;
  floors?: FloorCheck[];
  views?: SheetView[];
  structure?: StructureLevel[];
  details?: ColumnDetail[];
  details_reader?: string | null;
  beam_details?: BeamSectionRead[];
  tank_details?: TankDrawingRead[];
  picture_reader?: PictureReaderStatus | null;
  checks?: DrawingCheck[];
}

export interface RegisterSyncResult {
  drawing_id: string;
  total: number;
  added: number;
  updated: number;
  removed: number;
  by_type: Record<string, number>;
  sheets: number;
  sheets_read: number;
  waiting: RegisterWaiting[];
  set_aside: RegisterSetAside[];
  sheet_status: RegisterSheetStatus[];
  measured: number;
  needs_review: number;
  decisions?: number;
  evidence?: Record<string, number>;
  totals?: RangeTotal[];
  source_mix?: Record<string, Record<string, number>>;
  floors_to_decide?: number;
  floors_undecided?: Array<{ floor: string; pages: number[] }>;
}

export interface RangeTotal { unit: string; likely: number; low: number; high: number; rows: number; unbounded: number; leaves_out: number }

export interface FrameMember {
  measurement_id: string;
  instance: number;
  category: string;
  tag: string | null;
  length_mm: number;
  width_mm: number;
  sheet_x_mm: number;
  sheet_y_mm: number;
  x_mm: number | null;
  y_mm: number | null;
}

export type FrameMethod = "REFERENCE" | "COLUMN_MATCH" | "ENVELOPE" | "UNALIGNED" | "MANUAL";

export interface FrameView {
  key: string;
  reference: boolean;
  method: FrameMethod;
  grade: "ASSUMED" | "CONFIRMED";
  dx_mm: number;
  dy_mm: number;
  supporters: number;
  compared: number;
  residual_mm: number;
  confidence: number;
  anchors: number;
  decided: boolean;
  members: FrameMember[];
}

export interface FrameColumnAtPlace { view: string; tag: string | null; length_mm: number; width_mm: number }

export interface FrameColumnIssue {
  code: "COLUMN_TAG_DIFFERS" | "COLUMN_SIZE_DIFFERS";
  x_mm: number;
  y_mm: number;
  grade: "ASSUMED" | "CONFIRMED";
  columns: FrameColumnAtPlace[];
}

export interface FrameColumns { places: number; shared: number; agree: number; issues: FrameColumnIssue[] }

export interface Frame {
  drawing_id: string;
  reference: string | null;
  origin_mm: number[];
  views: FrameView[];
  columns?: FrameColumns;
  status: "NONE" | "ASSUMED" | "CONFIRMED";
  open_views: string[];
  unplaced: string[];
  unconfirmed: string[];
  cleared_placements: number;
}

export interface ReconcilePdfPlace { marks: string[]; views: string[] }
export interface ReconcileModelPlace { names: string[]; element_ids: string[] }
export interface ReconcilePair { pdf: ReconcilePdfPlace; model: ReconcileModelPlace; distance_mm: number }
export interface ReconcileSizeDiffers { pdf: ReconcilePdfPlace; model: ReconcileModelPlace; pdf_size: number[] | null; model_size: number[] | null }
export interface ReconcileModelChoice { drawing_id: string; filename: string; columns: number }

export interface ColumnReconcile {
  drawing_id: string;
  model_drawing_id: string | null;
  models: ReconcileModelChoice[];
  status: "NONE" | "MATCHED" | "UNMATCHED";
  reason: "NO_MODEL" | "NO_PDF_COLUMNS" | null;
  grade: "ASSUMED" | "CONFIRMED";
  method: string;
  dx_mm: number;
  dy_mm: number;
  supporters: number;
  compared: number;
  pdf_places: number;
  model_places: number;
  agrees: boolean;
  pairs: ReconcilePair[];
  pdf_only: ReconcilePdfPlace[];
  model_only: ReconcileModelPlace[];
  size_differs: ReconcileSizeDiffers[];
}

export interface ReconcileQuery { model_drawing_id?: string; dx_mm?: number; dy_mm?: number }

export interface FramePlaceBody { view: string; action: "CONFIRM" | "SET" | "CLEAR"; dx_mm?: number; dy_mm?: number }
export interface FramePlaceBody { view: string; action: "CONFIRM" | "SET" | "CLEAR"; dx_mm?: number; dy_mm?: number }

export type ZGrade = "PRINTED" | "TYPED" | "ASSUMED";

export interface FloorLevel {
  key: string;
  level_mm: number | null;
  clear_mm: number | null;
  floor_to_floor_mm: number | null;
  soffit_mm: number | null;
  top_mm: number | null;
  source: "SECTION" | "LEVEL_MARKS" | "TYPICAL" | "DATUM" | null;
  level_source: "PRINTED_MARK" | "SUM_OF_STOREYS" | "AT_DATUM" | null;
  grade: ZGrade;
  reason: string | null;
}

export type ZDatum = "DRAWING_LEVEL_ZERO" | "GROUND_FLOOR_LEVEL";

export interface FootingLevelState { ngl_mm: number | null; ngl_source: "TYPED" | "LEVEL_MARK" | null; bottom_below_ngl_mm: number | null; usable: boolean }

export interface FloorDatums { drawing_id: string; datum: ZDatum; floors: FloorLevel[]; footing: FootingLevelState }

export interface MemberZ { base_mm: number | null; top_mm: number | null; base_source: string; top_source: string; grade: ZGrade; notes: string[]; floor: string | null; datum: ZDatum | string }

export interface FloorSource {
  sheet_id: string;
  page_no: number;
  from_plans: boolean;
  caption: string | null;
  wall_m: number;
  walls: number;
  items: number;
  open: number;
  accepted: number;
  rejected: number;
  set_aside: boolean;
  combined?: number;
  added?: number;
  added_wall_m?: number;
}

export interface FloorEntry {
  floor: string;
  state: "SINGLE" | "LISTED" | "DOUBLE" | "COMBINED" | "CHOSEN" | "NONE";
  choosable: boolean;
  chosen_sheet_id: string | null;
  suggested_sheet_id: string | null;
  conflict: boolean;
  sources: FloorSource[];
}

export interface FloorSources { drawing_id: string; floors: FloorEntry[]; to_decide: number }

export interface TypedValue { kind: string; field: string; value_mm: number; times: number; at: string }

export interface TypedMemory { drawing_id: string; values: TypedValue[] }

export interface CrossCheck {
  code: string;
  status: "WARN" | "INFO" | "PASS";
  floor: string | null;
  message: string;
  pages: number[];
  numbers: Record<string, unknown>;
}

export interface ReadyItem { id: string; category: string; tag: string | null; floor: string | null; page_no: number; grade: string | null }
export interface HeldItem extends ReadyItem { reasons: Array<{ code: string; message: string }> }
export interface ReadyToAccept { drawing_id: string; ready: ReadyItem[]; held: HeldItem[]; held_by_reason: Record<string, number>; checks_warning: number }

export interface CrossChecks { drawing_id: string; checks: CrossCheck[]; warnings: number; info: number; passed: number }

export interface KnownFact {
  kind: "TOTAL" | "COUNT" | "ROOM_AREA" | "SLAB_AREA" | "SCHEDULE";
  category?: string;
  tag?: string;
  floor?: string;
  count?: number;
  name?: string;
  area_m2?: number;
  mark?: string;
  width_mm?: number;
  height_mm?: number;
  tolerance_pct?: number;
}

export interface FactResult {
  index: number;
  text: string;
  status: "PASS" | "FAIL" | "MISSING";
  expected: unknown;
  found: unknown;
  message: string;
  pages: number[];
}

export interface FactsCheck { drawing_id: string; results: FactResult[]; passed: number; failed: number; missing: number }

/** One rule of the reader that decided something on a sheet, with the basis its numbers stand on. */
export interface TraceRule {
  id: string;
  label: string;
  basis: "TUNED" | "STANDARD" | "DEFAULT";
  items: number;
  notes: number;
  codes: string[];
  examples: string[];
  thresholds: Record<string, number | string>;
}

export interface TraceScale { agreement: string | null; support: number; trust: number | null; gate: string | null; decided_by: string }

export interface TraceSheet { sheet_id: string; page_no: number; scale: TraceScale; rules: TraceRule[]; silent: string[] }

export interface ReaderTrace {
  drawing_id: string;
  sheets: TraceSheet[];
  summary: { sheets: number; tuned_rules_fired: string[]; default_rules_fired: string[]; tuned_items: number };
}

export type FloorChoiceBody = { choices: Array<{ floor: string; sheet_id: string }> } | { use_suggested: true };

export interface FloorChoiceResult {
  chosen: Array<{ floor: string; sheet_id: string; page_no: number; set_aside: number; restored: number }>;
  set_aside: number;
  restored: number;
  blocked: Array<{ floor: string; code: string; message: string }>;
  floors: FloorSources;
}

export interface PlanRead { key: string; caption: string; level_hint: string | null; bbox: number[]; wall_m_found: number; walls: number | null; items: Record<string, number> }
export interface LeftOut { caption: string | null; kind: string | null; bbox: number[]; wall_m: number }
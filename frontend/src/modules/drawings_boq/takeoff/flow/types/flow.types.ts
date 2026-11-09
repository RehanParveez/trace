export type StepKey = "upload" | "read" | "quantities" | "review" | "boq" | "export";
export type StepState = "DONE" | "OPEN" | "RUNNING" | "FAILED" | "READY";
export type LineState = "MEASURED" | "ASSUMED" | "PART_ASSUMED";
export type ProfileSource = "REQUEST" | "COMPANY" | "DEFAULT";
export type ExportKind = "xlsx" | "priced_pdf" | "client_pdf" | "accuracy_pdf";
export type SeenStep = "review" | "boq";
export type Confidence = "High" | "Medium" | "Low";

export interface FlowStep {
  key: StepKey;
  state: StepState;
  detail: string | null;
}

export interface SittingSegment {
  name: string;
  start: string;
  end: string;
  seconds: number | null;
}

export interface SittingStage {
  name: string;
  seconds: number;
  status: string;
}

export interface Sitting {
  events: Record<string, string>;
  segments: SittingSegment[];
  stages: SittingStage[];
  reader_seconds: number | null;
  sitting_seconds: number | null;
  complete: boolean;
  exports: Array<Record<string, unknown>>;
}

export interface BillingProfileOption {
  id: string;
  label: string;
}

export interface FlowStatus {
  project_id: string;
  steps: FlowStep[];
  next: StepKey | null;
  open_rows: number;
  sitting: Sitting;
  profile: string;
  profile_source: ProfileSource;
  profiles: BillingProfileOption[];
}

export interface FlowLine {
  code: string;
  description: string | null;
  unit: string;
  qty: number | null;
  floor: string | null;
  rate: number | null;
  rate_unit: string | null;
  amount: number | null;
  low: number | null;
  high: number | null;
  unpriced_why: string | null;
  state: LineState;
  label: string;
  priced: boolean;
  measured_amount: number | null;
  assumed_amount: number | null;
  low_pct: number | null;
  high_pct: number | null;
  elements: string[];
  open_rows: number;
}

export interface FlowTotals {
  grand: number;
  measured: number;
  assumed: number;
  priced: number;
  unpriced: number;
  by_section: Record<string, number | null>;
  by_floor: Record<string, number | null>;
  range: { low: number | null; high: number | null; of_amount: number | null } | null;
}

export interface CoverageRow {
  section: string;
  MEASURED: number;
  ASSUMED: number;
  ASKED: number;
  NOT_READ: number;
  total: number;
  with_quantity_pct: number;
}

export interface AssumptionRow {
  input: string;
  rule: string | null;
  value: number | string | null;
  unit: string | null;
  range: number[] | null;
  source: string | null;
  items: string[];
  floors: string[];
}

export interface RateBookUsed {
  id: string;
  code: string;
  version: number;
  edition: string | null;
  scope: string;
  items: number;
}

export interface FlowBoq {
  project_id: string;
  has_ledger: boolean;
  profile: string;
  profile_source: ProfileSource;
  lines: FlowLine[];
  totals: FlowTotals;
  rate_books: RateBookUsed[];
  rate_notes: string[];
  banner: string[];
  open_rows: number;
  coverage: CoverageRow[];
  assumptions: AssumptionRow[];
}

export interface RateBookOption {
  id: string;
  code: string;
  name?: string | null;
  status?: string;
}

export type AccuracyBand = "High" | "Medium" | "Low" | "Not banded";
export type AccuracyBasis = "MONEY" | "COUNT";
export type RankedBy = "LOW_CONFIDENCE_MONEY" | "LOW_CONFIDENCE_COUNT" | "ASSUMED_MONEY" | "ASSUMED_NO_RATES";

export interface AccuracyCoverage {
  sections: CoverageRow[];
  total: { MEASURED: number; ASSUMED: number; ASKED: number; NOT_READ: number; total: number; with_quantity_pct: number };
  not_read_sections: string[];
  not_read_items: Array<{ section: string; items: string[]; more: number }>;
  note: string | null;
}

export interface AccuracyMoney {
  priced: boolean;
  basis: AccuracyBasis;
  lines: number;
  priced_lines: number;
  unpriced_lines: number;
  total: number | null;
  measured: number | null;
  assumed: number | null;
  assumed_pct: number | null;
  note: string | null;
  assumed_lines: number | null;
  measured_lines: number | null;
}

export interface AccuracyBandRow {
  band: AccuracyBand;
  lines: number;
  amount: number | null;
  pct: number;
}

export interface AccuracyConfidence {
  shown: boolean;
  why: string | null;
  bands: AccuracyBandRow[];
  basis: AccuracyBasis | null;
  calibrated: Record<string, number | string | null> | null;
}

export interface AccuracyQuestion {
  key: string;
  item: string | null;
  prompt: string | null;
  page: number | null;
  effect_rs: number | null;
  touches: number;
  crop_url: string | null;
}

export interface AccuracyCheckLine {
  code: string;
  description: string | null;
  floor: string | null;
  unit: string | null;
  qty: number | null;
  amount: number | null;
  band: Confidence | null;
  why: string | null;
  assumed_amount: number | null;
  assumed_share: number | null;
  open_rows: number;
  pages: number[];
  crop_url: string | null;
}

export interface AccuracyTrackSet {
  set: string;
  office: string | null;
  date: string | null;
  commit: string | null;
  within_10: number;
  compared: number;
}

export interface AccuracyTrack {
  state: "MEASURED" | "NOT_MEASURED";
  text: string;
  rule: string;
  offices: number;
  registered_offices: number;
  first_sight_sets: number;
  scored_sets: number;
  unscored_sets: string[];
  within_10: number | null;
  compared: number | null;
  dates: string[];
  sets: AccuracyTrackSet[];
}

export interface AccuracyReport {
  title: string;
  intro: string;
  project: { id?: string; name?: string | null; case?: string };
  generated: string | null;
  profile: string | null;
  coverage: AccuracyCoverage;
  money: AccuracyMoney;
  confidence: AccuracyConfidence;
  questions: { open: number; money: number | null; unvalued: number; rows: AccuracyQuestion[]; more: number };
  assumptions: { count: number; more: number; rows: Array<{ input: string; value: number | string | null; unit: string | null; range: number[] | null; source: string | null; items: number; floors: string[] }> };
  check_first: { ranked_by: RankedBy; text: string; pool: number; lines: AccuracyCheckLine[] };
  track_record: AccuracyTrack;
  footer: string;
}

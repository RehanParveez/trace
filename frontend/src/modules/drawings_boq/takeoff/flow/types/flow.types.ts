export type StepKey = "upload" | "read" | "quantities" | "review" | "boq" | "export";
export type StepState = "DONE" | "OPEN" | "RUNNING" | "FAILED" | "READY";
export type LineState = "MEASURED" | "ASSUMED" | "PART_ASSUMED";
export type ProfileSource = "REQUEST" | "COMPANY" | "DEFAULT";
export type ExportKind = "xlsx" | "priced_pdf" | "client_pdf";
export type SeenStep = "review" | "boq";

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

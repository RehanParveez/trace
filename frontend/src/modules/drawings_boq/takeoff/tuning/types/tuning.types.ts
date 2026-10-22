export type ParamStatus = "SWEEPABLE" | "NOT_SWEEPABLE";
export type ParamStage = "READ" | "GATE" | "POLICY";
export type RuleBasis = "TUNED" | "STANDARD" | "DEFAULT";
export type Ladder = "narrow" | "standard" | "wide";
export type DecisionAction = "KEEP" | "CHANGE" | "INSUFFICIENT" | "INERT" | "REPORT_ONLY" | "INCOMPLETE";
export type SweepStatus = "COMPLETE" | "PARTIAL";

export interface TuningParam {
  key: string;
  name: string;
  rule_id: string;
  basis: RuleBasis;
  families: string[];
  unit: string;
  kind: string;
  lo: number;
  hi: number;
  hand: number;
  live: number;
  stage: ParamStage;
  status: ParamStatus;
  calibratable: boolean;
  reasons: string[];
  copies: string[];
  files: string[];
  reads: number;
  ledgered: boolean;
}

export interface TuningRule {
  id: string;
  label: string;
  basis: RuleBasis;
  codes: string[];
  params: string[];
  families: string[];
  sweepable: number;
  calibratable: number;
}

export interface UnregisteredModule {
  file: string;
  count: number;
  names: string[];
}

export interface TuningRegistry {
  extract_version: number;
  base_extract_version: number;
  rules: TuningRule[];
  params: TuningParam[];
  unregistered: { total: number; modules: UnregisteredModule[] };
  ledger: { entries: LedgerEntry[]; drift: string[] };
}

export interface LedgerEntry {
  key: string;
  from: number;
  to: number;
  extract_version: number;
  evidence: Record<string, unknown>;
}

export interface PlanBody {
  rules?: string[];
  keys?: string[];
  ladder: Ladder;
  include_unswept?: boolean;
  control_seconds?: number;
  copies: string[];
}

export interface TuningPlan {
  drawing_id: string;
  ladder: Ladder;
  constants: number;
  n_cells: number;
  cells: { key: string; value: number }[];
  left_out: { key: string; value?: number; reason: string }[];
  estimate_seconds: number | null;
  labels: number;
  complete_sheets: number;
  warnings: string[];
  command: string;
}

export interface SweepItem {
  id: string;
  drawing_id: string;
  created_at: string;
  extract_version: number;
  stale: boolean;
  ladder: Ladder;
  status: SweepStatus;
  constants: number;
  cells: number;
  changes: number;
  label_count: number;
  seconds: number;
  note: string | null;
  counts: Partial<Record<DecisionAction, number>>;
}

export interface SweepList {
  drawing_id: string;
  current_extract_version: number;
  sweeps: SweepItem[];
}

export interface GuardResult {
  name: string;
  ok: boolean;
  detail: string;
}

export interface TriedValue {
  value: number;
  f1: number | null;
  gain: number | null;
  ok: boolean;
  why_not: string[];
}

export interface DecisionEvidence {
  affected_families?: string[];
  labels?: number;
  needed?: number;
  complete_sheets?: number;
  f1_now?: number | null;
  chosen?: { value: number; f1: number | null; gain: number | null };
  neighbours?: { value: number; f1: number | null }[];
  guards?: GuardResult[];
  kinds_moved_outside_the_rule?: string[];
  tried?: TriedValue[];
}

export interface Decision {
  key: string;
  rule_id: string;
  basis: RuleBasis;
  hand: number;
  current: number;
  proposed: number | null;
  families: string[];
  action: DecisionAction;
  reasons: string[];
  evidence: DecisionEvidence;
}

export interface Decisions {
  decision_version: number;
  policy: { min_gain: number; min_labels: number; regression_tol: number; gate_min_units: number };
  decisions: Decision[];
  counts: Partial<Record<DecisionAction, number>>;
  skipped: { key: string; reason: string }[];
  partial: boolean;
  design: string | null;
  joint: { ok: boolean; changes: string[]; guards: GuardResult[] } | null;
}

export interface PatchHunk {
  key: string;
  file?: string;
  find?: string;
  replace?: string;
  error?: string;
}

export interface Patch {
  hunks: PatchHunk[];
  version: { file?: string; find?: string; replace?: string; new_version?: number; error?: string } | null;
  ledger_json: string | null;
  markdown: string;
}

export interface SweepDetail extends SweepItem {
  result: Record<string, unknown>;
  decisions: Decisions;
  patch: Patch;
}

export interface DecideBody {
  min_gain?: number;
  min_labels?: number;
  regression_tol?: number;
  gate_min_units?: number;
}

export interface DecideResult {
  sweep_id: string;
  decisions: Decisions;
  patch: Patch;
}

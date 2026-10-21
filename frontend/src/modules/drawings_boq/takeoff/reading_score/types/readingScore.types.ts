export type ScoreMode = "DRY_RUN" | "STORED";
export type ScoreStatus = "OK" | "REGRESSION" | "PARTIAL" | "NO_LABELS";
export type LabelPolarity = "POSITIVE" | "NEGATIVE";

export interface LabelSheetRow {
  sheet_id: string;
  page_no: number;
  title: string | null;
  positive: number;
  negative: number;
  complete: boolean;
  sources: string[];
}

export interface LabelFamilyRow {
  family: string;
  positive: number;
  negative: number;
}

export interface LabelsSummary {
  drawing_id: string;
  labels: number;
  positive: number;
  negative: number;
  stamp: string | null;
  sheets: LabelSheetRow[];
  families: LabelFamilyRow[];
  unlabelled_sheets: number[];
}

export interface LabelTemplate {
  columns: string[];
  csv: string;
  families: string[];
}

export interface DeriveLabelsResult {
  drawing_id: string;
  added: number;
  updated: number;
  unchanged: number;
  revoked: number;
  report: Record<string, number>;
  summary: LabelsSummary;
}

export interface ImportLabelsBody {
  format: "CSV" | "JSON";
  content: string;
  replace_imported: boolean;
}

export interface ImportLabelsResult {
  drawing_id: string;
  added: number;
  deleted: number;
  sheets: number;
  summary: LabelsSummary;
}

export interface MatchRuleValues {
  position_tol_pt: number;
  positions: boolean;
  size_tol_pct: number;
  size_tol_mm: number;
  regression_tol: number;
  gate_min_units: number;
  max_listed: number;
}

export interface RunScoreBody {
  mode: ScoreMode;
  rule?: Partial<MatchRuleValues>;
  sheet_ids?: string[];
  label_drawing_id?: string;
  budget_seconds?: number;
  max_total_seconds?: number;
  note?: string;
}

export interface SizeCounts {
  checked: number;
  ok: number;
  wrong: number;
  unread: number;
  match_rate?: number | null;
}

export interface FamilyScore {
  family: string;
  labels: number;
  found: number;
  tp: number;
  fp: number;
  fn: number;
  wrong_confirmed: number;
  unlabelled: number;
  unjudged: number;
  size: SizeCounts;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  upper_bound?: boolean;
  sheets?: number;
}

export interface ScoreTotalsView {
  labels: number;
  found: number;
  tp: number;
  fp: number;
  fn: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
}

export interface MemberRef {
  family: string;
  mark: string | null;
  x: number | null;
  y: number | null;
  why: string;
}

export interface SheetScore {
  sheet_id: string;
  page_no: number;
  title: string | null;
  basis: "COMPLETE" | "NEGATIVES_ONLY";
  families: FamilyScore[];
  misses: MemberRef[];
  wrong: MemberRef[];
  misses_cut: number;
  wrong_cut: number;
}

export interface NotJudged {
  sheet_id: string | null;
  page_no: number;
  title: string | null;
  reason: string;
  detail: string;
}

export interface ScoreResult {
  score_version: number;
  mode: ScoreMode;
  extract_version: number | null;
  analysis_version: number | null;
  partial: boolean;
  rule: MatchRuleValues;
  totals: ScoreTotalsView & { unlabelled?: number; unjudged?: number; size?: SizeCounts; wrong_confirmed?: number };
  families: FamilyScore[];
  sheets: SheetScore[];
  could_not_judge: NotJudged[];
  label_summary: Record<string, unknown>;
}

export interface RegressionReason {
  scope: string;
  best: number | null;
  now: number | null;
}

export interface ScoreBaseline {
  score_id: string | null;
  f1?: number | null;
  extract_version?: number | null;
  reasons: RegressionReason[];
  note?: string;
}

export interface ScoreListItem {
  id: string;
  drawing_id: string;
  label_drawing_id: string | null;
  created_at: string;
  mode: ScoreMode;
  status: ScoreStatus;
  extract_version: number | null;
  analysis_version: number | null;
  label_count: number;
  partial: boolean;
  rule_hash: string;
  labels_stamp: string;
  totals: ScoreTotalsView;
  note: string | null;
}

export interface ScoreList {
  drawing_id: string;
  current_extract_version: number;
  best_id: string | null;
  scores: ScoreListItem[];
}

export interface ScoreDetail extends ScoreListItem {
  result: ScoreResult;
  baseline: ScoreBaseline | null;
}

export interface FamilyChange {
  family: string;
  a: FamilyScore | null;
  b: FamilyScore | null;
  d_precision: number | null;
  d_recall: number | null;
  d_f1: number | null;
}

export interface MemberChange extends MemberRef {
  page_no: number;
}

export interface ScoreComparison {
  families: FamilyChange[];
  d_totals: { precision: number | null; recall: number | null; f1: number | null };
  lost: MemberChange[];
  gained: MemberChange[];
  same_rule: boolean;
  same_mode: boolean;
}

export interface ScoreCompare {
  drawing_id: string;
  a: ScoreListItem;
  b: ScoreListItem;
  comparison: ScoreComparison;
}

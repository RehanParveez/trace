export type FindingClass = "ERROR" | "CONFLICT" | "METHOD" | "MISSING" | "EXTRA" | "UNVERIFIABLE" | "ROUNDING" | "NAMING" | "CHECK" | "INFO";
export type FindingStatus = "OPEN" | "ACCEPTED" | "REJECTED" | "SIGNED";
export type FindingDecision = "OPEN" | "ACCEPTED" | "REJECTED";

export interface BbsDocumentSummary {
  id: string;
  project_id: string;
  file_name: string | null;
  sha256: string;
  status: "ACTIVE" | "SUPERSEDED";
  version: number;
  title: string | null;
  pages: number;
  profile: string;
  created_at: string;
  row_count: number;
  sheet_count: number;
}

export interface BbsUploadResponse {
  document: BbsDocumentSummary;
  summary: Record<string, unknown>;
  previous_version: number | null;
}

export interface BbsRowDiff {
  key: string;
  fields: Record<string, [string | null, string | null]>;
}

export interface BbsVersionDiff {
  from_version?: number;
  to_version?: number;
  counts: { added: number; removed: number; changed: number; same: number };
  added: string[];
  removed: string[];
  changed: BbsRowDiff[];
}

export interface CrosscheckTotals {
  compared_rows?: number;
  compared_lines?: number;
  skipped_no_line_rows?: number;
  unchecked_blockers?: Record<string, number>;
  by_code?: Record<string, number>;
  net_effect_kg?: string;
  net_effect_kg_error_only?: string;
  net_effect_kg_by_class?: Record<string, string>;
  match_stats?: { rows?: number; matched?: number; ask?: number; extra?: number; share_without_asking?: number };
}

export interface AuditTotals {
  rows?: number;
  sheets?: number;
  printed_total_kg?: string;
  rows_total_kg?: string;
  fractional_round_up_kg?: string;
  unit_weight_deviation_kg?: string;
  cut_from_parts_checked?: number;
  cut_from_parts_match?: number;
  cut_from_parts_skipped?: number;
  by_code?: Record<string, number>;
  by_class?: Record<string, number>;
  crosscheck?: CrosscheckTotals;
}

export interface AuditRun {
  id: string;
  document_id: string;
  level: string;
  engine_digest: string;
  rules_digest: string;
  decisions_digest: string;
  previous_document_id: string | null;
  totals: AuditTotals;
  diff: Partial<BbsVersionDiff>;
  created_at: string;
}

export interface FindingRef {
  page?: number | null;
  sheet?: number | null;
  sheet_name?: string | null;
  member?: string | null;
  sr?: number | null;
  description?: string | null;
}

export interface DrawingRef {
  pdf_key?: string | null;
  page?: number | null;
  sheet_no?: string | null;
  what?: string | null;
  uv?: number[] | null;
  anchor_native?: number[] | null;
}

export interface FindingConvention {
  key: string;
  value: string | number | boolean;
}

export type EffectBasis = "EXPECTATION" | "ESTIMATE" | "BBS_ROWS";

export interface Finding {
  id: string;
  run_id: string;
  code: string;
  finding_class: FindingClass;
  rule: string;
  bbs_ref: FindingRef;
  drawing_ref: DrawingRef | null;
  effect_basis: EffectBasis | null;
  convention: FindingConvention | null;
  bbs_value: string | null;
  trace_value: string | null;
  diff_kg: string | null;
  diff_pct: string | null;
  confidence: string;
  question: string | null;
  status: FindingStatus;
  reason: string | null;
  decided_at: string | null;
}

export interface FindingList {
  run_id: string | null;
  total: number;
  page: number;
  page_size: number;
  items: Finding[];
  counts_by_class: Record<string, number>;
  counts_by_status: Record<string, number>;
}

export interface FindingFilters {
  finding_class?: string;
  status?: string;
  code?: string;
  page: number;
}

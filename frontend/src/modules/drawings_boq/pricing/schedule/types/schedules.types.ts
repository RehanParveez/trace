import type { Num } from "../../../types/drawings-boq.types";

export type ImportStatus = "UPLOADED" | "PARSING" | "REVIEW" | "PUBLISHED" | "FAILED" | "CANCELLED";
export type SourceKind = "PDF" | "CSV";
export type RowFilter = "all" | "review" | "unmapped" | "mapped" | "skipped" | "sample" | "flagged";
export type MappingSource = "SUGGESTED" | "MANUAL" | "CSR_REF";
export type CheckStatus = "pass" | "warn" | "fail";

export interface ImportCheck {
  code: string;
  label: string;
  status: CheckStatus;
  detail: string;
  count: number | null;
}

export interface ImportReport {
  status: "PASS" | "PASS_WITH_WARNINGS" | "FAIL";
  checks: ImportCheck[];
  counts: { rows: number; flagged_for_review: number; unparsed_lines: number; with_alt_rate: number; pages: number | null };
  page_coverage: number | null;
  unparsed_sample: Array<{ page: number | null; line: number | null; text: string }>;
  page_range?: [number, number];
}

export interface ImportCounts {
  rows: number;
  live: number;
  to_review: number;
  mapped: number;
  unmapped: number;
  skipped: number;
  samples: number;
  samples_unverified: number;
  edited: number;
}

export interface RateImport {
  id: string;
  status: ImportStatus;
  source_kind: SourceKind;
  filename: string;
  file_size: number;
  content_hash: string;
  layout_profile: string;
  first_page: number;
  last_page: number | null;
  book_code: string | null;
  book_name: string | null;
  edition: string | null;
  jurisdiction: string | null;
  province: string | null;
  city: string | null;
  currency: string;
  effective_from: string | null;
  effective_to: string | null;
  page_count: number | null;
  row_count: number;
  report: ImportReport | null;
  error_message: string | null;
  parsed_at: string | null;
  rate_book_id: string | null;
  published_at: string | null;
  created_at: string;
  duplicate_of_id: string | null;
  counts: Partial<ImportCounts>;
}

export interface Suggestion {
  code: string;
  description: string;
  unit: string;
  score: number;
  reason: string;
  spec_conflict: boolean;
}

export interface ImportRow {
  id: string;
  seq: number;
  page: number | null;
  line_no: number | null;
  chapter: string | null;
  item_no: string | null;
  description: string;
  raw_line: string | null;
  unit_raw: string | null;
  basis_qty: Num;
  unit: string | null;
  unit_known: boolean;
  rate_raw: string | null;
  rate: Num | null;
  rate_alt: Num | null;
  unit_rate: Num | null;
  flags: string[];
  needs_review: boolean;
  reviewed: boolean;
  skipped: boolean;
  edited: boolean;
  original: Record<string, unknown> | null;
  note: string | null;
  work_item_code: string | null;
  mapping_source: MappingSource | null;
  suggestions: Suggestion[];
  is_sample: boolean;
  sample_verified: boolean;
}

export interface ChapterSummary {
  chapter: string | null;
  rows: number;
  to_review: number;
}

export interface UploadPayload {
  file: File;
  layout_profile: string;
  first_page: number;
  last_page: number | null;
  book_code: string;
  book_name: string;
  edition: string;
  jurisdiction: string;
  province: string;
  city: string;
  currency: string;
  effective_from: string;
  effective_to: string;
}

export interface RowUpdatePayload {
  description?: string;
  item_no?: string | null;
  chapter?: string | null;
  unit?: string;
  basis_qty?: number;
  rate?: number;
  work_item_code?: string;
  clear_mapping?: boolean;
  reviewed?: boolean;
  skipped?: boolean;
  sample_verified?: boolean;
  note?: string | null;
}

export type BulkAction = "confirm" | "skip" | "unskip" | "map" | "clear_mapping" | "accept_suggestions";

export interface BulkPayload {
  action: BulkAction;
  row_ids?: string[];
  filter?: RowFilter;
  chapter?: string;
  q?: string;
  work_item_code?: string;
  min_score?: number;
}

export interface ReparsePayload {
  layout_profile?: string;
  first_page?: number;
  last_page?: number | null;
}

export interface ReadinessItem {
  code: string;
  message: string;
  count?: number | null;
}

export interface Readiness {
  can_publish: boolean;
  blockers: ReadinessItem[];
  warnings: ReadinessItem[];
  counts: Record<string, number>;
}

export interface PublishPayload {
  existing_book_id?: string | null;
  code?: string;
  name?: string;
  edition?: string;
  jurisdiction?: string;
  province?: string;
  city?: string;
  effective_from?: string | null;
  effective_to?: string | null;
  include_unmapped: boolean;
}

export interface PublishResult {
  rate_book_id: string;
  created: number;
  updated: number;
  left_out: number;
  unit_changes: Array<{ row_id: string; item_no: string | null; from_unit: string; to_unit: string }>;
}

export interface SuggestResult {
  rows_with_suggestions: number;
  rows_without: number;
  catalog_size: number;
}

export interface BookInfo {
  id: string;
  code: string;
  name: string;
  edition: string | null;
  immutable_version: number;
  status: string;
  effective_from: string | null;
  scope: string;
}

export type CompareMatch = "code" | "csr_ref";

export interface CompareLine {
  work_item_code: string;
  description: string | null;
  trade: string | null;
  csr_ref: string | null;
  status: "ADDED" | "REMOVED" | "CHANGED" | "UNIT_MISMATCH";
  unit: string;
  rate_a: string | null;
  rate_b: string | null;
  delta: string | null;
  pct: string | null;
}

export interface CompareResult {
  book_a: BookInfo;
  book_b: BookInfo;
  match_on: CompareMatch;
  counts: { added: number; removed: number; changed: number; unchanged: number; unit_mismatch: number };
  matched: number;
  median_change_pct: string | null;
  overall_ratio: string | null;
  suggested_factors: Array<{ trade: string; matched: number; median_ratio: string }>;
  lines: CompareLine[];
  truncated: boolean;
}

export interface HistoryPoint {
  book_id: string;
  book_code: string;
  version: number;
  edition: string | null;
  status: string;
  effective_from: string | null;
  unit: string;
  rate: string;
  pct_from_previous: string | null;
}

export interface HistoryResult {
  work_item_code: string;
  unit: string | null;
  points: HistoryPoint[];
}

export interface RefreshPayload {
  source_book_id: string;
  match_on: "csr_ref" | "code";
  trades?: string[] | null;
  recompute_analyses: boolean;
  apply: boolean;
}

export interface RefreshResult {
  applied: boolean;
  source: BookInfo;
  match_on: string;
  updated: number;
  unchanged: number;
  unmatched: number;
  skipped: number;
  changes: Array<{ id: string; work_item_code: string; unit: string; old: string; new: string; pct: string | null }>;
  unmatched_sample: Array<{ id: string; work_item_code: string; unit: string; csr_ref: string | null }>;
  analyses: { recomputed: number; changed: Array<{ code: string; unit: string; old: string | null; new: string }>; failed: Array<{ code: string; error: string }> };
}

export interface RateGap {
  work_item_code: string | null;
  unit: string;
  reason: "NO_CODE" | "NO_RATE" | "UNIT_MISMATCH";
  lines: number;
  quantity: string;
  sample_description: string | null;
  available_units: string[];
  item_ids: string[];
}

export interface RateGapsResult {
  boq_version_id: string;
  as_of: string;
  rate_books: Array<{ id: string; code: string; edition: string | null; immutable_version: number; scope: string }>;
  priced: number;
  unpriced: number;
  resolvable: number;
  gaps: RateGap[];
}

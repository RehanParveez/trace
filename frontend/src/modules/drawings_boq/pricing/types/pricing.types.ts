import type { Num } from "../../types/drawings-boq.types";

export type RateBookStatus = "DRAFT" | "ACTIVE" | "SUPERSEDED" | "ARCHIVED";
export type RateBookOwner = "all" | "system" | "org";

export interface RateBook {
  id: string;
  organization_id: string | null;
  code: string;
  name: string;
  description: string | null;
  edition: string | null;
  currency: string;
  jurisdiction: string | null;
  province: string | null;
  city: string | null;
  effective_from: string | null;
  effective_to: string | null;
  status: RateBookStatus;
  immutable_version: number;
  published_at: string | null;
  content_hash: string | null;
  parent_rate_book_id: string | null;
  supersedes_rate_book_id: string | null;
  is_system: boolean;
  item_count: number;
  analysis_count: number;
  escalation_count: number;
}

export interface RateBookFilters {
  status?: RateBookStatus | null;
  owner?: RateBookOwner;
}

export interface RateBookCreatePayload {
  code: string;
  name: string;
  description?: string | null;
  edition?: string | null;
  currency?: string;
  jurisdiction?: string | null;
  province?: string | null;
  city?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  copy_from_id?: string | null;
}

export interface RateBookUpdatePayload {
  name?: string;
  description?: string | null;
  edition?: string | null;
  currency?: string;
  jurisdiction?: string | null;
  province?: string | null;
  city?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
}

export interface RateItem {
  id: string;
  rate_book_id: string;
  work_item_code: string;
  unit: string;
  rate: Num;
  description: string | null;
  trade: string | null;
  specification: string | null;
  csr_ref: string | null;
  analysis_id: string | null;
  is_active: boolean;
}

export interface RateItemFilters {
  q?: string;
  trade?: string;
  include_inactive?: boolean;
}

export interface RateItemInput {
  work_item_code: string;
  unit: string;
  rate: number;
  description?: string | null;
  trade?: string | null;
  specification?: string | null;
  csr_ref?: string | null;
}

export interface RateItemUpdatePayload {
  rate?: number;
  description?: string | null;
  trade?: string | null;
  specification?: string | null;
  csr_ref?: string | null;
  is_active?: boolean;
}

export interface RateImportResult {
  created: number;
  updated: number;
  total: number;
}

export interface RateEscalation {
  id: string;
  rate_book_id: string;
  trade_scope: string;
  effective_from: string;
  factor: Num;
  note: string | null;
}

export interface EscalationCreatePayload {
  trade_scope?: string;
  effective_from: string;
  factor: number;
  note?: string | null;
}

export type AnalysisComponentType = "MATERIAL" | "LABOUR" | "PLANT" | "OTHER";
export type AnalysisComponentSource = "DIRECT" | "RATE_ITEM" | "LABOUR_RATE" | "MATERIAL_LIBRARY";

export interface AnalysisComponent {
  id: string;
  sequence: number;
  component_type: AnalysisComponentType;
  description: string;
  work_item_code: string | null;
  rate_source: AnalysisComponentSource;
  ref_rate_item_id: string | null;
  unit: string;
  coefficient: Num;
  unit_rate: Num | null;
}

export interface AnalysisComponentInput {
  component_type: AnalysisComponentType;
  description: string;
  work_item_code?: string | null;
  rate_source: AnalysisComponentSource;
  ref_rate_item_id?: string | null;
  unit: string;
  coefficient: number;
  unit_rate?: number | null;
}

export interface RateAnalysis {
  id: string;
  rate_book_id: string;
  code: string;
  work_item_code: string;
  description: string;
  unit: string;
  basis_quantity: Num;
  overhead_pct: Num;
  profit_pct: Num;
  computed_rate: Num | null;
  computed_at: string | null;
  is_active: boolean;
  components: AnalysisComponent[];
}

export interface AnalysisCreatePayload {
  code: string;
  work_item_code: string;
  description: string;
  unit: string;
  basis_quantity?: number;
  overhead_pct?: number;
  profit_pct?: number;
  components: AnalysisComponentInput[];
}

export interface AnalysisUpdatePayload {
  description?: string;
  unit?: string;
  basis_quantity?: number;
  overhead_pct?: number;
  profit_pct?: number;
  components?: AnalysisComponentInput[];
}

export interface AnalysisBreakdownLine {
  sequence: number;
  component_type: AnalysisComponentType;
  description: string;
  unit: string;
  coefficient: string;
  unit_rate: string;
  amount: string;
}

export interface AnalysisBreakdown {
  analysis_id: string;
  lines: AnalysisBreakdownLine[];
  cost_by_type: Record<string, string>;
  cost: string;
  overhead: string;
  profit: string;
  total: string;
  basis_quantity: string;
  rate: string;
  unit: string;
}

export interface ProjectRateOverride {
  id: string;
  project_id: string;
  work_item_code: string;
  unit: string;
  rate: Num;
  reason: string;
  effective_from: string | null;
  effective_to: string | null;
  created_by_user_id: string | null;
  created_at: string | null;
  revoked_at: string | null;
  revoked_by_user_id: string | null;
  revoke_reason: string | null;
}

export interface OverrideCreatePayload {
  work_item_code: string;
  unit: string;
  rate: number;
  reason: string;
  effective_from?: string | null;
  effective_to?: string | null;
}

export interface PriceVersionPayload {
  rate_book_ids?: string[] | null;
  as_of?: string | null;
  overwrite_manual?: boolean;
  item_ids?: string[] | null;
}

export interface PricedRateBook {
  id: string;
  code: string;
  edition: string | null;
  immutable_version: number;
  scope: "ORGANIZATION" | "SYSTEM";
  content_hash: string | null;
}

export interface PriceVersionResult {
  boq_version_id: string;
  as_of: string;
  rate_books: PricedRateBook[];
  priced: number;
  changed: number;
  unpriced: number;
  unit_mismatch: number;
  skipped_manual: number;
  skipped_other: number;
  by_source: Record<string, number>;
  total: Num;
  open_issues: number;
}

export interface PricingSummary {
  boq_version_id: string;
  priced_at: string | null;
  pricing_meta: {
    as_of?: string;
    rate_books?: PricedRateBook[];
    overwrite_manual?: boolean;
  } & Record<string, unknown>;
  item_count: number;
  unpriced_count: number;
  by_source: Record<string, number>;
  total: Num;
}

export interface RateAttempt {
  source: "PROJECT_OVERRIDE" | "RATE_BOOK" | "LIBRARY";
  result: "used" | "no_rate" | "unit_mismatch";
  book?: string;
  book_id?: string;
  override_id?: string;
  matched_on?: string;
  units?: string[];
}

export interface RateResolutionTrace {
  source?: string;
  unit_rate?: Num;
  base_rate?: Num;
  escalation_factor?: Num | null;
  rate_book_code?: string;
  edition?: string | null;
  book_version?: number;
  csr_ref?: string | null;
  rate_unit?: string;
  unit_converted?: boolean;
  reason?: string;
  override_rate?: string;
  rate?: string;
  override_unit?: string;
  library_unit?: string;
  raw_text?: string;
  matched_on?: string;
  as_of?: string;
}

export interface RateExplain {
  item_id: string;
  work_item_code: string | null;
  unit: string;
  current: RateResolutionTrace | null;
  current_source: string | null;
  current_unit_rate: Num | null;
  would_resolve_to: RateResolutionTrace | null;
  attempts: RateAttempt[];
  stack: PricedRateBook[];
}

export type DiffStatus = "ADDED" | "REMOVED" | "CHANGED" | "UNCHANGED";

export interface DiffElementRef {
  element_id: string;
  name: string | null;
  ifc_global_id: string | null;
}

export interface DiffLine {
  item_key: string;
  status: DiffStatus;
  work_item_code: string | null;
  material_name: string | null;
  unit_a: string | null;
  unit_b: string | null;
  unit_changed: boolean;
  net_a: Num | null;
  net_b: Num | null;
  quantity_a: Num | null;
  quantity_b: Num | null;
  rate_a: Num | null;
  rate_b: Num | null;
  amount_a: Num | null;
  amount_b: Num | null;
  net_delta: Num | null;
  quantity_delta: Num | null;
  quantity_delta_pct: Num | null;
  rate_delta: Num | null;
  amount_delta: Num | null;
  elements_added: DiffElementRef[];
  elements_removed: DiffElementRef[];
  element_counts: Record<string, number>;
}

export interface DiffSummary {
  ADDED: number;
  REMOVED: number;
  CHANGED: number;
  UNCHANGED: number;
  total_a: Num;
  total_b: Num;
  total_delta: Num;
  total_delta_pct: Num | null;
  unpriced_a: number;
  unpriced_b: number;
}

export interface DiffResult {
  version_a_id: string;
  version_b_id: string;
  summary: DiffSummary;
  lines: DiffLine[];
}

export interface DiffOptions {
  include_unchanged?: boolean;
  include_elements?: boolean;
}
import type { ExportKind } from "../../types/drawings-boq.types";

export type RunMode = "FULL" | "INCREMENTAL";

export type FallbackReason =
  | "NO_BASELINE"
  | "ALLOCATION_INPUTS_CHANGED"
  | "TOO_MANY_CHANGES"
  | "BASELINE_INCONSISTENT"
  | "VERIFY_MISMATCH";

export interface RunOptions {
  force_full: boolean;
  verify: boolean;
}

export interface StageTiming {
  stage: string;
  status: string;
  duration_ms: number | null;
  peak_rss_mb: number | null;
}

export interface RunBudget {
  name: string;
  limit: number;
  actual: number | null;
  unit: string;
  ok: boolean | null;
}

export interface RunAllocation {
  mode?: RunMode;
  fallback_reason?: FallbackReason | string;
  participating?: number;
  reused?: number;
  recompute?: number;
  changed?: number;
  added?: number;
  modified?: number;
  removed?: number;
  affected_by_neighbourhood?: number;
  order_flips?: number;
  remap_misses?: number;
  geometry_built?: number;
}

export interface RunVerifyResult {
  checked: boolean;
  matched: boolean;
  problems?: unknown[];
}

export interface RunFailure {
  code: string;
  stage: string | null;
  message: string;
}

export interface RunMetrics {
  run_id: string;
  organization_id: string;
  project_id: string;
  status: string;
  mode: RunMode;
  baseline_run_id: string | null;
  engine_version: string;
  fingerprint: string;
  attempts: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  stages: StageTiming[];
  timings_ms: Record<string, number>;
  counts: Record<string, unknown>;
  allocation: RunAllocation;
  verify: RunVerifyResult | null;
  peak_rss_mb: number | null;
  failure: RunFailure | null;
  budgets: RunBudget[];
}

export interface SlowRun {
  run_id: string;
  project_id: string;
  mode: RunMode;
  duration_seconds: number;
  elements: number;
}

export interface QuotaUsage {
  used: number;
  limit: number | null;
  remaining: number | null;
  period_start?: string | null;
  period_end?: string | null;
}

export interface ConcurrentUsage {
  active: number;
  limit: number;
}

export interface RateLimitWindow {
  window_seconds: number;
  limit: number;
  used: number;
  remaining: number;
  resets_in_seconds: number;
}

export interface CalcUsage {
  quota: QuotaUsage | null;
  concurrent: ConcurrentUsage;
  rate_limits: RateLimitWindow[];
}

export interface OrgCalcMetrics {
  organization_id: string;
  window_days: number;
  runs_total: number;
  runs_by_status: Record<string, number>;
  runs_by_mode: Record<string, number>;
  failure_codes: Record<string, number>;
  active_now: number;
  duration_seconds: { p50: number | null; p95: number | null; max: number | null };
  elements_processed: number;
  warnings_total: number;
  incremental_share: number;
  slowest_runs: SlowRun[];
  usage: CalcUsage;
}

export interface ImpactElement {
  element_id: string;
  ifc_type: string | null;
  name: string | null;
  ifc_global_id: string | null;
  overlap_mm3: number | null;
}

export interface ImpactLedgerRow {
  element_id: string | null;
  work_item_code: string;
  quantity_net: string | number;
  unit: string;
  ledger_id: string;
}

export interface ElementImpact {
  run_id: string;
  element_id: string;
  touching: ImpactElement[];
  affected_ledger: ImpactLedgerRow[];
  truncated: boolean;
}

export type ExportJobStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED";
export type ExportDelivery = "auto" | "sync" | "async";

export interface ExportJob {
  id: string;
  boq_version_id: string;
  snapshot_id: string;
  kind: string;
  format: string;
  status: ExportJobStatus;
  parameters: Record<string, unknown>;
  file_size_bytes: number | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface ExportRequest {
  kind: ExportKind;
  format: "pdf" | "xlsx";
  snapshotId?: string | null;
  compareSnapshotId?: string | null;
  delivery?: ExportDelivery;
}

export type ExportOutcome =
  | { kind: "file"; filename: string }
  | { kind: "job"; job: ExportJob };
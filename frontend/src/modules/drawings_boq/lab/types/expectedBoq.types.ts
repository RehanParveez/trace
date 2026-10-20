export type ExpectedToleranceFrom = "family" | "all" | "default";

export interface ExpectedFamily {
  key: string;
  label: string;
  unit: string;
  quantity: number;
  rows: number;
  tolerance_pct: number;
  tolerance_from: ExpectedToleranceFrom;
  default_pct: number;
}

export interface ExpectedBoqSummary {
  id: string;
  name: string;
  source: string | null;
  default_tolerance_pct: number | null;
  rows: number;
  family_count: number;
  updated_at: string | null;
}

export interface ExpectedBoqDetail {
  id: string;
  name: string;
  source: string | null;
  default_tolerance_pct: number | null;
  tolerances: Record<string, number>;
  families: ExpectedFamily[];
  rows: number;
  updated_at: string | null;
  unmapped?: { item: string; unit: string; quantity: number; section: string }[];
}

export interface ExpectedTolerancesBody {
  default_tolerance_pct: number | null;
  tolerances: Record<string, number | null>;
}

export type ExpectedStatus = "MATCH" | "DIFF" | "MISSING" | "EXTRA" | "OUT_OF_SCOPE";

export interface ExpectedCheckLine {
  key: string;
  label: string;
  status: ExpectedStatus;
  unit: string;
  qs: number | null;
  software: number | null;
  difference: number | null;
  error_pct: number | null;
  tolerance_pct: number;
  tolerance_from: ExpectedToleranceFrom;
  class: string | null;
  software_rows: number;
}

export interface ExpectedGate {
  passed: boolean;
  failures: string[];
  families: number;
  within: number;
  failed: number;
}

export interface ExpectedCheckResult {
  expected_id: string;
  expected_name: string;
  run_id: string;
  software_rows: number;
  lines: ExpectedCheckLine[];
  gate: ExpectedGate;
  measures: { closeness_pct?: number | null; coverage_pct: number | null; extra_lines: number };
}

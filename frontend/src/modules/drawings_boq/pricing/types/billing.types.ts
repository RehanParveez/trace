export interface BillingProfileOption {
  id: string;
  label: string;
}

export interface BillSource {
  element: string;
  qty_key: string;
  floor: string | null;
  value: number | null;
  unit: string;
  assumed: boolean;
}

export interface BillSpec {
  name: string;
  value: string | null;
  basis: "ANSWER" | "ASSUMED" | string;
}

export interface BillLine {
  code: string;
  unit: string;
  qty: number | null;
  spec: BillSpec | null;
  floor: string | null;
  sources: BillSource[];
}

export interface BillIncluded {
  qty_key: string;
  where: string;
  value: number | null;
  unit: string;
}

export interface BillRateNeeded {
  element: string;
  qty_key: string;
  value: number | null;
  unit: string;
  why: string;
}

export interface BillSpecQuestion {
  spec: string;
  floor: string | null;
  default: string | null;
  question: string;
}

export interface BillNotMeasured {
  element: string;
  name: string | null;
  floor: string | null;
  state: string;
  reasons: string[];
  quantity: { value: number; unit: string } | null;
}

export interface BillUnavailable {
  element: string;
  name: string | null;
  qty: string;
  unit: string;
  why: string;
}

export interface BillingSource {
  run: { id: string; completed_at: string | null } | null;
  lines: number;
  no_family: number;
  no_unit: { family: string; floor: string | null; why: string }[];
}

export interface BillingView {
  project_id: string;
  has_ledger: boolean;
  source: BillingSource;
  profile: string;
  profiles: BillingProfileOption[];
  lines: BillLine[];
  included: BillIncluded[];
  rate_needed: BillRateNeeded[];
  questions: BillSpecQuestion[];
  not_measured: BillNotMeasured[];
  unavailable: BillUnavailable[];
  counts: { measured_entries: number; assumed_entries: number; not_measured: number };
  reconciled: boolean;
  lost: Record<string, number | null>;
}

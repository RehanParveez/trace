export type CompletenessVerdict = "EMPTY" | "PARTIAL" | "NO_KNOWN_GAPS";
export type CompletenessSeverity = "BLOCKER" | "WARNING" | "INFO";

export interface CompletenessFinding {
  code: string;
  severity: CompletenessSeverity;
  title: string;
  detail: string;
  fix: string | null;
}

export interface CompletenessFamily {
  family: string;
  label: string;
  present: boolean;
  rows: number;
  codes: string[];
}

export interface CompletenessSkipped {
  stage: string;
  reason: string;
  lost: string | null;
  fix: string | null;
}

export interface CompletenessStep {
  step: string;
  label: string;
  family: string | null;
  enabled: boolean;
  ran: boolean;
  rows: number;
  reason: string | null;
  reason_text: string | null;
  gap: boolean;
  fix: string | null;
}

export interface BillCompleteness {
  run_id: string;
  verdict: CompletenessVerdict;
  ledger_rows: number;
  families: CompletenessFamily[];
  skipped_stages: CompletenessSkipped[];
  funnel: { confirmed: number; draft: number; undecided: number };
  held_by_reason: Record<string, number>;
  derived_steps: CompletenessStep[];
  boq_error: string | null;
  findings: CompletenessFinding[];
  note: string;
}

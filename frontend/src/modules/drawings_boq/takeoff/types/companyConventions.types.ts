export type ConventionOrigin = "COMPANY" | "QS_WORKBOOK" | "PROJECT" | "CODE_DEFAULT_ASSUMED";

export interface ConventionOption { value: string; text: string }

export interface ConventionRow {
  key: string;
  group: string;
  label: string;
  kind: "NUMBER" | "SWITCH" | "CHOICE";
  unit: string | null;
  default: number | string | null;
  value: number | string | null;
  origin: ConventionOrigin;
  origin_text: string;
  low: number;
  high: number;
  options: ConventionOption[];
  editable: boolean;
  why_fixed: string | null;
  set_by: string | null;
  set_at: string | null;
  evidence: string | null;
  sheets_read_with_other_value: number;
  cls: "PRINTED" | "STANDARD" | "JUDGEMENT";
  version: number | null;
  rule_id: string | null;
  scope: Record<string, unknown>;
  scoped: Array<{ scope: Record<string, unknown>; value: unknown; cls: string; origin: string; version: number; rule_id: string }>;
  project_override: { value: unknown; note: string | null; set_at: string | null } | null;
}

export interface CompanyConventions {
  rows: ConventionRow[];
  sheets_read: number;
  assumed: number;
  qs_name: string;
  qs_answered_on: string;
  book: { id: string; name: string; version: number } | null;
  project_id: string | null;
}

export interface ProjectOverridesUpdate {
  values: Record<string, number | string | boolean | null>;
  note?: string | null;
}

export interface ConventionsUpdate {
  values: Record<string, number | string | boolean | null>;
  evidence?: string | null;
}

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
}

export interface CompanyConventions {
  rows: ConventionRow[];
  sheets_read: number;
  assumed: number;
  qs_name: string;
  qs_answered_on: string;
}

export interface ConventionsUpdate {
  values: Record<string, number | string | boolean | null>;
  evidence?: string | null;
}

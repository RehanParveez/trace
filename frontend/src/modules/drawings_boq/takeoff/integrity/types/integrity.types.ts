export type IntegrityState = "OK" | "PARTIAL" | "LOOK";
export type IntegrityCheckStatus = "OK" | "WARN" | "INFO";

export interface IntegrityCheck {
  code: string;
  status: IntegrityCheckStatus;
  title: string;
  message: string;
  pages: number[];
  count: number;
}

export interface IntegritySummary {
  warn: number;
  info: number;
  ok: number;
  sheets: number;
  read: number;
}

export interface IntegrityReport {
  drawing_id: string;
  status: IntegrityState;
  code_version: number;
  checks: IntegrityCheck[];
  summary: IntegritySummary;
}

export type CheckStatus = "PASS" | "WARN" | "INFO";

export interface CheckInput {
  key: string;
  label: string;
  quantity: number;
  unit: string;
}

export interface ReasonCheck {
  code: string;
  status: CheckStatus;
  label: string;
  message: string;
  value: number | null;
  unit: string;
  low: number | null;
  high: number | null;
  inputs: CheckInput[];
}

export interface ReasonFigure {
  key: string;
  label: string;
  quantity: number;
  unit: string;
  rows: number;
}

export interface Reasonableness {
  checks: ReasonCheck[];
  warnings: number;
  passed: number;
  info: number;
  figures: ReasonFigure[];
  ungrouped_rows: number;
  note: string;
}

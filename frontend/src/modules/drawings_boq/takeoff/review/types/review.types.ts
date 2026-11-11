export type ReviewKind = "AI_CANDIDATE" | "READING" | "CONFLICT" | "QUESTION";
export type ReviewSource = "PRINTED" | "AI_READ" | "ASSUMED";
export type ReviewState = "OPEN" | "DECIDED";
export type ReviewActionName = "accept" | "correct" | "reject";

export interface ReviewLine {
  element: string;
  name: string;
  floor: string;
  state: string;
  quantity: number | null;
  unit: string | null;
  range: number[] | null;
}

export interface ReviewAction {
  action: ReviewActionName;
  value: string | null;
  choices: string[];
}

export interface ReviewOption {
  value: string;
  label: string;
  text: string;
}

export interface ReviewDecision {
  action: string;
  value: string | null;
  by: string | null;
  at: string | null;
}

export interface ReviewRow {
  id: string;
  key: string;
  kind: ReviewKind;
  item: string;
  prompt: string;
  floor: string | null;
  floors: string[];
  page: number | null;
  pages: number[];
  crop_url: string | null;
  quote: string | null;
  source: ReviewSource;
  effect_rs: number | null;
  lines: ReviewLine[];
  unquantified: number;
  touches: string[];
  actions: ReviewAction[];
  reasons?: Record<string, string[]>;
  state: ReviewState;
  decision: ReviewDecision | null;
  default: Record<string, unknown> | null;
  unit: string | null;
  options?: ReviewOption[];
  affects: string | null;
  read_id: string | null;
  task: string | null;
  drawing_id: string | null;
  decision_id: string | null;
}

export interface ReviewResponse {
  project_id: string;
  has_ledger: boolean;
  rows: ReviewRow[];
  open: number;
  by_kind: Record<string, number>;
  rates_loaded: boolean;
  item: string | null;
}

export interface ReviewActionBody {
  action: ReviewActionName | "withdraw";
  value?: string | null;
  reason?: string | null;
}

export interface ReviewActionResponse extends ReviewResponse {
  key: string;
  touched: string[];
}

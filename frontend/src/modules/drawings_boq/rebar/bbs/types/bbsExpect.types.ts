export type InputState = "PRINTED" | "DERIVED" | "DEFAULTED" | "MISSING";
export type MemberClass = "COLUMN" | "BEAM" | "FOOTING" | "PLINTH" | "SLAB" | "LINTEL" | "TANK";

export interface ExpectInput {
  name: string;
  value: unknown;
  state: InputState;
  source: string;
  flag: string | null;
}

export interface ExpectLine {
  role: string;
  dia: number | null;
  count: string | null;
  cut_ft: string | null;
  spacing_in: string | null;
  laps: number;
  lap_ft: string;
  total_ft: string | null;
  kg: string | null;
  note: string | null;
}

export interface Expectation {
  id: string;
  member_class: MemberClass;
  mark: string;
  floor: string | null;
  count: number | null;
  total_ft: number | null;
  kg: number | null;
  complete: boolean;
  plan_count: number | null;
  source_page: number | null;
  decision_only: boolean;
  lines: ExpectLine[];
  inputs: ExpectInput[];
  blocked: string[];
  notes: string[];
}

export interface InputShares {
  counts: Record<InputState, number>;
  total: number;
  shares: Record<InputState, number>;
}

export interface ExpectRun {
  id: string;
  document_id: string;
  decisions: Record<string, unknown>;
  decisions_digest: string;
  member_count: number;
  complete_count: number;
  stats: { shares: InputShares; by_class: Record<string, { members: number; complete: number; kg: number }>; complete_kg: number };
  created_at: string;
}

export interface ExpectationList {
  run_id: string | null;
  total: number;
  page: number;
  page_size: number;
  items: Expectation[];
  counts_by_class: Record<string, number>;
}

export interface ExpectFilters {
  member_class: MemberClass | "";
  complete: "" | "yes" | "no";
  page: number;
}

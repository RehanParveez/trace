export interface MarkSource {
  sheet_id: string;
  page_no: number;
  caption: string | null;
  floor: string | null;
  advice: string | null;
  count: number;
  shapes: number[][];
  basis: "SCHEDULE" | "DETAIL" | "PLAN" | null;
  open: number;
  accepted: number;
  set_aside: number;
}

export type MarkState = "DOUBLE" | "DIFFER" | "UNPLACED" | "CHOSEN";

export interface MarkEntity {
  key: string;
  category: string;
  mark: string;
  tag: string | null;
  floor: string | null;
  state: MarkState;
  agree: boolean;
  live_sheets: number;
  suggested_sheet_id: string | null;
  chosen_sheet_id: string | null;
  conflict: boolean;
  choosable: boolean;
  sources: MarkSource[];
}

export interface MarkEntities {
  drawing_id: string;
  entities: MarkEntity[];
  to_decide: number;
  differ: number;
  unplaced: number;
  single: number;
}

export type MarkChoiceBody = { use_suggested: true } | { choices: { key: string; sheet_id: string }[] };

export interface MarkChoiceResult {
  chosen: { key: string; sheet_id: string; page_no: number; tag: string | null; set_aside: number; restored: number }[];
  set_aside: number;
  restored: number;
  blocked: { key: string; code: string; message: string }[];
  marks: MarkEntities;
}

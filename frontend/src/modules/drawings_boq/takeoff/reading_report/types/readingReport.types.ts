export type ReadStatus = "READ" | "UNSURE" | "NOT_READ" | "CONFLICT";
export type SheetStatus = ReadStatus | "NOT_RUN" | "NOTHING_EXPECTED" | null;
export type ScaleState = "SET" | "UNVERIFIED" | "MISSING" | "UNKNOWN";
export type Box = [number, number, number, number];

export interface ReportReason {
  code: string;
  text: string;
  class?: string | null;
}

export interface ReportItem {
  id: string;
  ckey: string;
  class: string;
  category: string;
  kind: "LENGTH" | "AREA" | "COUNT" | string;
  label: string;
  mark: string | null;
  status: ReadStatus;
  reasons: string[];
  source: string;
  confidence: number | null;
  count: number;
  decision: string;
  valid: string;
  points: number[][];
  box: Box | null;
  missing: string[];
  joins: { kind: string; status?: string | null; with?: unknown; note?: string | null }[];
  conflict: string | null;
}

export interface ClassRow {
  class: string;
  expected: boolean;
  status: ReadStatus | null;
  reasons: string[];
  no_reader: boolean;
  count: number;
  by_status: Record<string, number>;
}

export interface ReportSheet {
  sheet_id: string;
  page_no: number;
  title: string | null;
  role: string | null;
  plan_kind: string | null;
  floor: string | null;
  discipline: string | null;
  scale_text: string | null;
  scale: ScaleState;
  text_type: string | null;
  status: SheetStatus;
  ran: boolean;
  width_pt: number | null;
  height_pt: number | null;
  rotation: number;
  items: number;
  by_status: Record<string, number>;
  classes: ClassRow[];
  reasons: ReportReason[];
  held: Record<string, unknown> | null;
  overrides: number;
  misreads: number;
  extract_version: number | null;
  item_rows?: ReportItem[] | null;
}

export interface ReadingReport {
  drawing_id: string;
  sheets: ReportSheet[];
  totals: { sheets: number; ran: number; items: number; by_status: Record<string, number>; empty_sheets: number[] };
  manual_marks_are_scored: boolean;
  joins_applied_to_quantities: boolean;
}

export interface SheetItems {
  sheet_id: string;
  items: ReportItem[];
}

export interface CompletenessInput {
  input: string;
  label: string;
  state: string;
  items: number;
  marks: string[];
}

export interface CompletenessElement {
  element: string;
  items: number;
  complete: number;
  accepted: number;
  state: "COMPLETE" | "PARTLY" | "BLOCKED";
  inputs: CompletenessInput[];
  work_items: string[];
}

export interface BlockingInput extends CompletenessInput {
  element: string;
  blocks: string[];
}

export interface Completeness {
  project_id: string;
  elements: CompletenessElement[];
  blocking: BlockingInput[];
  items: number;
  complete: number;
}

export interface ManualMark {
  id: string;
  drawing_id: string;
  sheet_id: string;
  item_class: string;
  mark: string | null;
  geometry: { points?: number[][]; box?: number[] };
  attrs: Record<string, string | number>;
  note: string | null;
  status: string;
  image_checked: boolean;
  created_at: string;
  counts_as_truth: boolean;
}

export interface ManualMarkBody {
  sheet_id: string;
  item_class: string;
  mark?: string | null;
  geometry: { points?: number[][]; box?: number[] };
  attrs?: Record<string, string | number>;
  note?: string | null;
}

export type MisreadKind = "WRONG_VALUE" | "WRONG_CLASS" | "WRONG_POSITION" | "INVENTED" | "MISSED" | "OTHER";

export interface MisreadBody {
  sheet_id: string;
  kind: MisreadKind;
  candidate_id?: string | null;
  item_class?: string | null;
  mark?: string | null;
  box?: number[] | null;
  expected?: Record<string, string | number>;
  read_as?: Record<string, unknown>;
  note?: string | null;
}

export interface MisreadReport {
  id: string;
  drawing_id: string;
  sheet_id: string;
  candidate_id: string | null;
  ckey: string | null;
  item_class: string | null;
  mark: string | null;
  kind: MisreadKind;
  box: number[] | null;
  expected: Record<string, unknown>;
  read_as: Record<string, unknown>;
  note: string | null;
  extract_version: number | null;
  status: string;
  created_at: string;
}

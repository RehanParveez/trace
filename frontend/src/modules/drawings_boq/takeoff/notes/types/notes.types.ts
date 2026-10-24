export type NoteFate = "USED" | "GRADE" | "CHECKED" | "LISTED" | "CONFLICT" | "NOT_MADE";

export interface NoteRow {
  kind: string;
  text: string | null;
  pages: number[];
  count: number;
  value_mm: number | null;
  value: number | null;
  scope: string | null;
  heading?: string | null;
  fate: NoteFate;
  param: string | null;
  param_text: string | null;
  why: string;
  layer?: string | null;
  material?: string | null;
}

export interface NoteContradiction {
  code: string;
  severity: "warning" | "info";
  title: string;
  message: string;
  pages: number[];
}

export interface NotesSummary {
  notes: number;
  USED: number;
  GRADE: number;
  CHECKED: number;
  LISTED: number;
  CONFLICT: number;
  NOT_MADE: number;
  contradictions: number;
  look: number;
}

export interface NotesReport {
  drawing_id: string;
  sheets_read: number;
  sheets_total: number;
  rows: NoteRow[];
  contradictions: NoteContradiction[];
  summary: NotesSummary;
}

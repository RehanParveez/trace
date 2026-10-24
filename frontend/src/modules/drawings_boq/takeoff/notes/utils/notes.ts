import type { NoteFate, NoteRow, NotesReport } from "../types/notes.types";

export const FATE_ORDER: NoteFate[] = ["CONFLICT", "NOT_MADE", "USED", "GRADE", "CHECKED", "LISTED"];

export const FATE_TITLE: Record<NoteFate, string> = {
  CONFLICT: "Not applied: the drawing disagrees",
  NOT_MADE: "No item is made from it",
  USED: "Used in the calculation",
  GRADE: "Given to members as their grade",
  CHECKED: "Compared with the drawing, nothing changed",
  LISTED: "Listed only, no quantity uses it",
};

export const FATE_TONE: Record<NoteFate, "green" | "red" | "blue" | "gold" | "slate"> = {
  CONFLICT: "red",
  NOT_MADE: "gold",
  USED: "green",
  GRADE: "blue",
  CHECKED: "green",
  LISTED: "slate",
};

export const OPEN_FATES: NoteFate[] = ["CONFLICT", "NOT_MADE"];

export function isEmpty(report: NotesReport | undefined): boolean {
  return !report || (report.rows.length === 0 && report.contradictions.length === 0);
}

export function pagesText(pages: number[] | null | undefined): string {
  const p = [...(pages ?? [])].sort((a, b) => a - b);
  if (!p.length) return "";
  return `${p.length === 1 ? "sheet" : "sheets"} ${p.join(", ")}`;
}

export interface FateGroup { fate: NoteFate; rows: NoteRow[] }

export function groupByFate(report: NotesReport | undefined): FateGroup[] {
  if (!report) return [];
  return FATE_ORDER.map((fate) => ({ fate, rows: report.rows.filter((r) => r.fate === fate) })).filter((g) => g.rows.length > 0);
}

export function lookCount(report: NotesReport | undefined): number {
  return report?.summary.look ?? 0;
}

export function summaryLine(report: NotesReport | undefined): string {
  if (!report || !report.summary.notes) return "";
  const s = report.summary;
  const bits = [`${s.notes} ${s.notes === 1 ? "note" : "notes"}`];
  if (s.USED) bits.push(`${s.USED} used`);
  if (s.GRADE) bits.push(`${s.GRADE} graded`);
  if (s.look) bits.push(`${s.look} to look at`);
  return bits.join(" · ");
}

export function noteTitle(r: NoteRow): string {
  return (r.text ?? "").trim() || r.kind;
}

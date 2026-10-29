import type { ColumnDetail, DrawingCheck, DrawingFacts, StructureMark } from "../types/takeoff.types";

export function detailSizeText(d: Pick<ColumnDetail, "w_in" | "h_in">): string {
  if (d.w_in == null && d.h_in == null) return "";
  const one = (v: number | null) => (v == null ? "?" : `${Math.round(v * 10) / 10}"`);
  return `${one(d.w_in)} × ${one(d.h_in)}`;
}

export type DetailState = "READ" | "PARTIAL" | "NOT_READ";

export function detailState(d: ColumnDetail): DetailState {
  if (d.read === "TEXT" || d.read === "TEXT_SQUARE" || d.read === "OCR" || d.read === "OCR_SQUARE") return "READ";
  return d.read === "PARTIAL" ? "PARTIAL" : "NOT_READ";
}

export function detailRows(facts: DrawingFacts | undefined): ColumnDetail[] {
  return [...(facts?.details ?? [])].sort((a, b) => a.mark.localeCompare(b.mark, undefined, { numeric: true }) || (a.page_no ?? 0) - (b.page_no ?? 0));
}

export function sortedChecks(facts: DrawingFacts | undefined): DrawingCheck[] {
  const checks = facts?.checks ?? [];
  return [...checks.filter((c) => c.severity === "warning"), ...checks.filter((c) => c.severity !== "warning")];
}

export function warningCount(facts: DrawingFacts | undefined): number {
  return (facts?.checks ?? []).filter((c) => c.severity === "warning").length;
}

export function hasChecks(facts: DrawingFacts | undefined): boolean {
  return (facts?.checks?.length ?? 0) > 0 || (facts?.details?.length ?? 0) > 0;
}

export function marksFrom(marks: StructureMark[] | undefined, source: NonNullable<StructureMark["size_source"]>): string[] {
  return [...new Set((marks ?? []).filter((m) => m.size_source === source && m.tag).map((m) => m.tag as string))];
}

export function readerMissing(facts: DrawingFacts | undefined): boolean {
  return facts?.details_reader === "UNAVAILABLE" || facts?.details_reader === "FAILED";
}

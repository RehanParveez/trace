import type { RegisterSyncResult, RegisterWaiting, SheetAction } from "../types/takeoff.types";

export type RegisterMeasureMode = "EXACT" | "APPROXIMATE" | "NONE" | "PDF_MEASURED" | "PDF_FOUND";

export interface MeasureBadge { tone: "green" | "gold" | "red"; label: string }

export function measureBadge(mode: RegisterMeasureMode | null | undefined): MeasureBadge | null {
  switch (mode) {
    case "EXACT": return { tone: "green", label: "Exact" };
    case "APPROXIMATE": return { tone: "gold", label: "Bbox" };
    case "NONE": return { tone: "red", label: "No geometry" };
    case "PDF_MEASURED": return { tone: "green", label: "PDF measured" };
    case "PDF_FOUND": return { tone: "gold", label: "PDF found" };
    default: return null;
  }
}

export function waitingPages(reg: Pick<RegisterSyncResult, "waiting"> | null | undefined): string {
  if (!reg || reg.waiting.length === 0) return "";
  return [...new Set(reg.waiting.map((w) => w.page_no))].sort((a, b) => a - b).join(", ");
}

export function unreadPages(reg: Pick<RegisterSyncResult, "waiting"> | null | undefined): string {
  if (!reg) return "";
  return [...new Set(reg.waiting.filter((w) => !w.code).map((w) => w.page_no))].sort((a, b) => a - b).join(", ");
}

export interface WaitingLine { page_no: number; message: string; action: SheetAction }

export function actionOf(w: Pick<RegisterWaiting, "action" | "code">): SheetAction {
  if (w.action) return w.action;
  if (w.code && w.code.startsWith("SCALE_")) return "CONFIRM_SCALE";
  if (w.code === "PROGRAM_ERROR") return "REPORT_PROBLEM";
  if (w.code && w.code !== "PREPARE_FAILED" && w.code !== "NOT_PREPARED") return "MEASURE_BY_HAND";
  return "READ_SHEETS";
}

export function waitingLines(
  reg: Pick<RegisterSyncResult, "waiting"> | null | undefined,
  issues: Array<{ page_no: number; message: string }> = [],
): WaitingLine[] {
  if (!reg) return [];
  const fresh = new Map(issues.map((i) => [i.page_no, i.message]));
  const seen = new Set<number>();
  const lines: WaitingLine[] = [];
  for (const w of [...reg.waiting].sort((a, b) => a.page_no - b.page_no)) {
    if (seen.has(w.page_no)) continue;
    seen.add(w.page_no);
    lines.push({ page_no: w.page_no, message: w.message ?? w.error ?? fresh.get(w.page_no) ?? "", action: actionOf(w) });
  }
  return lines;
}

export function pagesFor(lines: WaitingLine[], action: SheetAction): string {
  return lines.filter((l) => l.action === action).map((l) => l.page_no).join(", ");
}


export interface SheetRow {
  sheet_id: string;
  page_no: number;
  tone: "ok" | "info" | "action";
  level: string | null;
  title: string | null;
  items: number;
  message: string | null;
}

export function sheetRows(
  reg: Pick<RegisterSyncResult, "sheet_status"> | null | undefined,
  issues: Array<{ page_no: number; message: string }> = [],
): SheetRow[] {
  if (!reg) return [];
  const fresh = new Map(issues.map((i) => [i.page_no, i.message]));
  return [...(reg.sheet_status ?? [])]
    .sort((a, b) => a.page_no - b.page_no)
    .map((s) => ({
      sheet_id: s.sheet_id,
      page_no: s.page_no,
      tone: s.status === "READ" ? "ok" : s.status === "SET_ASIDE" ? "info" : "action",
      level: s.level,
      title: s.title,
      items: s.items,
      message: s.message ?? fresh.get(s.page_no) ?? null,
    }));
}

export function setAsideCount(reg: Pick<RegisterSyncResult, "set_aside"> | null | undefined): number {
  return reg?.set_aside?.length ?? 0;
}

export function needsPerson(reg: Pick<RegisterSyncResult, "waiting"> | null | undefined): boolean {
  return Boolean(reg && reg.waiting.length > 0);
}

export function isPdfFormat(format: string | null | undefined): boolean {
  return (format ?? "").toUpperCase() === "PDF";
}
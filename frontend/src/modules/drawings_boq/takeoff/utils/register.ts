import type { RegisterSyncResult } from "../types/takeoff.types";

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
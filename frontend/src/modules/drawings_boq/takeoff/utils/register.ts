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

export function needsPerson(reg: Pick<RegisterSyncResult, "waiting"> | null | undefined): boolean {
  return Boolean(reg && reg.waiting.length > 0);
}

export function isPdfFormat(format: string | null | undefined): boolean {
  return (format ?? "").toUpperCase() === "PDF";
}
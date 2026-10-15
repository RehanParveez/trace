import type { BillClass, BillClasses, BillCompareLine, BillCompareResult, BillFilter, BillStatus } from "../types/billCompare.types";

export const BILL_CLASSES: BillClass[] = ["READING", "CONVENTION", "QS_ERROR", "MISSING_FEATURE", "NEEDS_DECISION"];

export const BILL_CLASS_TEXT: Record<BillClass, string> = {
  READING: "Reading is wrong",
  CONVENTION: "QS convention",
  QS_ERROR: "QS error",
  MISSING_FEATURE: "Not built yet",
  NEEDS_DECISION: "Needs a decision",
};

export const BILL_STATUS_TEXT: Record<BillStatus, string> = {
  MATCH: "Matches",
  DIFF: "Differs",
  MISSING: "Not found",
  EXTRA: "Not in bill",
  OUT_OF_SCOPE: "Lump sum",
};

export const BILL_STATUS_TONE: Record<BillStatus, "ok" | "warn" | "bad" | "muted"> = {
  MATCH: "ok",
  DIFF: "bad",
  MISSING: "bad",
  EXTRA: "warn",
  OUT_OF_SCOPE: "muted",
};

export function isOpenDifference(line: BillCompareLine): boolean {
  return (line.status === "DIFF" || line.status === "MISSING" || line.status === "EXTRA") && !line.class;
}

export function filterLines(lines: BillCompareLine[], filter: BillFilter): BillCompareLine[] {
  if (filter === "ALL") return lines;
  if (filter === "MATCH") return lines.filter((l) => l.status === "MATCH");
  return lines.filter((l) => l.status === "DIFF" || l.status === "MISSING" || l.status === "EXTRA");
}

export function qtyText(value: number | null, unit: string): string {
  if (value === null || Number.isNaN(value)) return "—";
  const rounded = Math.abs(value) >= 100 ? Math.round(value) : Math.round(value * 100) / 100;
  return `${rounded.toLocaleString("en-US")} ${unit}`.trim();
}

export function errorText(pct: number | null): string {
  if (pct === null || Number.isNaN(pct)) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function withClass(classes: BillClasses, key: string, cls: BillClass | null, note: string): BillClasses {
  const next = { ...classes };
  if (!cls) {
    delete next[key];
    return next;
  }
  next[key] = { class: cls, note: note.trim() };
  return next;
}

export function applyClasses(result: BillCompareResult, classes: BillClasses): BillCompareResult {
  const lines = result.lines.map((l) => {
    const c = classes[l.key];
    return c ? { ...l, class: c.class, note: c.note } : { ...l, class: null, note: "" };
  });
  const open = lines.filter(isOpenDifference).length;
  return { ...result, lines, measures: { ...result.measures, unclassified_differences: open } };
}

export function classesStorageKey(runId: string, fileName: string): string {
  return `bill-compare:${runId}:${fileName}`;
}

export function loadClasses(key: string): BillClasses {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as BillClasses;
    const ok: BillClasses = {};
    for (const [k, v] of Object.entries(parsed ?? {})) {
      if (v && BILL_CLASSES.includes(v.class)) ok[k] = { class: v.class, note: String(v.note ?? "") };
    }
    return ok;
  } catch {
    return {};
  }
}

export function saveClasses(key: string, classes: BillClasses): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(classes));
  } catch {
    return;
  }
}

export function classesForm(classes: BillClasses): string {
  return JSON.stringify(classes);
}

export function parseTolerance(text: string, fallback = 5): number {
  const n = Number(text);
  if (!Number.isFinite(n) || text.trim() === "") return fallback;
  return Math.min(100, Math.max(0, n));
}

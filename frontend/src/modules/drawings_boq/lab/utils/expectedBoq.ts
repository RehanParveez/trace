import type { ExpectedBoqDetail, ExpectedCheckLine, ExpectedGate, ExpectedStatus, ExpectedTolerancesBody, ExpectedToleranceFrom } from "../types/expectedBoq.types";

export type ToleranceText = { ok: true; value: number | null } | { ok: false };

export function parseTolerance(text: string): ToleranceText {
  const s = text.trim().replace(",", ".");
  if (s === "") return { ok: true, value: null };
  if (!/^\d+(\.\d+)?$/.test(s)) return { ok: false };
  const v = Number(s);
  return v >= 0 && v <= 100 ? { ok: true, value: Math.round(v * 100) / 100 } : { ok: false };
}

export const FROM_WORDS: Record<ExpectedToleranceFrom, string> = {
  family: "Set for this item",
  all: "Set for all items",
  default: "Starting value",
};

export const STATUS_WORDS: Record<ExpectedStatus, string> = {
  MATCH: "Inside tolerance",
  DIFF: "Outside tolerance",
  MISSING: "Not measured",
  EXTRA: "Not in the expected BOQ",
  OUT_OF_SCOPE: "Not compared",
};

export const STATUS_TONE: Record<ExpectedStatus, "ok" | "bad" | "warn" | "muted"> = {
  MATCH: "ok",
  DIFF: "bad",
  MISSING: "bad",
  EXTRA: "warn",
  OUT_OF_SCOPE: "muted",
};

const ORDER: Record<ExpectedStatus, number> = { DIFF: 0, MISSING: 1, EXTRA: 2, MATCH: 3, OUT_OF_SCOPE: 4 };

export function sortLines(lines: ExpectedCheckLine[]): ExpectedCheckLine[] {
  return [...lines].sort((a, b) => ORDER[a.status] - ORDER[b.status] || Math.abs(b.error_pct ?? 0) - Math.abs(a.error_pct ?? 0) || a.label.localeCompare(b.label));
}

export function qtyText(q: number | null | undefined, unit: string): string {
  if (q === null || q === undefined) return "-";
  const text = Math.abs(q) >= 100 ? q.toLocaleString("en-US", { maximumFractionDigits: 0 }) : q.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return unit ? `${text} ${unit}` : text;
}

export function errorText(pct: number | null | undefined): string {
  if (pct === null || pct === undefined) return "-";
  return `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

export function marginText(line: ExpectedCheckLine): string {
  if (line.error_pct === null) return "";
  const gap = Math.abs(line.error_pct) - line.tolerance_pct;
  return gap > 0 ? `${gap.toFixed(1)} points past ${line.tolerance_pct}%` : `${(-gap).toFixed(1)} points inside ${line.tolerance_pct}%`;
}

export function gateWords(gate: ExpectedGate): { tone: "ok" | "bad"; text: string } {
  if (gate.families === 0) return { tone: "bad", text: "Nothing could be compared: no item of the expected BOQ was found in this run." };
  if (gate.passed) return { tone: "ok", text: `All ${gate.families} items are inside their tolerance.` };
  return { tone: "bad", text: `${gate.within} of ${gate.families} items are inside their tolerance; ${gate.failed} ${gate.failed === 1 ? "is" : "are"} not.` };
}

export function tolerancesBody(detail: ExpectedBoqDetail, edits: Record<string, string>, allText: string): { body: ExpectedTolerancesBody; wrong: string[] } {
  const wrong: string[] = [];
  const own: Record<string, number | null> = {};
  const all = parseTolerance(allText);
  if (!all.ok) wrong.push("all");
  for (const f of detail.families) {
    if (!(f.key in edits)) continue;
    const parsed = parseTolerance(edits[f.key]);
    if (!parsed.ok) {
      wrong.push(f.key);
      continue;
    }
    const before = detail.tolerances[f.key] ?? null;
    if (parsed.value !== before) own[f.key] = parsed.value;
  }
  return { body: { default_tolerance_pct: all.ok ? all.value : detail.default_tolerance_pct, tolerances: own }, wrong };
}

export function hasChanges(detail: ExpectedBoqDetail, edits: Record<string, string>, allText: string): boolean {
  const { body, wrong } = tolerancesBody(detail, edits, allText);
  return wrong.length > 0 || Object.keys(body.tolerances).length > 0 || body.default_tolerance_pct !== detail.default_tolerance_pct;
}

export function unmappedNote(n: number): string {
  return n === 0 ? "" : `${n} ${n === 1 ? "row of the file belongs" : "rows of the file belong"} to no item family and ${n === 1 ? "was" : "were"} left out.`;
}

export function apiErrorText(error: unknown, fallback: string): string {
  const e = error as { response?: { data?: { message?: string; detail?: { message?: string } | string; error?: { message?: string } } } } | null;
  const d = e?.response?.data;
  const detail = typeof d?.detail === "string" ? d.detail : d?.detail?.message;
  return d?.error?.message || detail || d?.message || fallback;
}

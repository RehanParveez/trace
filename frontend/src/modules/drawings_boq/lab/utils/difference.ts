import type { ComparableRun, DiffItem, DiffMember, DiffStatus, FixAudience, FixEntry, FixList, VariationKind } from "../types/difference.types";

export type Tone = "ok" | "warn" | "bad" | "muted";

export const STATUS_WORDS: Record<DiffStatus, string> = {
  SAME: "No change",
  CHANGED: "Changed",
  ADDED: "New in the later run",
  REMOVED: "Not in the later run",
};

export const STATUS_TONE: Record<DiffStatus, Tone> = { SAME: "muted", CHANGED: "warn", ADDED: "ok", REMOVED: "bad" };

export const KIND_WORDS: Record<VariationKind, string> = { ADDITION: "Addition", OMISSION: "Omission", NEW_ITEM: "New item", ITEM_DROPPED: "Item dropped" };

export const KIND_TONE: Record<VariationKind, Tone> = { ADDITION: "ok", OMISSION: "bad", NEW_ITEM: "ok", ITEM_DROPPED: "bad" };

export const AUDIENCES: FixAudience[] = ["ARCHITECT", "QS", "TRACE"];

export const AUDIENCE_WORDS: Record<FixAudience, { tab: string; intro: string }> = {
  ARCHITECT: { tab: "For the architect", intro: "What the drawings or the model do not say. This is the list to send." },
  QS: { tab: "For the QS", intro: "Choices and site assumptions that only you can give, and checks to make. Not for the architect." },
  TRACE: { tab: "For Trace", intro: "Things the program could not map or measure. Not for the architect." },
};

export const PRIORITY_WORDS: Record<string, string> = { error: "High", warning: "Medium", info: "Low" };

export type DiffFilter = "CHANGES" | "ALL";

export function apiErrorText(error: unknown, fallback: string): string {
  const e = error as { response?: { data?: { message?: string; detail?: { message?: string } | string; error?: { message?: string } } } } | null;
  const d = e?.response?.data;
  const detail = typeof d?.detail === "string" ? d.detail : d?.detail?.message;
  return d?.error?.message || detail || d?.message || fallback;
}

export function qtyText(q: number | null | undefined, unit = ""): string {
  if (q === null || q === undefined) return "-";
  const text = Math.abs(q) >= 100 ? q.toLocaleString("en-US", { maximumFractionDigits: 1 }) : q.toLocaleString("en-US", { maximumFractionDigits: 3 });
  return unit ? `${text} ${unit}` : text;
}

export function deltaText(delta: number, unit = ""): string {
  if (delta === 0) return unit ? `0 ${unit}` : "0";
  return `${delta > 0 ? "+" : "-"}${qtyText(Math.abs(delta), unit)}`;
}

export function pctText(pct: number | null | undefined): string {
  if (pct === null || pct === undefined) return "-";
  return `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

export function filterItems(items: DiffItem[], filter: DiffFilter): DiffItem[] {
  return filter === "ALL" ? items : items.filter((i) => i.status !== "SAME" || i.source_moved);
}

export function defaultPair(runs: ComparableRun[], currentRunId: string | null | undefined): { from: string | undefined; to: string | undefined } {
  if (runs.length === 0) return { from: undefined, to: undefined };
  const at = runs.findIndex((r) => r.id === currentRunId);
  if (at === -1) return { from: runs[1]?.id, to: runs[0].id };
  return { from: runs[at + 1]?.id, to: runs[at].id };
}

export function headline(m: { changed: number; added: number; removed: number; same: number }): string {
  if (m.changed + m.added + m.removed === 0) return `Nothing changed: all ${m.same} work items are the same in both runs.`;
  const bits = [`${m.changed} changed`, `${m.added} new`, `${m.removed} not in the later run`].filter((b) => !b.startsWith("0 "));
  return `${bits.join(", ")}; ${m.same} the same.`;
}

export function sourceMoveText(item: DiffItem): string {
  if (!item.source_moved) return "";
  const now = item.sources.filter((s) => s.b !== 0).map((s) => `${s.source.replace(/_/g, " ").toLowerCase()} ${qtyText(s.b, item.unit)}`);
  return `Same total, but it now comes from: ${now.join(", ")}.`;
}

export function memberText(m: DiffMember, unit: string): string {
  const where = m.level ? ` (${m.level})` : "";
  const label = m.label ?? m.key ?? "";
  if (m.status === "ADDED") return `${label}${where}: new, ${qtyText(m.b, unit)}`;
  if (m.status === "REMOVED") return `${label}${where}: gone, was ${qtyText(m.a, unit)}`;
  return `${label}${where}: ${qtyText(m.a, unit)} to ${qtyText(m.b, unit)} (${deltaText(m.delta, unit)})`;
}

export function entriesFor(fix: FixList | undefined, audience: FixAudience): FixEntry[] {
  return (fix?.items ?? []).filter((e) => e.audience === audience);
}

export function whereText(e: FixEntry): string {
  const parts: string[] = [];
  if (e.levels.length) parts.push(e.levels.slice(0, 6).join(", ") + (e.levels.length > 6 ? ` and ${e.levels.length - 6} more` : ""));
  if (e.marks.length) parts.push("marks " + e.marks.slice(0, 8).join(", ") + (e.marks.length > 8 ? ` and ${e.marks.length - 8} more` : ""));
  return parts.join("; ");
}

export function fixText(fix: FixList | undefined, audience: FixAudience, title = "Drawing queries"): string {
  const rows = entriesFor(fix, audience);
  if (rows.length === 0) return "";
  return [title, "", ...rows.map((e, n) => `${n + 1}. ${e.topic}: ${e.ask}`)].join("\n") + "\n";
}

export function emptyFixWords(fix: FixList | undefined): string {
  if (!fix || fix.total > 0) return "";
  return "No open issue is recorded for this run. If the BOQ has not been built from it yet, build it first: the list is made from the review issues that the BOQ build records.";
}

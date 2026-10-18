import type { ConfirmMark, DriverMark, MarkState, RangeDrivers, RangeStale } from "../types/drawings-boq.types";

type Located = Pick<DriverMark, "measurement_id" | "sheet_id" | "drawing_id" | "project_id" | "state">;

export function markHref(m: Located): string | null {
  if (!m.project_id || !m.drawing_id || m.state === "gone") return null;
  const sheet = m.sheet_id ? `sheet=${encodeURIComponent(m.sheet_id)}&` : "";
  return `/app/takeoff/${encodeURIComponent(m.project_id)}/${encodeURIComponent(m.drawing_id)}?${sheet}m=${encodeURIComponent(m.measurement_id)}`;
}

export function markLabel(m: Pick<DriverMark, "page_no" | "tag">, fallback = "mark"): string {
  const page = m.page_no ? `p.${m.page_no}` : "";
  const parts = [page, m.tag ?? ""].filter((p) => p !== "");
  return parts.length > 0 ? parts.join(" · ") : fallback;
}

export const MOVED_STATES: readonly MarkState[] = ["reopened", "changed", "gone"];

export function staleCount(stale: RangeStale | undefined): number {
  return stale ? stale.reopened + stale.changed + stale.gone : 0;
}

export function staleOf(data: RangeDrivers | undefined): RangeStale | null {
  return data?.stale && staleCount(data.stale) > 0 ? data.stale : null;
}

function cell(v: string | number | null): string {
  if (v === null) return "";
  const raw = String(v);
  const s = typeof v === "string" && /^[=+\-@]/.test(raw) ? `'${raw}` : raw;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export const WORKLIST_HEADER = [
  "Rank",
  "Page",
  "Tag",
  "Feeds",
  "State",
  "Share of the spread %",
  "Low if this mark were exact",
  "High if this mark were exact",
  "Low after this and the ones above",
  "High after this and the ones above",
  "Unit",
] as const;

export function worklistCsv(rows: ConfirmMark[], unit: string): string {
  const lines = [WORKLIST_HEADER.join(",")];
  rows.forEach((m, i) => {
    lines.push(
      [i + 1, m.page_no, m.tag, m.items.join(" / "), m.state, m.share_pct, m.low_after, m.high_after, m.cum_low, m.cum_high, unit].map(cell).join(","),
    );
  });
  return `${lines.join("\r\n")}\r\n`;
}

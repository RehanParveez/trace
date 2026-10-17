import type { QuantityRange, RangeTotal } from "../types/drawings-boq.types";

export const GRADE_ORDER = ["PRINTED", "VERIFIED", "CONFIRMED", "PICTURE", "MEASURED", "ASSUMED", "MISSING", "NOT_READ"] as const;

const num = (v: unknown): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

export type RangeTone = "green" | "blue" | "gold" | "red" | "slate";

export function gradeTone(grade: string | null | undefined): RangeTone {
  switch (grade) {
    case "PRINTED":
    case "VERIFIED":
    case "CONFIRMED":
      return "green";
    case "PICTURE":
    case "MEASURED":
      return "blue";
    case "ASSUMED":
      return "gold";
    case "MISSING":
    case "NOT_READ":
      return "red";
    default:
      return "slate";
  }
}

export interface RangeView {
  low: number;
  likely: number;
  high: number;
  exact: boolean;
  complete: boolean;
  unboundedRows: number;
  leavesOutRows: number;
  weakest: string | null;
}

export function rangeView(range: QuantityRange | null | undefined): RangeView | null {
  if (!range) return null;
  const low = num(range.low);
  const high = num(range.high);
  const likely = num(range.likely);
  return {
    low,
    likely,
    high,
    exact: low === likely && high === likely,
    complete: Boolean(range.complete),
    unboundedRows: num(range.unbounded_rows),
    leavesOutRows: num(range.leaves_out_rows),
    weakest: range.weakest ?? null,
  };
}

export function reaches(range: QuantityRange | null | undefined): { down: number; up: number } | null {
  if (!range) return null;
  return { down: Math.max(0, num(range.likely) - num(range.low)), up: Math.max(0, num(range.high) - num(range.likely)) };
}

const round4 = (v: number): number => Math.round(v * 10000) / 10000;

export function rangeTotals(items: Array<{ unit: string; quantity: number | string; quantity_range?: QuantityRange | null }>): RangeTotal[] {
  const by = new Map<string, { likely: number; down: number; up: number; items: number; unbounded: number; leaves: number }>();
  for (const it of items) {
    const unit = it.unit || "";
    const slot = by.get(unit) ?? { likely: 0, down: 0, up: 0, items: 0, unbounded: 0, leaves: 0 };
    by.set(unit, slot);
    slot.items += 1;
    slot.likely += num(it.quantity);
    const r = reaches(it.quantity_range);
    if (!r) {
      slot.unbounded += 1;
      continue;
    }
    slot.down += r.down ** 2;
    slot.up += r.up ** 2;
    if (num(it.quantity_range?.unbounded_rows) > 0) slot.unbounded += 1;
    if (num(it.quantity_range?.leaves_out_rows) > 0) slot.leaves += 1;
  }
  return [...by.entries()]
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([unit, s]) => ({
      unit,
      likely: round4(s.likely),
      low: round4(s.likely - Math.sqrt(s.down)),
      high: round4(s.likely + Math.sqrt(s.up)),
      items: s.items,
      unbounded: s.unbounded,
      leaves_out: s.leaves,
    }));
}

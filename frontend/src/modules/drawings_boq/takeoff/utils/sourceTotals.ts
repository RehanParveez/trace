export interface SourceQuantity { source: string; quantity: string }
export interface SourceTotalItem {
  work_item_code: string;
  name: string | null;
  unit: string;
  total: string;
  rows: number;
  sources: SourceQuantity[];
  mixed: boolean;
}
export interface SourceTotalsReconciliation {
  replaced: number;
  variances: number;
  not_counted: number;
  verified: number;
  tolerance_pct: string | null;
  replaced_rows: Array<Record<string, unknown>>;
  variance_rows: Array<Record<string, unknown>>;
  not_counted_rows: Array<Record<string, unknown>>;
}
export interface SourceTotals {
  run: { id: string; completed_at: string | null } | null;
  items: SourceTotalItem[];
  reconciliation: SourceTotalsReconciliation;
  mixed_items: number;
}

export const SOURCE_TEXT: Record<string, string> = {
  MODEL: "Model",
  PDF_TAKEOFF: "PDF measurements",
  DERIVED: "Derived from the drawing",
  SCHEDULE_IMPORT: "Schedule",
  MANUAL: "Typed by hand",
  ESTIMATE: "Estimate",
};

export function sourceText(source: string): string {
  return SOURCE_TEXT[source] ?? source.toLowerCase().replace(/_/g, " ");
}

export function quantityText(value: string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

export function sourceShares(item: Pick<SourceTotalItem, "total" | "sources">): Array<{ source: string; quantity: string; pct: number }> {
  const total = Number(item.total);
  if (!Number.isFinite(total) || total === 0) return [];
  return item.sources.map((s) => ({ ...s, pct: Math.round((Number(s.quantity) / total) * 100) }));
}

export function itemsToShow(data: SourceTotals | undefined, onlyMixed: boolean): SourceTotalItem[] {
  const items = data?.items ?? [];
  const shown = onlyMixed ? items.filter((i) => i.mixed) : items;
  return [...shown].sort((a, b) => Number(b.mixed) - Number(a.mixed) || a.work_item_code.localeCompare(b.work_item_code));
}

export function hasReconciliation(r: SourceTotalsReconciliation | undefined): boolean {
  return Boolean(r && (r.replaced || r.variances || r.not_counted || r.verified));
}

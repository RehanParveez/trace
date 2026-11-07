import type { BillingView, BillLine } from "./billing.types";

export interface PricedLine extends Omit<BillLine, "sources"> {
  description: string | null;
  rate: number | null;
  rate_unit: string | null;
  amount: number | null;
  low: number | null;
  high: number | null;
  unpriced_why: string | null;
  assumed_share: number;
  by_floor: Record<string, number | null>;
}

export interface PricedTotals {
  grand: number;
  measured: number;
  assumed: number;
  priced: number;
  unpriced: number;
  by_section: Record<string, number | null>;
  by_floor: Record<string, number | null>;
  range: Record<string, number | null> | null;
}

export interface ProjectPricedRateBook {
  id: string;
  code: string;
  version: number;
  edition: string | null;
  scope: string;
  items: number;
  content_hash: string | null;
}

export interface PricedMaterials {
  totals: Record<string, number | null>;
  rows: { code: string; material: string; qty: number | null; how: string }[];
  missing: { code: string; why: string }[];
  coefficient_table: boolean;
}

export interface PricedView extends Omit<BillingView, "lines"> {
  lines: PricedLine[];
  totals: PricedTotals;
  rate_books: ProjectPricedRateBook[];
  rate_notes: string[];
  materials: PricedMaterials;
}

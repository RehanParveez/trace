import type { DerivedSteelStats, LedgerTrace, SteelEstimateStats } from "../types/drawings-boq.types";

export const ESTIMATE_RECIPE = "PDF_MEMBER_STEEL_ESTIMATE";

export interface SteelEstimateFamilyView {
  family: string;
  members: number;
  kg: string;
  low: string;
  high: string;
}

export interface SteelEstimateView {
  members: number;
  kg: string;
  low: string;
  high: string;
  measuredKg: string;
  totalKg: string;
  totalLow: string;
  totalHigh: string;
  sharePct: string;
  slabRule: string | null;
  slabRuleSource: string | null;
  families: SteelEstimateFamilyView[];
  skipped: { code: string; count: number }[];
}

function add(a: string, b: string): string {
  return String(Math.round((Number(a) + Number(b)) * 1000) / 1000);
}

export function steelEstimateView(st: DerivedSteelStats | null | undefined): SteelEstimateView | null {
  const est: SteelEstimateStats | undefined = st?.estimate;
  if (!est || !est.enabled) return null;
  const skipped = Object.entries(est.skipped ?? {}).filter(([, n]) => Number(n) > 0).map(([code, count]) => ({ code, count: Number(count) }));
  const members = Number(est.members ?? 0);
  if (members === 0 && skipped.length === 0) return null;
  const measured = String(st?.measured_kg ?? "0");
  const kg = String(est.kg ?? "0");
  return {
    members,
    kg,
    low: String(est.kg_low ?? kg),
    high: String(est.kg_high ?? kg),
    measuredKg: measured,
    totalKg: add(measured, kg),
    totalLow: String(st?.total_low_kg ?? add(measured, String(est.kg_low ?? kg))),
    totalHigh: String(st?.total_high_kg ?? add(measured, String(est.kg_high ?? kg))),
    sharePct: String(st?.estimated_share_pct ?? "0"),
    slabRule: est.slab_rule_kg_per_m2 ?? null,
    slabRuleSource: est.slab_rule_source ?? null,
    families: Object.entries(est.by_family ?? {}).map(([family, v]) => ({ family, members: Number(v.members), kg: String(v.kg), low: String(v.kg_low), high: String(v.kg_high) })),
    skipped,
  };
}

export interface SteelEstimateSourceView {
  page: number;
  category: string;
  tag: string;
  instance: number;
  instances: number;
  lengthMm: number;
  widthMm: number;
  depthMm: number;
  basis: "QS_RULE" | "USUAL_KG_PER_M3";
  unit: string;
  quantity: string;
  rate: string;
  rateLow: string;
  rateHigh: string;
  bareKg: string | null;
  wastagePct: string | null;
  kg: string | null;
  kgLow: string | null;
  kgHigh: string | null;
}

export function estimateSourceView(trace: LedgerTrace | null | undefined): SteelEstimateSourceView | null {
  const inputs = trace?.inputs as { recipe?: string; steel_source?: Record<string, unknown> } | undefined;
  const raw = inputs?.steel_source as
    | {
        page_no?: number; category?: string; tag?: string | null; instance?: number; instances?: number; size_mm?: number[]; bare_kg?: string; wastage_pct?: string;
        estimate?: { basis: "QS_RULE" | "USUAL_KG_PER_M3"; unit: string; quantity: string; kg_per_unit: string; kg_per_unit_low: string; kg_per_unit_high: string };
      }
    | undefined;
  if (inputs?.recipe !== ESTIMATE_RECIPE || !raw?.estimate || !Array.isArray(raw.size_mm) || raw.size_mm.length < 3) return null;
  const net = (trace?.net ?? {}) as { kg?: string; kg_low?: string; kg_high?: string };
  return {
    page: Number(raw.page_no),
    category: String(raw.category ?? ""),
    tag: raw.tag ?? "",
    instance: Number(raw.instance),
    instances: Number(raw.instances),
    lengthMm: Number(raw.size_mm[0]),
    widthMm: Number(raw.size_mm[1]),
    depthMm: Number(raw.size_mm[2]),
    basis: raw.estimate.basis,
    unit: raw.estimate.unit,
    quantity: raw.estimate.quantity,
    rate: raw.estimate.kg_per_unit,
    rateLow: raw.estimate.kg_per_unit_low,
    rateHigh: raw.estimate.kg_per_unit_high,
    bareKg: raw.bare_kg ?? null,
    wastagePct: raw.wastage_pct ?? null,
    kg: net.kg ?? null,
    kgLow: net.kg_low ?? null,
    kgHigh: net.kg_high ?? null,
  };
}

export interface UnprintedSteel {
  enabled: boolean;
  members: number;
  kg: number;
  kg_low: number;
  kg_high: number;
  kg_with_printed: number;
  kg_low_with_printed: number;
  kg_high_with_printed: number;
  slab_rule_kg_per_m2: number | null;
  by_family: Record<string, { members: number; kg: number; kg_low: number; kg_high: number }>;
  not_estimated: Record<string, number>;
}

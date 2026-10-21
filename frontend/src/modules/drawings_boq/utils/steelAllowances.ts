import type { DerivedStats, SteelAllowanceStats, SteelRingZoneStats } from "../types/drawings-boq.types";

export interface SteelAllowancesView {
  ran: boolean;
  reason: string | null;
  wireKg: string | null;
  wirePct: number | null;
  wireAssumed: boolean;
  chairsKg: string | null;
  chairsKgPerM2: number | null;
  chairsAssumed: boolean;
  slabAreaM2: string;
  reinforcementKg: string;
  totalKg: string;
  sharePct: string;
  skipped: { code: string; count: number }[];
}

function num(value: string | number | null | undefined): number | null {
  if (value == null) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function steelAllowancesView(stats: DerivedStats | null | undefined): SteelAllowancesView | null {
  const s: SteelAllowanceStats | undefined = stats?.steel_allowances;
  if (!s || !s.enabled) return null;
  return {
    ran: Boolean(s.ran),
    reason: s.reason ?? null,
    wireKg: s.wire_on ? String(s.wire_kg ?? "0") : null,
    wirePct: num(s.wire_pct),
    wireAssumed: s.wire_source === "default",
    chairsKg: s.chairs_on ? String(s.chairs_kg ?? "0") : null,
    chairsKgPerM2: num(s.chairs_kg_per_m2),
    chairsAssumed: s.chairs_source === "default",
    slabAreaM2: String(s.slab_area_m2 ?? "0"),
    reinforcementKg: String(s.reinforcement_kg ?? "0"),
    totalKg: String(s.kg ?? "0"),
    sharePct: String(s.share_of_reinforcement_pct ?? "0"),
    skipped: Object.entries(s.skipped ?? {}).map(([code, count]) => ({ code, count: Number(count) })),
  };
}

export function steelAllowancesReasonWords(reason: string | null | undefined): string {
  switch (reason) {
    case "SWITCHED_OFF":
      return "Both settings are off.";
    case "NO_REINFORCEMENT":
      return "The run has no reinforcement rows to add them to. Read the bars from the drawing, or estimate the steel of the members first.";
    case "NOTHING_TO_ADD":
      return "The percentage and the rate gave no weight.";
    default:
      return reason ?? "";
  }
}

export function steelAllowanceSkipWords(code: string): string {
  switch (code) {
    case "ROW_WITHOUT_MEMBER":
      return "steel rows from the model, whose members are not known, get no chairs";
    case "SLAB_WITHOUT_SIZE":
      return "slab rows with no size get no chairs";
    default:
      return code;
  }
}

export interface RingZoneView {
  marks: number;
  denseSpacingMm: number | null;
  skipped: { code: string; count: number }[];
}

export function ringZoneView(stats: DerivedStats | null | undefined): RingZoneView | null {
  const z: SteelRingZoneStats | undefined = stats?.steel?.ring_zone;
  if (!z || !z.enabled) return null;
  return {
    marks: Number(z.marks ?? 0),
    denseSpacingMm: num(z.dense_spacing_mm),
    skipped: Object.entries(z.skipped ?? {}).map(([code, count]) => ({ code, count: Number(count) })),
  };
}

export function ringZoneSkipWords(code: string): string {
  switch (code) {
    case "PRINTED":
      return "the drawing prints a closer zone";
    case "ALREADY_CLOSE":
      return "the printed spacing is already as close";
    case "MEMBER_TOO_SHORT":
      return "too short for two zones";
    default:
      return code;
  }
}

export function allowancesLine(a: { binding_wire_kg: number; chairs_kg: number; kg: number; with_bars_kg: number; share_pct: number }): string {
  const fmt = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: v >= 100 ? 0 : 1 });
  const parts: string[] = [];
  if (a.binding_wire_kg > 0) parts.push(`binding wire ${fmt(a.binding_wire_kg)} kg`);
  if (a.chairs_kg > 0) parts.push(`chairs ${fmt(a.chairs_kg)} kg`);
  return `On top of the bars, not in the weight above: ${parts.join(" and ")} (${a.share_pct.toFixed(1)} % of the bars). With them the steel is ${fmt(a.with_bars_kg)} kg.`;
}

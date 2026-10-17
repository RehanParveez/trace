import type { DatumView } from "../api/datums.api";
import type { ElementParameterRange } from "../api/elementParams.api";
import type { DerivedFoundationEntry, EarthBalance, RunStats, StageBand } from "../types/drawings-boq.types";

export const LEVEL_RANGE = { min: -100000, max: 300000 } as const;

export type ParseResult = { value?: number | null; error?: "NOT_A_NUMBER" | "OUT_OF_RANGE" };

function parseNumber(raw: string | undefined, min: number, max: number): ParseResult {
  const text = (raw ?? "").trim();
  if (text === "") return {};
  const n = Number(text);
  if (!Number.isFinite(n)) return { error: "NOT_A_NUMBER" };
  if (n < min || n > max) return { error: "OUT_OF_RANGE" };
  return { value: n };
}

export function parseLevel(raw: string | undefined): ParseResult {
  return parseNumber(raw, LEVEL_RANGE.min, LEVEL_RANGE.max);
}

export function parseElementValue(raw: string | undefined, range: ElementParameterRange | undefined): ParseResult {
  return parseNumber(raw, range?.low ?? 0, range?.high ?? Number.MAX_SAFE_INTEGER);
}

export function datumDraft(datums: readonly DatumView[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const d of datums) {
    if (d.editable && d.typed_z_mm !== null) out[d.name] = String(d.typed_z_mm);
  }
  return out;
}

export function datumUpdate(draft: Record<string, string>, datums: readonly DatumView[]): { values: Record<string, number | null>; errors: string[] } {
  const values: Record<string, number | null> = {};
  const errors: string[] = [];
  for (const d of datums) {
    if (!d.editable) continue;
    const parsed = parseLevel(draft[d.name]);
    if (parsed.error) {
      errors.push(d.name);
      continue;
    }
    const next = parsed.value ?? null;
    if (next !== d.typed_z_mm) values[d.name] = next;
  }
  return { values, errors };
}

export function missingTypedNames(typed: Record<string, number>, datums: readonly DatumView[]): string[] {
  const known = new Set(datums.map((d) => d.name));
  return Object.keys(typed).filter((n) => !known.has(n)).sort();
}

export function bandText(band: StageBand): string {
  const lo = band.from_mm === null ? "" : `${Math.round(band.from_mm)}`;
  const hi = band.to_mm === null ? "" : `${Math.round(band.to_mm)}`;
  if (lo === "" && hi === "") return "";
  if (lo === "") return `up to ${hi} mm`;
  if (hi === "") return `from ${lo} mm`;
  return `${lo} to ${hi} mm`;
}

export interface BalanceView {
  excavation: string;
  backfill: string;
  buried: string;
  carted: string;
  gap: string;
  closes: boolean;
  outside: string;
  outsideTaken: boolean;
  negativeRows: number;
}

export function balanceView(balance: EarthBalance | null | undefined): BalanceView | null {
  if (!balance) return null;
  const outside = Number(balance.structure_outside_trench_m3);
  return {
    excavation: balance.excavation_m3,
    backfill: balance.backfill_m3,
    buried: balance.buried_m3,
    carted: balance.carted_m3,
    gap: balance.gap_m3,
    closes: balance.closes,
    outside: balance.structure_outside_trench_m3,
    outsideTaken: Number.isFinite(outside) && outside > 0.05,
    negativeRows: balance.negative_backfill_rows,
  };
}

export type DpcWhy = "ALL_ITEMS_IN_MODEL" | "NO_PROFILE" | "NO_WALL_ON_DPC" | "NO_DPC_LEVEL";

export interface DpcView {
  ran: boolean;
  areaM2: string | null;
  rows: number;
  doorsTakenOut: number;
  levelMm: number | null;
  levelSource: string | null;
  why: DpcWhy | null;
  verticalTaken: boolean;
}

export function dpcView(stats: RunStats | null | undefined): DpcView | null {
  const dpc = stats?.derived?.dpc;
  if (!dpc || !dpc.enabled) return null;
  const level = dpc.model?.level ?? null;
  return {
    ran: Boolean(dpc.ran),
    areaM2: dpc.area_m2 ?? null,
    rows: dpc.rows ?? 0,
    doorsTakenOut: (dpc.model?.doors_taken_out ?? 0) + (dpc.pdf?.doors_taken_out ?? 0),
    levelMm: level ? level.z_mm : null,
    levelSource: level ? level.source : null,
    why: dpc.ran ? null : (dpc.reason ?? null),
    verticalTaken: dpc.vertical !== undefined && dpc.vertical !== "NOT_TAKEN",
  };
}

export interface ElementRow {
  id: string;
  label: string;
  bed: string;
  names: string[];
  values: Record<string, { value: number; source: string }>;
}

export const ELEMENT_NAMES = ["working_space_mm", "pcc_projection_mm", "pcc_thickness_mm", "ballast_clearance_mm", "ballast_thickness_mm"] as const;

export function elementRows(list: readonly DerivedFoundationEntry[] | undefined, labels: Record<string, string>): ElementRow[] {
  return (list ?? []).map((f) => {
    const names = ELEMENT_NAMES.filter((n) => f.params[n] !== undefined);
    const values: ElementRow["values"] = {};
    for (const n of names) values[n] = { value: f.params[n].value, source: f.params[n].source };
    return { id: f.element_id, label: labels[f.element_id] || f.label || f.role, bed: f.bed, names: [...names], values };
  });
}

export function elementDraft(saved: Record<string, Record<string, number>>): Record<string, Record<string, string>> {
  const out: Record<string, Record<string, string>> = {};
  for (const [eid, items] of Object.entries(saved)) {
    out[eid] = Object.fromEntries(Object.entries(items).map(([n, v]) => [n, String(v)]));
  }
  return out;
}

export function elementUpdate(
  draft: Record<string, Record<string, string>>,
  saved: Record<string, Record<string, number>>,
  rows: readonly ElementRow[],
  ranges: Record<string, ElementParameterRange>,
): { values: Record<string, Record<string, number | null>>; labels: Record<string, string>; errors: string[] } {
  const values: Record<string, Record<string, number | null>> = {};
  const labels: Record<string, string> = {};
  const errors: string[] = [];
  for (const row of rows) {
    for (const n of row.names) {
      const parsed = parseElementValue(draft[row.id]?.[n], ranges[n]);
      if (parsed.error) {
        errors.push(`${row.id}:${n}`);
        continue;
      }
      const next = parsed.value ?? null;
      const before = saved[row.id]?.[n] ?? null;
      if (next !== before) {
        (values[row.id] ??= {})[n] = next;
        labels[row.id] = row.label;
      }
    }
  }
  return { values, labels, errors };
}

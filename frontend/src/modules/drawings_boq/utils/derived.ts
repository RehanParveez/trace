import type {BOQItemSpec, DerivedParamName, DerivedParams, LayerSplitTrace, LedgerTrace,
} from "../types/drawings-boq.types";

export interface DerivedFieldDef {
  key: DerivedParamName;
  defaultMm: number | null;
  min: number;
  max: number;
}

export const DERIVED_FIELDS: readonly DerivedFieldDef[] = [
  { key: "working_space_mm", defaultMm: 150, min: 0, max: 3000 },
  { key: "pcc_projection_mm", defaultMm: 100, min: 0, max: 1000 },
  { key: "pcc_thickness_mm", defaultMm: 100, min: 0, max: 600 },
  { key: "ngl_below_ffl_mm", defaultMm: null, min: -2000, max: 3000 },
];

export type DerivedInput = Partial<Record<DerivedParamName, string>>;

export function parseDerivedField(raw: string | undefined, def: DerivedFieldDef): { value?: number; error?: "NOT_A_NUMBER" | "OUT_OF_RANGE" } {
  const text = (raw ?? "").trim();
  if (text === "") {
    return {};
  }
  const n = Number(text);
  if (!Number.isFinite(n)) {
    return { error: "NOT_A_NUMBER" };
  }
  if (n < def.min || n > def.max) {
    return { error: "OUT_OF_RANGE" };
  }
  return { value: n };
}

export function derivedParamsFromInput(input: DerivedInput): { params: DerivedParams | undefined; errors: DerivedParamName[] } {
  const params: DerivedParams = {};
  const errors: DerivedParamName[] = [];
  for (const def of DERIVED_FIELDS) {
    const parsed = parseDerivedField(input[def.key], def);
    if (parsed.error) {
      errors.push(def.key);
    } else if (parsed.value !== undefined) {
      params[def.key] = parsed.value;
    }
  }
  return { params: Object.keys(params).length > 0 ? params : undefined, errors };
}

export function mmToInches(mm: number): string {
  const inches = mm / 25.4;
  return Number.isInteger(inches) ? String(inches) : inches.toFixed(1);
}

export function isDerivedSpec(spec: BOQItemSpec | null | undefined): boolean {
  return spec?.kind === "DERIVED";
}

export type DerivedBasis = "user" | "convention" | "default";

export interface DerivedBasisRow {
  key: string;
  value: number;
  basis: DerivedBasis | null;
}

const BASIS_ORDER = ["working_space_mm", "pcc_projection_mm", "pcc_thickness_mm", "ngl"];

export function derivedBasisRows(spec: BOQItemSpec | null | undefined): DerivedBasisRow[] {
  if (!isDerivedSpec(spec)) {
    return [];
  }
  const params = spec?.params ?? {};
  const basis = (spec?.basis ?? {}) as Record<string, string>;
  const rows: DerivedBasisRow[] = [];
  for (const key of BASIS_ORDER) {
    const value = key === "ngl" ? spec?.ngl_z_mm : params[key];
    if (typeof value !== "number") {
      continue;
    }
    const b = basis[key];
    rows.push({ key, value, basis: b === "user" || b === "convention" || b === "default" ? b : null });
  }
  return rows;
}

export function derivedHasAssumption(spec: BOQItemSpec | null | undefined): boolean {
  return derivedBasisRows(spec).some((r) => r.basis === "default");
}

export interface LayerSplitView {
  family: string;
  ofM3: string;
  billedThicknessMm: string;
  totalThicknessMm: string;
  declaredThicknessMm: string | null;
  excludedM3: string;
  sharePercent: number;
  layers: { material: string; family: string; thicknessMm: string }[];
}

export function layerSplitView(trace: LedgerTrace | null | undefined): LayerSplitView | null {
  const raw = (trace?.inputs as { layer_split?: LayerSplitTrace } | undefined)?.layer_split;
  if (!raw || !Array.isArray(raw.layers) || raw.layers.length === 0) {
    return null;
  }
  const share = Number(raw.share);
  return {
    family: String(raw.family ?? ""),
    ofM3: String(raw.of_m3 ?? ""),
    billedThicknessMm: String(raw.billed_thickness_mm ?? ""),
    totalThicknessMm: String(raw.total_thickness_mm ?? ""),
    declaredThicknessMm: raw.declared_thickness_mm ?? null,
    excludedM3: String(raw.excluded_m3 ?? "0"),
    sharePercent: Number.isFinite(share) ? Math.round(share * 1000) / 10 : 0,
    layers: raw.layers.map((l) => ({ material: l.material, family: l.family, thicknessMm: l.thickness_mm })),
  };
}

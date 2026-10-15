import type {BOQItemSpec, DerivedClaims, DerivedParamName, DerivedParams, DerivedPdfSource, DerivedStats, FormworkSource, LayerSplitTrace, LedgerTrace, SteelBarLine, SteelRingLine, SteelSource,
} from "../types/drawings-boq.types";

export interface DerivedFieldDef {
  key: DerivedParamName;
  defaultMm: number | null;
  min: number;
  max: number;
  flag?: boolean;
  asked?: boolean;
  unit?: "dia";
}

export const DERIVED_FIELDS: readonly DerivedFieldDef[] = [
  { key: "working_space_mm", defaultMm: 150, min: 0, max: 3000 },
  { key: "pcc_projection_mm", defaultMm: 100, min: 0, max: 1000 },
  { key: "pcc_thickness_mm", defaultMm: 100, min: 0, max: 600 },
  { key: "ballast_clearance_mm", defaultMm: 152.4, min: 0, max: 1000 },
  { key: "ballast_thickness_mm", defaultMm: 304.8, min: 0, max: 1500 },
  { key: "wall_bed", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "shoring", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "footing_formwork", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "slab_edge_formwork", defaultMm: 1, min: 0, max: 1, flag: true },
  { key: "steel_cover_mm", defaultMm: 38.1, min: 10, max: 100 },
  { key: "ring_hook_dia", defaultMm: 20, min: 0, max: 40, unit: "dia" },
  { key: "ngl_below_ffl_mm", defaultMm: null, min: -2000, max: 3000 },
  { key: "footing_bottom_below_ngl_mm", defaultMm: null, min: 1, max: 10000, asked: true },
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

export function derivedInputFromParams(values: DerivedParams | undefined): DerivedInput {
  const input: DerivedInput = {};
  for (const def of DERIVED_FIELDS) {
    const value = values?.[def.key];
    if (typeof value === "number") {
      input[def.key] = String(value);
    }
  }
  return input;
}

export function derivedUpdateFromInput(input: DerivedInput): Partial<Record<DerivedParamName, number | null>> {
  const update: Partial<Record<DerivedParamName, number | null>> = {};
  for (const def of DERIVED_FIELDS) {
    const parsed = parseDerivedField(input[def.key], def);
    if (parsed.error) {
      continue;
    }
    update[def.key] = parsed.value ?? null;
  }
  return update;
}

export function mmToInches(mm: number): string {
  const inches = mm / 25.4;
  return Number.isInteger(inches) ? String(inches) : inches.toFixed(1);
}

export function isDerivedSpec(spec: BOQItemSpec | null | undefined): boolean {
  return spec?.kind === "DERIVED";
}

export type DerivedBasis = "user" | "convention" | "default" | "claim";

export interface DerivedBasisRow {
  key: string;
  value: number;
  basis: DerivedBasis | null;
}

const BASIS_ORDER = ["working_space_mm", "pcc_projection_mm", "pcc_thickness_mm", "ballast_clearance_mm", "ballast_thickness_mm", "shoring", "footing_formwork", "slab_edge_formwork", "steel_cover_mm", "ring_hook_dia", "ngl"];

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
    rows.push({ key, value, basis: b === "user" || b === "convention" || b === "default" || b === "claim" ? b : null });
  }
  return rows;
}

export function derivedHasAssumption(spec: BOQItemSpec | null | undefined): boolean {
  return derivedBasisRows(spec).some((r) => r.basis === "default");
}

export interface DerivedWaitingView {
  waiting: number;
  tags: string[];
  pages: number[];
}

export function derivedWaitingView(claims: DerivedClaims | null | undefined): DerivedWaitingView | null {
  const waiting = Number(claims?.waiting ?? 0);
  if (!claims || !Number.isFinite(waiting) || waiting <= 0) {
    return null;
  }
  const list = Array.isArray(claims.waiting_list) ? claims.waiting_list : [];
  const tags = Array.from(new Set(list.map((x) => x.tag).filter((x): x is string => typeof x === "string" && x !== ""))).sort();
  const pages = Array.from(new Set(list.map((x) => x.page_no).filter((x) => Number.isFinite(x)))).sort((a, b) => a - b);
  return { waiting, tags, pages };
}

export interface DerivedPdfSourceView {
  page: number;
  tag: string;
  instance: number;
  instances: number;
  lengthMm: number;
  widthMm: number;
  thicknessMm: number;
  bottomBelowGroundMm: number;
}

export function derivedPdfSourceView(trace: LedgerTrace | null | undefined): DerivedPdfSourceView | null {
  const raw = (trace?.inputs as { pdf_source?: DerivedPdfSource } | undefined)?.pdf_source;
  if (!raw || !Array.isArray(raw.size_mm) || raw.size_mm.length < 3) {
    return null;
  }
  return {
    page: Number(raw.page_no),
    tag: raw.tag ?? "",
    instance: Number(raw.instance),
    instances: Number(raw.instances),
    lengthMm: Number(raw.size_mm[0]),
    widthMm: Number(raw.size_mm[1]),
    thicknessMm: Number(raw.size_mm[2]),
    bottomBelowGroundMm: Number(raw.bottom_below_ngl_mm),
  };
}

export function isFormworkSpec(spec: BOQItemSpec | null | undefined): boolean {
  return spec?.kind === "DERIVED" && spec?.recipe === "STRUCT_FORMWORK";
}

export function isSteelSpec(spec: BOQItemSpec | null | undefined): boolean {
  return spec?.kind === "DERIVED" && spec?.recipe === "PDF_LINTEL_STEEL";
}

export interface SteelSourceView {
  page: number;
  category: string;
  tag: string;
  instance: number;
  instances: number;
  lengthMm: number;
  widthMm: number;
  depthMm: number;
  bars: { role: string; n: number; bar: number; lengthM: string; kg: string }[];
  rings: { bar: number; spacingMm: string; count: number; cutLengthM: string; kg: string } | null;
}

export function steelSourceView(trace: LedgerTrace | null | undefined): SteelSourceView | null {
  const raw = (trace?.inputs as { steel_source?: SteelSource } | undefined)?.steel_source;
  if (!raw || !Array.isArray(raw.size_mm) || raw.size_mm.length < 3 || !Array.isArray(raw.bars)) {
    return null;
  }
  const ring: SteelRingLine | null = raw.rings ?? null;
  return {
    page: Number(raw.page_no),
    category: String(raw.category ?? ""),
    tag: raw.tag ?? "",
    instance: Number(raw.instance),
    instances: Number(raw.instances),
    lengthMm: Number(raw.size_mm[0]),
    widthMm: Number(raw.size_mm[1]),
    depthMm: Number(raw.size_mm[2]),
    bars: raw.bars.map((b: SteelBarLine) => ({ role: String(b.role), n: Number(b.n), bar: Number(b.bar), lengthM: String(b.length_m), kg: String(b.kg) })),
    rings: ring ? { bar: Number(ring.bar), spacingMm: String(ring.spacing_mm), count: Number(ring.count), cutLengthM: String(ring.cut_length_m), kg: String(ring.kg) } : null,
  };
}

export interface SteelStatsView {
  ran: boolean;
  reason: string | null;
  kg: string;
  rows: number;
  categories: { category: string; marks: number; kg: string }[];
  noBars: number;
  assumed: string[];
  lapAndWastageNotAdded: boolean;
}

export function steelStatsView(stats: DerivedStats | null | undefined): SteelStatsView | null {
  const st = stats?.steel;
  if (!st || !st.enabled || st.reason === "NO_MEMBERS") {
    return null;
  }
  const categories = Object.entries(st.by_category ?? {}).map(([category, v]) => ({ category, marks: Number(v.marks), kg: String(v.kg) }));
  return {
    ran: Boolean(st.ran),
    reason: st.reason ?? null,
    kg: String(st.kg ?? "0"),
    rows: Number(st.rows ?? 0),
    categories,
    noBars: Number(st.skipped?.NO_BARS ?? 0),
    assumed: Array.isArray(st.assumed) ? st.assumed : [],
    lapAndWastageNotAdded: Boolean(st.lap_and_wastage_not_added),
  };
}

export interface FormworkSourceView {
  page: number;
  category: string;
  tag: string;
  instance: number;
  instances: number;
  lengthMm: number;
  widthMm: number;
  depthMm: number;
  faces: { name: string; m2: string }[];
}

export function formworkSourceView(trace: LedgerTrace | null | undefined): FormworkSourceView | null {
  const raw = (trace?.inputs as { formwork_source?: FormworkSource } | undefined)?.formwork_source;
  if (!raw || !Array.isArray(raw.size_mm) || raw.size_mm.length < 3 || !Array.isArray(raw.faces)) {
    return null;
  }
  return {
    page: Number(raw.page_no),
    category: String(raw.category ?? ""),
    tag: raw.tag ?? "",
    instance: Number(raw.instance),
    instances: Number(raw.instances),
    lengthMm: Number(raw.size_mm[0]),
    widthMm: Number(raw.size_mm[1]),
    depthMm: Number(raw.size_mm[2]),
    faces: raw.faces.map((f) => ({ name: String(f.name), m2: String(f.m2) })),
  };
}

export interface FormworkStatsView {
  ran: boolean;
  reason: string | null;
  areaM2: string;
  rows: number;
  categories: { category: string; marks: number; m2: string }[];
  footingsLeftOut: number;
  assumed: string[];
  contactNotDeducted: boolean;
}

export function formworkStatsView(stats: DerivedStats | null | undefined): FormworkStatsView | null {
  const fw = stats?.formwork;
  if (!fw || !fw.enabled || fw.reason === "NO_MEMBERS") {
    return null;
  }
  const categories = Object.entries(fw.by_category ?? {}).map(([category, v]) => ({ category, marks: Number(v.marks), m2: String(v.m2) }));
  return {
    ran: Boolean(fw.ran),
    reason: fw.reason ?? null,
    areaM2: String(fw.area_m2 ?? "0"),
    rows: Number(fw.rows ?? 0),
    categories,
    footingsLeftOut: Number(fw.skipped?.FOOTING_NOT_SHUTTERED_DEFAULT ?? 0),
    assumed: Array.isArray(fw.assumed) ? fw.assumed : [],
    contactNotDeducted: Boolean(fw.contact_not_deducted),
  };
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

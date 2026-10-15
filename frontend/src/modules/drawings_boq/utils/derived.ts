import type {BOQItemSpec, DerivedClaims, DerivedParamName, DerivedParams, DerivedPdfSource, DerivedStats, FormworkSource, LayerSplitTrace, LedgerTrace, SteelLine, SteelSource,
} from "../types/drawings-boq.types";

export interface DerivedFieldDef {
  key: DerivedParamName;
  defaultMm: number | null;
  min: number;
  max: number;
  flag?: boolean;
  asked?: boolean;
  unit?: "dia" | "pct";
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
  { key: "formwork_shared_faces", defaultMm: 1, min: 0, max: 1, flag: true },
  { key: "steel_cover_mm", defaultMm: 38.1, min: 10, max: 100 },
  { key: "ring_hook_dia", defaultMm: 20, min: 0, max: 40, unit: "dia" },
  { key: "bar_lap_dia", defaultMm: 40, min: 0, max: 80, unit: "dia" },
  { key: "bar_anchor_dia", defaultMm: 0, min: 0, max: 80, unit: "dia" },
  { key: "steel_wastage_pct", defaultMm: 0, min: 0, max: 15, unit: "pct" },
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

const BASIS_ORDER = ["working_space_mm", "pcc_projection_mm", "pcc_thickness_mm", "ballast_clearance_mm", "ballast_thickness_mm", "shoring", "footing_formwork", "slab_edge_formwork", "formwork_shared_faces", "steel_cover_mm", "ring_hook_dia", "bar_lap_dia", "bar_anchor_dia", "steel_wastage_pct", "ngl"];

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
  return spec?.kind === "DERIVED" && (spec?.recipe === "PDF_MEMBER_STEEL" || spec?.recipe === "PDF_LINTEL_STEEL");
}

export interface SteelLineView {
  kind: "bars" | "rings" | "mesh";
  role: string;
  count: number;
  size: string;
  cutLengthM: string;
  kg: string;
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
  lines: SteelLineView[];
  bareKg: string | null;
  wastagePct: string | null;
  concreteM3: string | null;
}

function sizeLabel(bar: number | null | undefined, diaMm: string): string {
  return bar ? `#${bar}` : `${Number(diaMm)} mm`;
}

function legacyLines(raw: SteelSource): SteelLine[] {
  const lines: SteelLine[] = (raw.bars ?? []).map((b) => ({
    kind: "bars", role: String(b.role), bar: Number(b.bar), dia_mm: String(Number(b.bar) * 3.175), count: Number(b.n), cut_length_m: "", kg_per_m: "", length_m: String(b.length_m), kg: String(b.kg),
  }));
  if (raw.rings) {
    lines.push({ kind: "rings", role: "ring", bar: Number(raw.rings.bar), dia_mm: String(Number(raw.rings.bar) * 3.175), count: Number(raw.rings.count), cut_length_m: String(raw.rings.cut_length_m), kg_per_m: "", length_m: "", kg: String(raw.rings.kg) });
  }
  return lines;
}

export function steelSourceView(trace: LedgerTrace | null | undefined): SteelSourceView | null {
  const raw = (trace?.inputs as { steel_source?: SteelSource } | undefined)?.steel_source;
  if (!raw || !Array.isArray(raw.size_mm) || raw.size_mm.length < 3) {
    return null;
  }
  const lines = Array.isArray(raw.lines) ? raw.lines : Array.isArray(raw.bars) ? legacyLines(raw) : null;
  if (!lines) {
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
    lines: lines.map((l) => ({ kind: l.kind, role: String(l.role), count: Number(l.count), size: sizeLabel(l.bar, l.dia_mm), cutLengthM: String(l.cut_length_m), kg: String(l.kg) })),
    bareKg: raw.bare_kg ?? null,
    wastagePct: raw.wastage_pct ?? null,
    concreteM3: raw.concrete_m3 ?? null,
  };
}

export interface SteelStatsView {
  ran: boolean;
  reason: string | null;
  kg: string;
  bareKg: string;
  withFivePctKg: string;
  wastagePct: string;
  rows: number;
  categories: { category: string; marks: number; kg: string }[];
  diameters: { diaMm: string; kg: string; lengthM: string }[];
  intensity: { family: string; kgPerM3: string; concreteM3: string; low: string; high: string; status: "IN_RANGE" | "BELOW_RANGE" | "ABOVE_RANGE" }[];
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
  const diameters = Object.entries(st.by_diameter ?? {})
    .map(([diaMm, v]) => ({ diaMm, kg: String(v.kg), lengthM: String(v.length_m) }))
    .sort((a, b) => Number(a.diaMm) - Number(b.diaMm));
  const intensity = Object.entries(st.intensity ?? {}).map(([family, v]) => ({
    family, kgPerM3: String(v.kg_per_m3), concreteM3: String(v.concrete_m3), low: String(v.range[0]), high: String(v.range[1]), status: v.status,
  }));
  return {
    ran: Boolean(st.ran),
    reason: st.reason ?? null,
    kg: String(st.kg ?? "0"),
    bareKg: String(st.bare_kg ?? st.kg ?? "0"),
    withFivePctKg: String(st.with_5pct_kg ?? st.kg ?? "0"),
    wastagePct: String(st.wastage_pct ?? "0"),
    rows: Number(st.rows ?? 0),
    categories,
    diameters,
    intensity,
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

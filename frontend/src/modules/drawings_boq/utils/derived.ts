import type {BOQItemSpec, DerivedClaims, DerivedParamName, DerivedParams, DerivedPdfSource, DerivedStats, FormworkSource, LayerSplitTrace, LedgerTrace, SteelLine, SteelSource,
} from "../types/drawings-boq.types";

import { steelEstimateView } from "./steelEstimate";
import type { SteelEstimateView } from "./steelEstimate";

export interface DerivedFieldDef {
  key: DerivedParamName;
  defaultMm: number | null;
  min: number;
  max: number;
  flag?: boolean;
  asked?: boolean;
  unit?: "dia" | "pct" | "kgm2";
  label?: string;
  hint?: string;
  choices?: readonly { value: string; label: string }[];
}

export const DERIVED_FIELDS: readonly DerivedFieldDef[] = [
  { key: "working_space_mm", defaultMm: 150, min: 0, max: 3000 },
  { key: "pcc_projection_mm", defaultMm: 100, min: 0, max: 1000 },
  { key: "pcc_thickness_mm", defaultMm: 76.2, min: 0, max: 600 },
  { key: "ballast_clearance_mm", defaultMm: 152.4, min: 0, max: 1000 },
  { key: "ballast_thickness_mm", defaultMm: 304.8, min: 0, max: 1500 },
  { key: "wall_bed", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "shoring", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "footing_formwork", defaultMm: 1, min: 0, max: 1, flag: true },
  { key: "slab_edge_formwork", defaultMm: 1, min: 0, max: 1, flag: true },
  { key: "formwork_shared_faces", defaultMm: 1, min: 0, max: 1, flag: true },
  { key: "tank_base_formwork", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "steel_cover_mm", defaultMm: 38.1, min: 10, max: 100, label: "Cover to bars: general (mm)" },
  { key: "steel_cover_slab_mm", defaultMm: 38.1, min: 10, max: 100, label: "Cover to bars: slab (mm)", hint: "Empty: the general cover, or the cover the drawing prints for slabs" },
  { key: "steel_cover_beam_mm", defaultMm: 38.1, min: 10, max: 100, label: "Cover to bars: beam and lintel (mm)", hint: "Empty: the general cover, or the cover the drawing prints for beams" },
  { key: "steel_cover_column_mm", defaultMm: 38.1, min: 10, max: 100, label: "Cover to bars: column (mm)", hint: "Empty: the general cover, or the cover the drawing prints for columns" },
  { key: "steel_cover_footing_mm", defaultMm: 38.1, min: 10, max: 100, label: "Cover to bars: footing (mm)", hint: "Empty: the general cover, or the cover the drawing prints for footings" },
  { key: "steel_cover_wall_mm", defaultMm: 38.1, min: 10, max: 100, label: "Cover to bars: RCC wall (mm)", hint: "Empty: the general cover, or the cover the drawing prints for walls" },
  { key: "fill_layer_mm", defaultMm: 152.4, min: 50, max: 600, label: "Compacted fill layer (mm)" },
  { key: "earth_swell_pct", defaultMm: 0, min: 0, max: 50, unit: "pct", label: "Swell of dug earth (percent)", hint: "Standard 0 percent: dug earth is counted as the bank volume" },
  { key: "fill_compaction_pct", defaultMm: 0, min: 0, max: 40, unit: "pct", label: "Extra loose earth for compacting the filling (percent)", hint: "Standard 0 percent: the filling needs its own volume only" },
  { key: "fill_from_excavation", defaultMm: 0, min: 0, max: 1, flag: true, label: "Use the surplus of the dig for the filling under floors" },
  { key: "floor_works_from_spaces", defaultMm: 0, min: 0, max: 1, flag: true, label: "Bed and termite treatment under the floor from the model's rooms" },
  { key: "wall_foundation_works", defaultMm: 0, min: 0, max: 1, flag: true, label: "Brick steps and termite trench under the model's masonry walls" },
  { key: "wall_membrane", defaultMm: 0, min: 0, max: 1, flag: true, label: "Membrane along the plinth under the model's walls" },
  { key: "wall_finishes_from_walls", defaultMm: 0, min: 0, max: 1, flag: true, label: "Plaster and paint from the model's walls when it has no rooms" },
  { key: "one_total", defaultMm: 0, min: 0, max: 1, flag: true, label: "One total: count a member once across the model and the drawings" },
  { key: "one_total_prefer", defaultMm: 0, min: 0, max: 2, label: "One total: which source is kept when both have the member", hint: "Empty: the source with the narrower range", choices: [{ value: "0", label: "The more exact source" }, { value: "1", label: "The drawing" }, { value: "2", label: "The model" }] },
  { key: "one_total_position_tol_mm", defaultMm: 100, min: 10, max: 1000, label: "One total: how far apart two members may stand and be the same (mm)", hint: "Counted once the drawing is placed on the model" },
  { key: "one_total_trust_pct", defaultMm: 50, min: 0, max: 100, unit: "pct", label: "One total: share of a kind that must find a partner (percent)", hint: "Below it the model is kept and the drawing set aside" },
  { key: "opening_area_from_model", defaultMm: 0, min: 0, max: 1, flag: true, label: "Area of doors and windows from the model" },
  { key: "roof_treatment_from_slabs", defaultMm: 0, min: 0, max: 1, flag: true, label: "Roof treatment from the model's roof slabs" },
  { key: "stair_formwork_soffit_only", defaultMm: 0, min: 0, max: 1, flag: true, label: "Stair formwork: soffit only" },
  { key: "beam_lintel_qs_rate", defaultMm: 0, min: 0, max: 1, flag: true, label: "Beam and lintel: rate as the QS does" },
  { key: "formwork_shared_walls", defaultMm: 1, min: 0, max: 1, flag: true, label: "Take off column faces that an RCC wall covers" },
  { key: "formwork_shared_beams", defaultMm: 1, min: 0, max: 1, flag: true, label: "Take off column faces that a beam covers" },
  { key: "rcc_wall_reveals", defaultMm: 0, min: 0, max: 1, flag: true, label: "Add the reveals of openings in RCC walls to the formwork" },
  { key: "ring_hook_dia", defaultMm: 20, min: 0, max: 40, unit: "dia" },
  { key: "bar_lap_dia", defaultMm: 40, min: 0, max: 80, unit: "dia" },
  { key: "bar_anchor_dia", defaultMm: 0, min: 0, max: 80, unit: "dia" },
  { key: "steel_wastage_pct", defaultMm: 5, min: 0, max: 15, unit: "pct" },
  { key: "steel_estimate_from_volume", defaultMm: 1, min: 0, max: 1, flag: true, label: "Estimate the steel of members whose drawing prints no bars", hint: "Empty: yes. The estimate is shown apart from the printed bars, with a range" },
  { key: "slab_steel_kg_per_m2", defaultMm: 17.2223, min: 0, max: 200, unit: "kgm2", label: "Slab steel by rule (kg per square metre)", hint: "Empty: 17.2223, the 1.6 kg per sq ft of the QS workbook. 0 uses the usual kg per m3 instead" },
  { key: "beam_depth_includes_slab", defaultMm: 1, min: 0, max: 1, flag: true },
  { key: "tie_band_replaces_lintel", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "dpc_thickness_mm", defaultMm: 38.1, min: 0, max: 300 },
  { key: "dpc_door_deduction", defaultMm: 1, min: 0, max: 1, flag: true },
  { key: "stair_formwork_soffit_only", defaultMm: 0, min: 0, max: 1, flag: true },
  { key: "beam_lintel_qs_rate", defaultMm: 0, min: 0, max: 1, flag: true },
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

export interface ParamSourceView {
  source: "typed" | "drawing" | "qs" | "default";
  value: number | null;
  text: string | null;
  pages: number[];
}

export interface PrintedNotes {
  drawing?: Partial<Record<DerivedParamName, number>>;
  qs?: Partial<Record<DerivedParamName, number>>;
  notes?: Record<string, { text?: string | null; pages?: number[]; count?: number }>;
}

export function paramSourceView(def: DerivedFieldDef, typed: string | undefined, from: PrintedNotes): ParamSourceView {
  if ((typed ?? "").trim() !== "") {
    return { source: "typed", value: null, text: null, pages: [] };
  }
  const printed = from.drawing?.[def.key];
  if (typeof printed === "number") {
    const note = from.notes?.[def.key];
    return { source: "drawing", value: printed, text: note?.text ?? null, pages: note?.pages ?? [] };
  }
  const answered = from.qs?.[def.key];
  if (typeof answered === "number") {
    return { source: "qs", value: answered, text: null, pages: [] };
  }
  return { source: "default", value: def.defaultMm, text: null, pages: [] };
}

export function mmToInches(mm: number): string {
  const inches = mm / 25.4;
  return Number.isInteger(inches) ? String(inches) : inches.toFixed(1);
}

export function isDerivedSpec(spec: BOQItemSpec | null | undefined): boolean {
  return spec?.kind === "DERIVED";
}

export type DerivedBasis = "user" | "convention" | "drawing" | "qs" | "default" | "claim" | "detected";

export interface DerivedBasisRow {
  key: string;
  value: number;
  basis: DerivedBasis | null;
}

const BASIS_ORDER = ["working_space_mm", "pcc_projection_mm", "pcc_thickness_mm", "ballast_clearance_mm", "ballast_thickness_mm", "shoring", "footing_formwork", "slab_edge_formwork", 
  "formwork_shared_faces", "tank_base_formwork", "steel_cover_mm", "steel_cover_slab_mm", "steel_cover_beam_mm", "steel_cover_column_mm", "steel_cover_footing_mm", "steel_cover_wall_mm",
   "fill_layer_mm", "earth_swell_pct", "fill_compaction_pct", "fill_from_excavation", "floor_works_from_spaces", "wall_foundation_works", "wall_membrane", "wall_finishes_from_walls", "stair_formwork_soffit_only", "beam_lintel_qs_rate", "formwork_shared_walls", "formwork_shared_beams", "rcc_wall_reveals", "ring_hook_dia", "bar_lap_dia", "bar_anchor_dia", "steel_wastage_pct", "steel_estimate_from_volume", "slab_steel_kg_per_m2", "beam_depth_includes_slab", "tie_band_replaces_lintel", "dpc_thickness_mm", "dpc_door_deduction", "ngl"];
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
    rows.push({ key, value, basis: b === "user" || b === "convention" || b === "drawing" || b === "qs" || b === "default" || b === "claim" ? b : null });
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
  return spec?.kind === "DERIVED" && (spec?.recipe === "PDF_MEMBER_STEEL" || spec?.recipe === "PDF_LINTEL_STEEL" || spec?.recipe === "PDF_MEMBER_STEEL_ESTIMATE");
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
  estimate: SteelEstimateView | null;
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
    estimate: steelEstimateView(st),
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
  shared: { face: string; by: string; m2: string }[];
  fromModel: boolean;
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
    faces: raw.faces.filter((f) => !String(f.name).startsWith("shared ")).map((f) => ({ name: String(f.name), m2: String(f.m2) })),
    shared: Array.isArray(raw.shared_faces) ? raw.shared_faces.map((f) => ({ face: String(f.face), by: String(f.by), m2: String(f.m2) })) : [],
    fromModel: Boolean(raw.model_element),
  };
}

export interface FormworkStatsView {
  ran: boolean;
  reason: string | null;
  areaM2: string;
  rows: number;
  categories: { category: string; marks: number; m2: string; grossM2: string | null }[];
  footingsLeftOut: number;
  tanksLeftOut: number;
  assumed: string[];
  contactNotDeducted: boolean;
  takenOffM2: string | null;
  comparison: { grossM2: string; slabSoffitOnlyM2: string; beamPerRftM2: string; beamNetM2: string } | null;
  beamsMatched: number;
  beamsUnmatched: number;
  removedBy: { kind: string; m2: string }[];
  model: { members: number; notBox: number; columnsWithRemoval: number; beamsAdjusted: number; skipped: { reason: string; count: number }[] } | null;
  leftAlone: { reason: string; count: number }[];
}

export function takenOff(gross: string | null | undefined, net: string | null | undefined): string | null {
  const g = Number(gross);
  const n = Number(net);
  if (gross == null || net == null || !Number.isFinite(g) || !Number.isFinite(n)) return null;
  const d = Math.round((g - n) * 1e6) / 1e6;
  return d > 0 ? d.toFixed(6) : null;
}

function addMap(into: Map<string, number>, from: Record<string, string> | undefined) {
  for (const [k, v] of Object.entries(from ?? {})) {
    const n = Number(v);
    if (Number.isFinite(n) && n > 0) into.set(k, (into.get(k) ?? 0) + n);
  }
}

export function removedByKind(fw: DerivedStats["formwork"] | undefined): { kind: string; m2: string }[] {
  const sum = new Map<string, number>();
  addMap(sum, fw?.shared_faces?.removed_by);
  addMap(sum, fw?.model?.shared?.removed_by);
  return [...sum.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([kind, m2]) => ({ kind, m2: m2.toFixed(6) }));
}

export function formworkStatsView(stats: DerivedStats | null | undefined): FormworkStatsView | null {
  const fw = stats?.formwork;
  if (!fw || !fw.enabled || fw.reason === "NO_MEMBERS") {
     return null;
  }
  const categories = Object.entries(fw.by_category ?? {}).map(([category, v]) => ({
    category,
    marks: Number(v.marks),
    m2: String(v.m2),
    grossM2: v.gross_m2 != null ? String(v.gross_m2) : null,
  }));
  const cmp = fw.comparison;
  return {
    ran: Boolean(fw.ran),
    reason: fw.reason ?? null,
    areaM2: String(fw.area_m2 ?? "0"),
    rows: Number(fw.rows ?? 0),
    categories,
    footingsLeftOut: Number(fw.skipped?.FOOTING_NOT_SHUTTERED_DEFAULT ?? 0),
    tanksLeftOut: Number(fw.skipped?.TANK_NO_DETAIL ?? 0),
    assumed: Array.isArray(fw.assumed) ? fw.assumed : [],
    contactNotDeducted: Boolean(fw.contact_not_deducted),
    takenOffM2: takenOff(cmp?.gross_m2, fw.area_m2),
    comparison: cmp
      ? { grossM2: String(cmp.gross_m2), slabSoffitOnlyM2: String(cmp.slab_soffit_only_m2), beamPerRftM2: String(cmp.beam_per_rft_m2), beamNetM2: String(cmp.beam_net_m2) }
      : null,
    beamsMatched: Number(fw.beam_slab?.beams_matched ?? 0),
        beamsUnmatched: Number(fw.beam_slab?.beams_unmatched ?? 0),
    removedBy: removedByKind(fw),
    model: fw.model && Number(fw.model.members ?? 0) > 0
      ? {
          members: Number(fw.model.members ?? 0),
          notBox: Number(fw.model.not_box ?? 0),
          columnsWithRemoval: Number(fw.model.shared?.columns_with_removal ?? 0),
          beamsAdjusted: Number(fw.model.shared?.beams_adjusted ?? 0),
          skipped: Object.entries(fw.model.skipped ?? {}).map(([reason, count]) => ({ reason, count: Number(count) })),
        }
      : null,
    leftAlone: [
      ["WALL_NOT_PLACED", Number(fw.shared_faces?.unplaced_walls ?? 0)],
      ["WALL_NOT_SQUARE", Number(fw.shared_faces?.walls_not_square ?? 0)],
      ["BEAM_NOT_MATCHED", Number(fw.shared_faces?.unmatched_beams ?? 0)],
    ].filter(([, n]) => Number(n) > 0).map(([reason, count]) => ({ reason: String(reason), count: Number(count) })),
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

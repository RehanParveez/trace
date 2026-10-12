import type { DimsBasis, MeasureKind, MeasurementParams, ModeOption, OpeningRole, ReconMode, TakeoffMeasurement } from "../types/takeoff.types";
import { mmToString, parseLengthMm } from "./lengthInput";

export const RESERVED_WORK_ITEMS = ["STL-REBAR", "STL-STRUCT", "STL-PILE"];

export const DIMENSION_FIELDS = ["height_mm", "thickness_mm", "width_mm", "depth_mm", "length_mm"] as const;
export type DimensionField = (typeof DIMENSION_FIELDS)[number];

export const DIMENSION_LABEL: Record<DimensionField, string> = {
  height_mm: "Height",
  thickness_mm: "Thickness",
  width_mm: "Width",
  depth_mm: "Depth",
  length_mm: "Length",
};

export interface OpeningRow { role: OpeningRole; width: string; height: string; nos: string; label: string }
export interface AdjustmentRow { op: "LESS" | "ADD"; value: string; label: string }

export interface MeasureFormValue {
  quantity_mode: string;
  work_item_code: string;
  label: string;
  tag: string;
  material_grade: string;
  recon_mode: ReconMode;
  dims: Record<DimensionField, string>;
  dims_basis: DimsBasis;
  repeat: string;
  openings: OpeningRow[];
  adjustments: AdjustmentRow[];
}

export function emptyForm(kind: MeasureKind): MeasureFormValue {
  return {
    quantity_mode: "DIRECT",
    work_item_code: "",
    label: "",
    tag: "",
    material_grade: "",
    recon_mode: "AUTO",
    dims: { height_mm: "", thickness_mm: "", width_mm: "", depth_mm: "", length_mm: "" },
    dims_basis: "SPECIFIED",
    repeat: "1",
    openings: [],
    adjustments: [],
    ...(kind === "COUNT" ? {} : {}),
  };
}

export function modesFor(modes: ModeOption[] | undefined, kind: MeasureKind): ModeOption[] {
  return (modes ?? []).filter((m) => m.kind === kind);
}

export function modeOption(modes: ModeOption[] | undefined, kind: MeasureKind, mode: string): ModeOption | undefined {
  return (modes ?? []).find((m) => m.kind === kind && m.quantity_mode === mode);
}

export function supportsOpenings(mode: string): boolean {
  return mode === "LENGTH_X_HEIGHT" || mode === "LENGTH_X_HEIGHT_X_THICKNESS";
}

export interface ParamsResult { params: MeasurementParams; errors: string[]; missing: DimensionField[] }

export function formToParams(form: MeasureFormValue, required: string[]): ParamsResult {
  const errors: string[] = [];
  const missing: DimensionField[] = [];
  const params: MeasurementParams = {};
  for (const f of DIMENSION_FIELDS) {
    const raw = form.dims[f].trim();
    const needed = required.includes(f);
    if (!raw) {
      if (needed) missing.push(f);
      continue;
    }
    if (!needed) continue;
    const mm = parseLengthMm(raw);
    if (mm === null || mm <= 0) errors.push(`${DIMENSION_LABEL[f]} is not a length I can read (try 3000, 3m or 10ft 6in).`);
    else params[f] = mmToString(mm);
  }
  const repeat = Number(form.repeat || "1");
  if (!Number.isInteger(repeat) || repeat < 1 || repeat > 1000) errors.push("Repeat must be a whole number from 1 to 1000.");
  else params.repeat = repeat;
  params.dims_basis = form.dims_basis;
  if (supportsOpenings(form.quantity_mode)) {
    const openings: NonNullable<MeasurementParams["openings"]> = [];
    form.openings.forEach((o, i) => {
      const w = parseLengthMm(o.width);
      const h = parseLengthMm(o.height);
      const n = Number(o.nos || "1");
      if (w === null || h === null || w <= 0 || h <= 0) errors.push(`Opening ${i + 1}: width and height must be lengths.`);
      else if (!Number.isInteger(n) || n < 1) errors.push(`Opening ${i + 1}: number must be a whole number.`);
      else openings.push({ role: o.role, width_mm: mmToString(w), height_mm: mmToString(h), nos: n, label: o.label || null });
    });
    if (openings.length) params.openings = openings;
  }
  const adjustments: NonNullable<MeasurementParams["adjustments"]> = [];
  form.adjustments.forEach((a, i) => {
    const v = Number(a.value);
    if (!Number.isFinite(v) || v <= 0) errors.push(`Adjustment ${i + 1}: enter a number greater than zero.`);
    else adjustments.push({ op: a.op, value: String(v), label: a.label || null });
  });
  if (adjustments.length) params.adjustments = adjustments;
  return { params, errors, missing };
}

const str = (v: unknown): string => (v === null || v === undefined ? "" : String(v));

export function measurementToForm(m: TakeoffMeasurement): MeasureFormValue {
  const p = m.params ?? {};
  return {
    quantity_mode: m.quantity_mode,
    work_item_code: m.work_item_code ?? "",
    label: m.label ?? "",
    tag: m.tag ?? "",
    material_grade: m.material_grade ?? "",
    recon_mode: m.recon_mode,
    dims: {
      height_mm: str(p.height_mm), thickness_mm: str(p.thickness_mm), width_mm: str(p.width_mm), depth_mm: str(p.depth_mm), length_mm: str(p.length_mm),
    },
    dims_basis: p.dims_basis ?? "DRAWN",
    repeat: str(p.repeat ?? 1),
    openings: (p.openings ?? []).map((o) => ({ role: o.role, width: str(o.width_mm), height: str(o.height_mm), nos: str(o.nos), label: str(o.label) })),
    adjustments: (p.adjustments ?? []).map((a) => ({ op: a.op, value: str(a.value), label: str(a.label) })),
  };
}

export const RECON_HELP: Record<ReconMode, string> = {
  AUTO: "Counted unless the model already measures this work item; then it only verifies the model.",
  ADD: "Counted on top of the model quantity (use for parts the model does not have).",
  REPLACE_MODEL: "Replaces the model quantity for this work item.",
  VERIFY_ONLY: "Never counted; only compared with the model.",
};

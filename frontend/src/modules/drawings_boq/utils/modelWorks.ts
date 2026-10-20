import type { DerivedStats, RangeStampStats } from "../types/drawings-boq.types";

export interface WallWorksView {
  ran: boolean;
  reason: string | null;
  walls: number;
  lengthM: string;
  brickStepsM3: string;
  termiteM2: string;
  membraneM2: string;
  classes: { cls: "THIN" | "THICK"; walls: number; lengthM: number }[];
  belowDpc: number;
  skipped: { item: string; why: string }[];
  stepOffsetMm: number | null;
  stepHeights: { cls: "THIN" | "THICK"; heightsMm: number[] }[];
  pccProjectionMm: number | null;
  levelAssumed: boolean;
}

export function wallWorksView(stats: DerivedStats | null | undefined): WallWorksView | null {
  const w = stats?.wall_foundation;
  if (!w || !w.enabled) return null;
  return {
    ran: Boolean(w.ran),
    reason: w.reason ?? null,
    walls: Number(w.walls ?? 0),
    lengthM: String(w.length_m ?? "0"),
    brickStepsM3: String(w.brick_steps_m3 ?? "0"),
    termiteM2: String(w.termite_trench_m2 ?? "0"),
    membraneM2: String(w.membrane_m2 ?? "0"),
    classes: (Object.entries(w.classes ?? {}) as ["THIN" | "THICK", { walls: number; length_m: number }][]).map(([cls, v]) => ({ cls, walls: v.walls, lengthM: v.length_m })),
    belowDpc: Number(w.left_alone_going_below_dpc ?? 0),
    skipped: Object.entries(w.skipped ?? {}).map(([item, why]) => ({ item, why: String(why) })),
    stepOffsetMm: w.step_offset_mm ?? null,
    stepHeights: (Object.entries(w.step_heights_mm ?? {}) as ["THIN" | "THICK", number[]][]).map(([cls, heightsMm]) => ({ cls, heightsMm })),
    pccProjectionMm: w.pcc_projection_mm ?? null,
    levelAssumed: w.level?.source === "default",
  };
}

export interface WallFinishView {
  ran: boolean;
  reason: string | null;
  walls: number;
  rows: number;
  plasterInsideM2: string;
  plasterOutsideM2: string;
  openingsDeductedM2: string;
  openings: number;
  sidesFromGeometry: number;
  skipped: string[];
  levelAssumed: boolean;
}

export function wallFinishView(stats: DerivedStats | null | undefined): WallFinishView | null {
  const f = stats?.wall_finishes;
  if (!f || !f.enabled) return null;
  return {
    ran: Boolean(f.ran),
    reason: f.reason ?? null,
    walls: Number(f.walls ?? 0),
    rows: Number(f.rows ?? 0),
    plasterInsideM2: String(f.plaster_inside_m2 ?? "0"),
    plasterOutsideM2: String(f.plaster_outside_m2 ?? "0"),
    openingsDeductedM2: String(f.openings_deducted_m2 ?? "0"),
    openings: Number(f.openings ?? 0),
    sidesFromGeometry: Number(f.sides_from_geometry ?? 0),
    skipped: Object.keys(f.skipped ?? {}),
    levelAssumed: f.dpc_level?.source === "default",
  };
}

export interface RangeStampView {
  rows: number;
  stamped: number;
  unbounded: number;
  grades: { grade: string; count: number }[];
}

const GRADE_ORDER = ["PRINTED", "VERIFIED", "CONFIRMED", "MODEL", "PICTURE", "MEASURED", "ASSUMED", "MISSING", "NOT_READ"];

export function rangeStampView(ranges: RangeStampStats | null | undefined): RangeStampView | null {
  if (!ranges || typeof ranges.rows !== "number") return null;
  const grades = Object.entries(ranges.grades ?? {})
    .map(([grade, count]) => ({ grade, count: Number(count) }))
    .sort((a, b) => {
      const ia = GRADE_ORDER.indexOf(a.grade);
      const ib = GRADE_ORDER.indexOf(b.grade);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
  return { rows: ranges.rows, stamped: Number(ranges.stamped ?? 0), unbounded: Number(ranges.unbounded ?? 0), grades };
}

export function reasonWords(reason: string | null | undefined): string {
  switch (reason) {
    case "SWITCHED_OFF":
      return "The setting is off.";
    case "NO_PROFILE":
      return "The company has no measurement profile for derived works.";
    case "NO_WALLS":
      return "The model has no wall to work from.";
    case "NO_DPC_LEVEL":
      return "The model has no door to give the floor level, so the damp-proof course level is unknown. Type the floor level in the datums.";
    case "NO_WALL_ON_DPC":
      return "No masonry wall stands across the damp-proof course level.";
    case "ALL_ITEMS_ALREADY_MEASURED":
      return "Every item was already measured from the model or a drawing.";
    case "HAS_ROOMS":
      return "The model has rooms, so the finishes come from the rooms.";
    case "NOTHING_TO_MEASURE":
      return "The walls gave no quantity.";
    default:
      return reason ?? "";
  }
}

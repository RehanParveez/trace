import type { AcceptBody, AreaGeometry, CandidateCategory, CountGeometry, LengthGeometry, Pt, TakeoffCandidate } from "../types/takeoff.types";
import { steelForAccept } from "./steel";
import type { SteelSet } from "./steel";

export const CATEGORY_ORDER: CandidateCategory[] = ["WALL", "COLUMN", "FOOTING", "BEAM", "SLAB", "LINTEL", "STAIR", "DOOR", "WINDOW", "ROOM", "SITE"];

export const CATEGORY_TEXT: Record<CandidateCategory, { one: string; many: string }> = {
  WALL: { one: "Wall", many: "Walls" },
  COLUMN: { one: "Column", many: "Columns" },
  FOOTING: { one: "Footing", many: "Footings" },
  BEAM: { one: "Beam", many: "Beams" },
  SLAB: { one: "Slab", many: "Slabs" },
  LINTEL: { one: "Lintel", many: "Lintels" },
  STAIR: { one: "Stair", many: "Stairs" },
  DOOR: { one: "Door", many: "Doors" },
  WINDOW: { one: "Window", many: "Windows" },
  ROOM: { one: "Room", many: "Rooms" },
  SITE: { one: "Site item", many: "Site items" },
};

import { isNeckColumn, isTankWall, pickGivesDepth } from "./choices";

export type HeightField =
  | "wall_height_mm"
  | "column_height_mm"
  | "neck_height_mm"
  | "tank_wall_height_mm"
  | "footing_depth_mm"
  | "slab_thickness_mm"
  | "beam_depth_mm"
  | "plinth_beam_depth_mm"
  | "tie_band_depth_mm"
  | "excavation_depth_mm"
  | "fill_depth_mm"
  | "trench_depth_mm"
  | "pcc_thickness_mm"
  | "pcc_strip_width_mm"
  | "pcc_strip_width_thin_mm"
  | "brick_step_1_height_mm"
  | "brick_step_2_height_mm"
  | "brick_step_3_height_mm"
  | "brick_step_4_height_mm"
  | "brick_step_offset_mm"
  | "membrane_width_mm"
  | "door_frame_width_mm"
  | "door_frame_width_thin_mm"
  | "tile_height_mm"
  | "stair_waist_mm"
  | "site_length_mm"
  | "site_width_mm"
  | "site_height_mm"
  | "site_thickness_mm";

const HEIGHT_ORDER: HeightField[] = [
  "wall_height_mm",
  "tank_wall_height_mm",
  "column_height_mm",
  "neck_height_mm",
  "footing_depth_mm",
  "slab_thickness_mm",
  "beam_depth_mm",
  "plinth_beam_depth_mm",
  "tie_band_depth_mm",
  "excavation_depth_mm",
  "fill_depth_mm",
  "trench_depth_mm",
  "pcc_thickness_mm",
  "pcc_strip_width_mm",
  "pcc_strip_width_thin_mm",
  "brick_step_1_height_mm",
  "brick_step_2_height_mm",
  "brick_step_3_height_mm",
  "brick_step_4_height_mm",
  "brick_step_offset_mm",
  "membrane_width_mm",
  "door_frame_width_mm",
  "door_frame_width_thin_mm",
  "tile_height_mm",
  "stair_waist_mm",
  "site_length_mm",
  "site_width_mm",
  "site_height_mm",
  "site_thickness_mm",
];

export type Heights = Record<HeightField, string>;
export const NO_HEIGHTS: Heights = {
  wall_height_mm: "",
  tank_wall_height_mm: "",
  column_height_mm: "",
  neck_height_mm: "",
  footing_depth_mm: "",
  slab_thickness_mm: "",
  beam_depth_mm: "",
  plinth_beam_depth_mm: "",
  tie_band_depth_mm: "",
  excavation_depth_mm: "",
  fill_depth_mm: "",
  trench_depth_mm: "",
  pcc_thickness_mm: "",
  pcc_strip_width_mm: "",
  pcc_strip_width_thin_mm: "",
  brick_step_1_height_mm: "",
  brick_step_2_height_mm: "",
  brick_step_3_height_mm: "",
  brick_step_4_height_mm: "",
  brick_step_offset_mm: "",
  membrane_width_mm: "",
  door_frame_width_mm: "",
  door_frame_width_thin_mm: "",
  tile_height_mm: "",
  stair_waist_mm: "",
  site_length_mm: "",
  site_width_mm: "",
  site_height_mm: "",
  site_thickness_mm: "",
};

export const HEIGHT_LABEL: Record<HeightField, string> = {
  wall_height_mm: "Wall height (mm)",
  tank_wall_height_mm: "Water tank wall height (mm)",
  column_height_mm: "Column height (mm)",
  neck_height_mm: "Neck column height, top of the footing to the floor (mm)",
  footing_depth_mm: "Footing depth (mm)",
  slab_thickness_mm: "Slab thickness (mm)",
  beam_depth_mm: "Roof beam depth (mm)",
  plinth_beam_depth_mm: "Plinth beam depth (mm)",
  tie_band_depth_mm: "Tie band depth (mm)",
  excavation_depth_mm: "Excavation depth over the basement (mm)",
  fill_depth_mm: "Depth of the earth filling under the floor (mm)",
  trench_depth_mm: "Trench depth below the dug floor (mm)",
  pcc_thickness_mm: "Concrete bed thickness (mm)",
  pcc_strip_width_mm: "Strip width under walls of 6 in and thicker (mm)",
  pcc_strip_width_thin_mm: "Strip width under thin walls (mm)",
  brick_step_1_height_mm: "Brick foundation, height of step 1 from the bottom (mm)",
  brick_step_2_height_mm: "Brick foundation, height of step 2 (mm)",
  brick_step_3_height_mm: "Brick foundation, height of step 3 (mm)",
  brick_step_4_height_mm: "Brick foundation, height of step 4 (mm)",
  brick_step_offset_mm: "Brick foundation, each step narrower than the one below, both sides together (mm)",
  membrane_width_mm: "Damp-proof membrane width (mm)",
  door_frame_width_mm: "Door frame width in walls of 6 in and thicker (mm)",
  door_frame_width_thin_mm: "Door frame width in thin walls (mm)",
  tile_height_mm: "Kitchen wall tile height (mm)",
  stair_waist_mm: "Stair waist slab thickness under the steps (mm)",
  site_length_mm: "Site item: outside length of the tank, length of the ramp, or width of the gate (mm)",
  site_width_mm: "Site item: outside width of the tank or width of the ramp (mm)",
  site_height_mm: "Site item: outside height of the tank, or height of the boundary wall or gate (mm)",
  site_thickness_mm: "Site item: thickness of the tank walls and slabs, of the boundary wall, or of the ramp slab (mm)",
};

export type FoundationItem =
  | "EXCAVATION_AREA"
  | "TRENCH"
  | "PCC_STRIP"
  | "TERMITE_STRIP"
  | "TERMITE_UNDER_FLOOR"
  | "PCC_PAD"
  | "BRICK_STEP"
  | "MEMBRANE"
  | "KACHA_FLOOR"
  | "CEILING_PLASTER"
  | "PLASTER_INSIDE"
  | "PLASTER_OUTSIDE"
  | "DOOR_FRAME"
  | "DOOR_AREA"
  | "WINDOW_AREA"
  | "EARTH_FILL"
  | "ROOF_TREATMENT"
  | "FLOOR_FINISH"
  | "CEILING_PAINT"
  | "SKIRTING"
  | "DADO"
  | "PAINT_INSIDE"
  | "PAINT_OUTSIDE"
  | "FLOOR_PCC"
  | "FLOOR_BALLAST"
  | "FLOOR_SAND_FILL"
  | "MEMBRANE_COAT"
  | "MEMBRANE_POLYTHENE"
  | "FLOOR_WET"
  | "WALL_TILE"
  | "WET_WATERPROOF";

const FOUNDATION_ITEMS: FoundationItem[] = [
  "EXCAVATION_AREA",
  "TRENCH",
  "PCC_STRIP",
  "TERMITE_STRIP",
  "TERMITE_UNDER_FLOOR",
  "PCC_PAD",
  "BRICK_STEP",
  "MEMBRANE",
  "KACHA_FLOOR",
  "CEILING_PLASTER",
  "PLASTER_INSIDE",
  "PLASTER_OUTSIDE",
  "DOOR_FRAME",
  "DOOR_AREA",
  "WINDOW_AREA",
  "EARTH_FILL",
  "ROOF_TREATMENT",
  "FLOOR_FINISH",
  "CEILING_PAINT",
  "SKIRTING",
  "DADO",
  "PAINT_INSIDE",
  "PAINT_OUTSIDE",
  "FLOOR_PCC",
  "FLOOR_BALLAST",
  "FLOOR_SAND_FILL",
  "MEMBRANE_COAT",
  "MEMBRANE_POLYTHENE",
  "FLOOR_WET",
  "WALL_TILE",
  "WET_WATERPROOF",
];

export type SiteKind = "OHWT" | "UGWT" | "SEPTIC" | "BOUNDARY_WALL" | "GATE" | "PORCH_RAMP";

const SITE_KINDS: SiteKind[] = ["OHWT", "UGWT", "SEPTIC", "BOUNDARY_WALL", "GATE", "PORCH_RAMP"];

const SITE_TOKEN_FIELD: Record<string, HeightField> = {
  length_mm: "site_length_mm",
  width_mm: "site_width_mm",
  height_mm: "site_height_mm",
  thickness_mm: "site_thickness_mm",
};

export function siteKind(c: Pick<TakeoffCandidate, "category" | "facts">): SiteKind | null {
  if (c.category !== "SITE") return null;
  const kind = (c.facts as Record<string, unknown> | null)?.site_kind;
  return SITE_KINDS.find((x) => x === kind) ?? null;
}

function siteFields(c: Pick<TakeoffCandidate, "category" | "missing" | "facts">): HeightField[] {
  if (c.category !== "SITE") return [];
  return c.missing.map((m) => SITE_TOKEN_FIELD[m]).filter((f): f is HeightField => f !== undefined);
}

const BRICK_STEP_FIELDS: HeightField[] = ["brick_step_1_height_mm", "brick_step_2_height_mm", "brick_step_3_height_mm", "brick_step_4_height_mm"];

export function foundationItem(c: Pick<TakeoffCandidate, "category" | "facts">): FoundationItem | null {
  if (c.category !== "WALL") return null;
  const item = (c.facts as Record<string, unknown> | null)?.foundation_item;
  return FOUNDATION_ITEMS.find((x) => x === item) ?? null;
}

export function slabThicknessDisputed(c: Pick<TakeoffCandidate, "category" | "notes">): boolean {
  return c.category === "SLAB" && (c.notes ?? []).some((n) => n.code === "SLAB_THICKNESS_DISAGREES");
}

export interface SlabThicknessChoice { mm: number; sources: string[]; pages: number[] }

const SLAB_SOURCE_TEXT: Record<string, string> = { PLAN_NOTE: "plan note", OTHER_SHEET: "other sheet", SECTIONS: "building sections", SECTION_LABEL: "section label" };

export function slabThicknessChoices(c: Pick<TakeoffCandidate, "category" | "facts">): SlabThicknessChoice[] {
  if (c.category !== "SLAB") return [];
  const raw = (c.facts as Record<string, unknown> | null)?.thickness_options;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((o): o is Record<string, unknown> => typeof o === "object" && o !== null && typeof (o as Record<string, unknown>).mm === "number")
    .map((o) => ({ mm: o.mm as number, sources: Array.isArray(o.sources) ? (o.sources as string[]) : [], pages: Array.isArray(o.pages) ? (o.pages as number[]) : [] }));
}

export function isWallBeam(c: Pick<TakeoffCandidate, "category" | "facts">): boolean {
  return c.category === "BEAM" && (c.facts as Record<string, unknown> | null)?.derived_from === "WALLS";
}

export function isMeasuredBeam(c: Pick<TakeoffCandidate, "category" | "facts">): boolean {
  return isWallBeam(c) || (c.category === "BEAM" && (c.facts as Record<string, unknown> | null)?.from_strips === true);
}

function foundationFields(c: Pick<TakeoffCandidate, "category" | "missing" | "facts">): HeightField[] {
  const item = foundationItem(c);
  if (item === null) return [];
  const out: HeightField[] = [];
  if (c.missing.includes("strip_width_mm")) {
    out.push((c.facts as Record<string, unknown> | null)?.strip_class === "THIN" ? "pcc_strip_width_thin_mm" : "pcc_strip_width_mm");
  }
  if (c.missing.includes("depth_mm")) {
    out.push(item === "EXCAVATION_AREA" ? "excavation_depth_mm" : item === "TRENCH" ? "trench_depth_mm" : item === "EARTH_FILL" ? "fill_depth_mm" : "pcc_thickness_mm");
  }
  if (c.missing.includes("step_height_mm")) {
    const step = Number((c.facts as Record<string, unknown> | null)?.step_no);
    if (BRICK_STEP_FIELDS[step - 1]) out.push(BRICK_STEP_FIELDS[step - 1]);
  }
  if (c.missing.includes("step_offset_mm")) out.push("brick_step_offset_mm");
  if (c.missing.includes("membrane_width_mm")) out.push("membrane_width_mm");
  if (c.missing.includes("frame_width_mm")) {
    out.push((c.facts as Record<string, unknown> | null)?.frame_class === "THIN" ? "door_frame_width_thin_mm" : "door_frame_width_mm");
  }
  if (c.missing.includes("tile_height_mm")) out.push("tile_height_mm");
  return out;
}

export function heightFieldsFor(c: Pick<TakeoffCandidate, "category" | "missing"> & Partial<Pick<TakeoffCandidate, "notes" | "facts">>): HeightField[] {
  if (c.missing.includes("size")) return [];
  if (c.category === "SITE") return siteFields({ category: c.category, missing: c.missing, facts: c.facts ?? {} });
  const found = foundationFields({ category: c.category, missing: c.missing, facts: c.facts ?? {} });
  if (found.length) return found;
  const one = heightFieldFor(c);
  return one === null ? [] : [one];
}

export function heightFieldFor(c: Pick<TakeoffCandidate, "category" | "missing"> & Partial<Pick<TakeoffCandidate, "notes" | "facts">>): HeightField | null {
  if (c.missing.includes("size")) return null;
  if (c.category === "SITE") return siteFields({ category: c.category, missing: c.missing, facts: c.facts ?? {} })[0] ?? null;
  const found = foundationFields({ category: c.category, missing: c.missing, facts: c.facts ?? {} });
  if (found.length) return found[0];
  if (isTankWall(c) && c.missing.includes("height_mm")) return "tank_wall_height_mm";
  if (c.category === "WALL" && c.missing.includes("height_mm")) return "wall_height_mm";
  if (isNeckColumn(c) && c.missing.includes("height_mm")) return "neck_height_mm";
  if (c.category === "COLUMN" && c.missing.includes("height_mm")) return "column_height_mm";
  if (c.category === "FOOTING" && c.missing.includes("depth_mm")) return "footing_depth_mm";
  if (c.category === "SLAB" && c.missing.includes("thickness_mm")) return "slab_thickness_mm";
  if (c.category === "SLAB" && slabThicknessDisputed({ category: c.category, notes: c.notes ?? [] })) return "slab_thickness_mm";
  if (c.category === "BEAM" && c.missing.includes("depth_mm")) {
    const role = (c.facts as Record<string, unknown> | undefined)?.beam_role;
    return role === "PLINTH" ? "plinth_beam_depth_mm" : role === "BAND" ? "tie_band_depth_mm" : "beam_depth_mm";
  }
  if (c.category === "STAIR" && c.missing.includes("waist_mm")) return "stair_waist_mm";
  return null;
}

export function notMeasurable(c: Pick<TakeoffCandidate, "category" | "missing" | "status"> & Partial<Pick<TakeoffCandidate, "facts">>): boolean {
  return (c.category === "BEAM" && !isMeasuredBeam({ category: c.category, facts: c.facts ?? {} })) || c.missing.includes("size") || c.status === "INVALID";
}

export type Level = "high" | "medium" | "low";

export function confidenceLevel(confidence: string | number): Level {
  const n = Number(confidence);
  if (!Number.isFinite(n) || n < 0.65) return "low";
  return n >= 0.85 ? "high" : "medium";
}

export const ITEM_TEXT: Record<FoundationItem, string> = {
  EXCAVATION_AREA: "Excavation (whole area)",
  TRENCH: "Trenches under walls",
  PCC_STRIP: "Concrete bed under walls",
  TERMITE_STRIP: "Termite treatment under walls",
  TERMITE_UNDER_FLOOR: "Termite treatment under the floor",
  PCC_PAD: "Concrete bed under footings",
  BRICK_STEP: "Brick steps",
  MEMBRANE: "Damp-proof membrane",
  KACHA_FLOOR: "Bed under the floor",
  CEILING_PLASTER: "Ceiling plaster",
  PLASTER_INSIDE: "Plaster inside the walls",
  PLASTER_OUTSIDE: "Plaster outside the walls",
  DOOR_FRAME: "Door frames",
  DOOR_AREA: "Door area",
  WINDOW_AREA: "Window area",
  EARTH_FILL: "Earth filling under the floor",
  ROOF_TREATMENT: "Roof treatment",
  FLOOR_FINISH: "Floor finish",
  CEILING_PAINT: "Ceiling paint",
  SKIRTING: "Skirting",
  DADO: "Tile dado",
  PAINT_INSIDE: "Paint inside the walls",
  PAINT_OUTSIDE: "Paint outside the walls",
  FLOOR_PCC: "Concrete bed under the floor (specification)",
  FLOOR_BALLAST: "Brick ballast under the floor",
  FLOOR_SAND_FILL: "Sand filling under the floor",
  MEMBRANE_COAT: "Waterproofing coats on the basement walls",
  MEMBRANE_POLYTHENE: "Polythene sheet on the basement walls",
  FLOOR_WET: "Floor tile in baths and toilets",
  WALL_TILE: "Wall tile in kitchens",
  WET_WATERPROOF: "Waterproofing in baths and toilets",
};

export const SITE_TEXT: Record<SiteKind, string> = {
  OHWT: "Over head water tank",
  UGWT: "Underground water tank",
  SEPTIC: "Septic tank",
  BOUNDARY_WALL: "Boundary wall",
  GATE: "Gate",
  PORCH_RAMP: "Porch ramp",
};

export type KindKey = CandidateCategory | FoundationItem | SiteKind;

export function kindKey(c: Pick<TakeoffCandidate, "category" | "facts">): KindKey {
  return siteKind(c) ?? foundationItem(c) ?? c.category;
}

export function groupByKind(list: TakeoffCandidate[]): Array<{ key: KindKey; title: string; items: TakeoffCandidate[] }> {
  const out: Array<{ key: KindKey; title: string; items: TakeoffCandidate[] }> = [];
  const keys: KindKey[] = [...CATEGORY_ORDER, ...FOUNDATION_ITEMS, ...SITE_KINDS];
  for (const key of keys) {
    const items = list.filter((c) => kindKey(c) === key);
    if (!items.length) continue;
    out.push({ key, title: key in CATEGORY_TEXT ? CATEGORY_TEXT[key as CandidateCategory].many : key in SITE_TEXT ? SITE_TEXT[key as SiteKind] : ITEM_TEXT[key as FoundationItem], items });
  }
  return out;
}

export function unknownWorkItem(code: string, codes: string[]): boolean {
  return code.trim() !== "" && codes.length > 0 && !codes.includes(code.trim().toUpperCase());
}

export function groupByCategory(list: TakeoffCandidate[]): Array<{ category: CandidateCategory; items: TakeoffCandidate[] }> {
  const out: Array<{ category: CandidateCategory; items: TakeoffCandidate[] }> = [];
  for (const category of CATEGORY_ORDER) {
    const items = list.filter((c) => c.category === category);
    if (items.length) out.push({ category, items });
  }
  return out;
}

const BEAM_DEPTH_FIELDS: HeightField[] = ["beam_depth_mm", "plinth_beam_depth_mm", "tie_band_depth_mm"];

export function fieldsStillNeeded(c: TakeoffCandidate, picks?: Record<string, string>): HeightField[] {
  const given = c.category === "BEAM" && pickGivesDepth(c, picks);
  return heightFieldsFor(c).filter((f) => !(given && BEAM_DEPTH_FIELDS.includes(f)));
}

export function neededHeights(list: TakeoffCandidate[], picks?: Record<string, string>): HeightField[] {
  const set = new Set<HeightField>();
  for (const c of list) {
    for (const f of fieldsStillNeeded(c, picks)) set.add(f);
  }
  return HEIGHT_ORDER.filter((f) => set.has(f));
}

export function validHeight(text: string): number | null {
  const n = Number(text.trim().replace(/,/g, ""));
  return Number.isFinite(n) && n >= 75 && n <= 20000 ? n : null;
}

export function blockedByHeight(list: TakeoffCandidate[], ids: Set<string>, typed: Heights, picks?: Record<string, string>): TakeoffCandidate[] {
  return list.filter((c) => {
    if (!ids.has(c.id)) return false;
    return fieldsStillNeeded(c, picks).some((f) => validHeight(typed[f]) === null);
  });
}

export function candidatePoints(c: Pick<TakeoffCandidate, "kind" | "geometry">): Pt[] {
  if (c.kind === "AREA") return (c.geometry as AreaGeometry).outer ?? [];
  return ((c.geometry as LengthGeometry | CountGeometry).points ?? []) as Pt[];
}

const STALE_TEXT: Record<string, string> = {
  SCALE_CHANGED: "The scale of this sheet changed after this was read.",
  SHEET_READ_AGAIN: "The sheet was read again after this was found.",
  NEWER_LOGIC: "The reading rules have been improved since this was found.",
};

export function staleText(reasons: string[]): string {
  return reasons.map((r) => STALE_TEXT[r] ?? r).join(" ");
}

function foundationLine(c: TakeoffCandidate, item: FoundationItem): string {
  const line = foundationLineBase(c, item);
  const g = (c.facts as Record<string, unknown>).spec_grade as { grade?: unknown; what?: unknown } | undefined;
  const grade = g && typeof g.grade === "string" && g.grade ? `grade ${g.grade} as printed${typeof g.what === "string" && g.what ? ` (${g.what})` : ""}` : null;
  return [line, grade].filter(Boolean).join(" · ");
}

function roofFallText(f: Record<string, unknown>): string {
  const slope = f.slope as { min_mm?: unknown; max_mm?: unknown; avg_mm?: unknown } | null | undefined;
  const lo = Number(slope?.min_mm);
  const hi = Number(slope?.max_mm);
  const avg = Number(slope?.avg_mm);
  if (!slope || !Number.isFinite(lo) || !Number.isFinite(hi) || !Number.isFinite(avg)) return "fall not read";
  const inch = (v: number) => (v / 25.4).toFixed(1).replace(/\.0$/, "");
  return `fall ${inch(lo)}–${inch(hi)} in printed (average ${avg.toFixed(1)} mm)`;
}

function roofEdgeText(f: Record<string, unknown>): string {
  const edge = Number(f.edge_m);
  return f.edge_m != null && Number.isFinite(edge) && edge > 0 ? `roof edge ${edge.toFixed(2)} m from the printed size` : "roof edge not known";
}

function foundationLineBase(c: TakeoffCandidate, item: FoundationItem): string {
  const f = c.facts as Record<string, unknown>;
  const p = c.params as Record<string, unknown>;
  const num = (v: unknown) => (typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)) ? Number(v) : null);
  const inch = (v: number) => (v / 25.4).toFixed(1).replace(/\.0$/, "");
  const width = num(p.width_mm);
  const depth = num(p.depth_mm);
  const sizes = (suffix: string | null, needed: string) => [width !== null ? `${Math.round(width)} mm wide` : "width needed", suffix === null ? null : depth !== null ? `${Math.round(depth)} mm ${suffix}` : `${needed} needed`];

  if (item === "EXCAVATION_AREA") {
    const dims = Array.isArray(f.outline_dims_mm) ? (f.outline_dims_mm as number[]) : null;
    const area = num(f.area_m2);
    return [area !== null ? `${area.toFixed(2)} m² outline` : null, dims ? `${Math.round(dims[0])}×${Math.round(dims[1])} mm` : null, depth !== null ? `${Math.round(depth)} mm deep` : "depth needed"].filter(Boolean).join(" · ");
  }

  if (item === "TERMITE_UNDER_FLOOR" || item === "KACHA_FLOOR" || item === "CEILING_PLASTER") {
    const area = num(f.area_m2);
    const rooms = num(f.room_count);
    return [area !== null ? `${area.toFixed(2)} m² of ${item === "CEILING_PLASTER" ? "ceiling" : "floor"}` : null, rooms !== null ? `total of ${rooms} room${rooms === 1 ? "" : "s"}` : null].filter(Boolean).join(" · ");
  }

  if (item === "BRICK_STEP") {
    const len = num(f.length_m);
    const t = num(f.wall_thickness_mm);
    const step = num(f.step_no);
    const steps = num(f.steps_in_class);
    return [step !== null && steps !== null ? `step ${step} of ${steps}` : null, len !== null ? `${len.toFixed(2)} m` : null, t !== null ? `under ${inch(t)} in brick walls` : null, width !== null && depth !== null ? `${Math.round(width)} mm wide, ${Math.round(depth)} mm high` : "step sizes needed"].filter(Boolean).join(" · ");
  }

  if (item === "MEMBRANE") {
    const len = num(f.length_m);
    const walls = num(f.wall_count);
    const rcc = num(f.rcc_length_m);
    return [len !== null ? `${len.toFixed(2)} m of wall` : null, walls !== null ? `${walls} wall${walls === 1 ? "" : "s"}` : null, rcc ? `${rcc.toFixed(2)} m of it concrete` : null, width !== null ? `${Math.round(width)} mm wide` : "width needed"].filter(Boolean).join(" · ");
  }

  if (item === "PLASTER_INSIDE" || item === "PLASTER_OUTSIDE") {
    const area = num(f.area_m2);
    const face = num(f.face_length_m);
    const open = num(f.opening_m2);
    const outer = num(f.outer_wall_count);
    const walls = num(f.wall_count);
    return [area !== null ? `${area.toFixed(2)} m²` : "wall height needed", face !== null ? `${face.toFixed(2)} m of face` : null, open ? `${open.toFixed(2)} m² of openings taken out` : null, walls !== null && outer !== null ? `${outer} of ${walls} walls on the outline` : null].filter(Boolean).join(" · ");
  }

  if (item === "DOOR_FRAME") {
    const count = num(f.door_count);
    const size = Array.isArray(f.size_mm) ? (f.size_mm as number[]) : null;
    return [count !== null ? `${count} door${count === 1 ? "" : "s"}` : null, size ? `${Math.round(size[0])}×${Math.round(size[1])} mm` : null, f.height_assumed === true ? "height assumed" : null, f.frame_class === "THIN" ? "in thin walls" : "in thick walls", width !== null ? `${Math.round(width)} mm frame` : "frame width needed"].filter(Boolean).join(" · ");
  }

  if (item === "EARTH_FILL") {
    const area = num(f.area_m2);
    const rooms = num(f.room_count);
    return [area !== null ? `${area.toFixed(2)} m² of floor` : null, rooms !== null ? `total of ${rooms} room${rooms === 1 ? "" : "s"}` : null, depth !== null ? `${Math.round(depth)} mm deep` : "depth needed (not printed on the plan)"].filter(Boolean).join(" · ");
  }

  if (item === "ROOF_TREATMENT") {
    const area = num(f.area_m2);
    const basis = f.area_basis === "OUTLINE" ? "slab outline" : f.area_basis === "TABLE" ? "covered area of the table" : null;
    return [area !== null ? `${area.toFixed(2)} m² of roof` : null, basis, f.roof_found_by === "TOP_OF_SHEET" ? "top floor assumed to be the roof" : null, f.layers_defined === true ? `layers from ${typeof f.layers_heading === "string" ? f.layers_heading.toLowerCase() : "the specification"}` : Array.isArray(f.layer_sets) ? "roof layers printed under several headings, none chosen" : "layers not read", roofFallText(f), roofEdgeText(f)].filter(Boolean).join(" · ");
  }

  if (item === "FLOOR_FINISH" || item === "CEILING_PAINT" || item === "FLOOR_WET") {
    const area = num(f.area_m2);
    const rooms = num(f.room_count);
    const wet = num(f.wet_room_count);
    const dry = f.floor_scope === "DRY";
    return [
      area !== null ? `${area.toFixed(2)} m² of ${item === "CEILING_PAINT" ? "ceiling" : "floor"}` : null,
      rooms !== null ? `total of ${rooms} room${rooms === 1 ? "" : "s"}` : null,
      item === "FLOOR_FINISH" && dry && wet ? `dry rooms only, ${wet} wet room${wet === 1 ? "" : "s"} on their own line` : null,
      item === "FLOOR_FINISH" && !dry && wet ? `${wet} wet room${wet === 1 ? "" : "s"} included` : null,
      item === "FLOOR_WET" ? "baths and toilets, tiled" : null,
      item === "FLOOR_FINISH" ? "floor material not read" : null,
    ].filter(Boolean).join(" · ");
  }

  if (item === "SKIRTING" || item === "DADO") {
    const len = num(f.length_m);
    const per = num(f.perimeter_m);
    const area = num(f.area_m2);
    const high = num(f.dado_height_mm);
    const doors = num(f.door_count);
    const off = num(f.doors_deducted_m);
    const assumed = num(f.doors_assumed_width);
    const winArea = num(f.windows_m2);
    const winCount = Array.isArray(f.windows) ? f.windows.length : 0;
    const unsized = num(f.windows_unsized);
    const sills = num(f.windows_sill_assumed);
    return [
      item === "DADO" ? (area !== null ? `${area.toFixed(2)} m²` : null) : len !== null ? `${len.toFixed(2)} m` : null,
      item === "DADO" && len !== null ? `${len.toFixed(2)} m round the baths` : per !== null ? `${per.toFixed(2)} m round the rooms` : null,
      item === "DADO" && high !== null ? `${Math.round(high)} mm high` : null,
      doors !== null && off !== null ? `${doors} door${doors === 1 ? "" : "s"} taken off (${off.toFixed(2)} m)` : null,
      item === "DADO" && winCount > 0 && winArea !== null ? `${winCount} window${winCount === 1 ? "" : "s"} taken off (${winArea.toFixed(2)} m²)` : null,
      item === "DADO" && sills ? `${sills} window sill${sills === 1 ? "" : "s"} assumed` : null,
      item === "DADO" && unsized ? `${unsized} window${unsized === 1 ? "" : "s"} without a size not taken off` : null,
      assumed ? `${assumed} door width${assumed === 1 ? "" : "s"} assumed at 900 mm` : null,
    ].filter(Boolean).join(" · ");
  }

  if (item === "WET_WATERPROOF") {
    const area = num(f.area_m2);
    const floor = num(f.floor_m2);
    const turn = num(f.turnup_mm);
    const len = num(f.length_m);
    const doors = num(f.door_count);
    return [
      area !== null ? `${area.toFixed(2)} m²` : null,
      floor !== null ? `${floor.toFixed(2)} m² of floor` : null,
      turn !== null && len !== null ? `${Math.round(turn)} mm up ${len.toFixed(2)} m of wall (assumed)` : null,
      doors ? `${doors} door${doors === 1 ? "" : "s"} taken off` : null,
    ].filter(Boolean).join(" · ");
  }

  if (item === "WALL_TILE") {
    const len = num(f.length_m);
    const rooms = Array.isArray(f.rooms) ? f.rooms.length : null;
    const doors = num(f.door_count);
    const winCount = Array.isArray(f.windows) ? f.windows.length : 0;
    const unsized = num(f.windows_unsized);
    return [
      len !== null ? `${len.toFixed(2)} m of wall` : null,
      rooms !== null ? `${rooms} kitchen${rooms === 1 ? "" : "s"}` : null,
      doors ? `${doors} door${doors === 1 ? "" : "s"} taken off` : null,
      winCount > 0 ? `${winCount} window${winCount === 1 ? "" : "s"} taken off inside the tile height` : null,
      unsized ? `${unsized} window${unsized === 1 ? "" : "s"} without a size not taken off` : null,
      c.missing.includes("tile_height_mm") ? "tile height needed" : null,
    ].filter(Boolean).join(" · ");
  }

  if (item === "PAINT_INSIDE" || item === "PAINT_OUTSIDE") {
    const area = num(f.area_m2);
    const face = num(f.face_length_m);
    const open = num(f.opening_m2);
    const dado = num(f.less_dado_m2);
    return [area !== null ? `${area.toFixed(2)} m²` : "wall height needed", face !== null ? `${face.toFixed(2)} m of face` : null, open ? `${open.toFixed(2)} m² of openings taken out` : null, dado ? `${dado.toFixed(2)} m² of dado taken out` : null].filter(Boolean).join(" · ");
  }

  if (item === "DOOR_AREA" || item === "WINDOW_AREA") {
    const count = num(f.opening_count);
    const size = Array.isArray(f.size_mm) ? (f.size_mm as number[]) : null;
    const each = num(f.area_each_m2);
    const total = num(f.area_m2);
    return [count !== null ? `${count} ${item === "DOOR_AREA" ? "door" : "window"}${count === 1 ? "" : "s"}` : null, size ? `${Math.round(size[0])}×${Math.round(size[1])} mm` : null, each !== null ? `${each.toFixed(2)} m² each` : null, total !== null ? `${total.toFixed(2)} m² in all` : null, f.size_source === "SCHEDULE" ? "size from the schedule" : f.height_assumed === true ? "width as drawn, height assumed" : "size as drawn", "material not read"].filter(Boolean).join(" · ");
  }

  if (item === "FLOOR_PCC" || item === "FLOOR_BALLAST" || item === "FLOOR_SAND_FILL") {
    const area = num(f.area_m2);
    const rooms = num(f.room_count);
    const t = num(f.thickness_mm);
    const mix = typeof f.mix === "string" && f.mix ? ` (${f.mix})` : "";
    return [area !== null ? `${area.toFixed(2)} m² of floor` : null, rooms !== null ? `total of ${rooms} room${rooms === 1 ? "" : "s"}` : null, t !== null ? `${inch(t)} in thick${mix}` : null, "layer not tied to a floor heading"].filter(Boolean).join(" · ");
  }

  if (item === "MEMBRANE_COAT" || item === "MEMBRANE_POLYTHENE") {
    const len = num(f.length_m);
    const h = num(f.height_mm);
    const n = num(f.layers);
    const unit = f.layer_unit === "coat" ? "coat" : "layer";
    return [n !== null ? `${n} ${unit}${n === 1 ? "" : "s"}` : null, len !== null ? `${len.toFixed(2)} m of outside wall face` : null, h !== null ? `${Math.round(h)} mm high` : null, "same face as the single membrane item: accept one"].filter(Boolean).join(" · ");
  }

  if (item === "PCC_PAD") {
    const size = Array.isArray(f.size_mm) ? (f.size_mm as number[]) : null;
    const marks = num(f.marks);
    return [marks !== null ? `${marks} bed${marks === 1 ? "" : "s"}` : null, size ? `${Math.round(size[0])}×${Math.round(size[1])} mm each` : null, depth !== null ? `${Math.round(depth)} mm thick` : "thickness needed"].filter(Boolean).join(" · ");
  }
  const len = num(f.length_m);
  const t = num(f.wall_thickness_mm);
  const walls = num(f.wall_count);
  const rcc = num(f.rcc_length_m);
  const base = [len !== null ? `${len.toFixed(2)} m` : null, t !== null ? `under ${inch(t)} in walls` : null, walls !== null ? `${walls} wall${walls === 1 ? "" : "s"}` : null, rcc ? `${rcc.toFixed(2)} m of it concrete` : null];
  const tail = item === "TERMITE_STRIP" ? sizes(null, "") : item === "PCC_STRIP" ? sizes("thick", "thickness") : sizes("deep", "depth");
  return [...base, ...tail].filter(Boolean).join(" · ");
}

function siteLine(c: TakeoffCandidate): string {
  const f = c.facts as Record<string, unknown>;
  const num = (v: unknown) => (typeof v === "number" ? v : null);
  const ft = (mm: number | null) => (mm === null ? null : `${(mm / 304.8).toFixed(2).replace(/\.?0+$/, "")} ft`);
  const kind = siteKind(c);
  const need = c.missing.length ? `${c.missing.map((m) => ({ length_mm: "length", width_mm: "width", height_mm: "height", thickness_mm: "thickness" })[m as "length_mm"] ?? m).join(", ")} to type` : null;
  if (kind === "BOUNDARY_WALL") {
    const gate = f.gate_deducted === true ? num(f.gate_mm) : null;
    return [ft(num(f.length_mm)) ? `${ft(num(f.length_mm))} long` : null, ft(num(f.height_mm)) ? `${ft(num(f.height_mm))} high` : null, f.overall_text ? `of ${String(f.overall_text)} overall` : null, gate !== null ? `gate ${ft(gate)} taken out` : null, need].filter(Boolean).join(" · ");
  }
  if (kind === "GATE") return [ft(num(f.width_mm)) ? `${ft(num(f.width_mm))} wide` : null, ft(num(f.height_mm)) ? `${ft(num(f.height_mm))} high` : null, need].filter(Boolean).join(" · ");
  if (kind === "PORCH_RAMP") {
    const levels = Array.isArray(f.levels_printed) ? (f.levels_printed as string[]) : [];
    return [levels.length ? `levels ${levels.join(", ")}` : null, need].filter(Boolean).join(" · ");
  }
  const repeats = num(f.labels_on_sheet);
  return [repeats !== null && repeats > 1 ? `labelled ${repeats} times on this sheet` : null, need].filter(Boolean).join(" · ");
}

function neckText(f: Record<string, unknown>): string {
  const a = f.neck_assumed as { text?: unknown } | null | undefined;
  return a && typeof a.text === "string" ? `height ${a.text} assumed` : "height needed";
}

export function neckHeightAssumed(list: TakeoffCandidate[]): string | null {
  for (const c of list) {
    const a = isNeckColumn(c) ? ((c.facts as Record<string, unknown> | null)?.neck_assumed as { text?: unknown } | undefined) : undefined;
    if (a && typeof a.text === "string") return a.text;
  }
  return null;
}

export function factLine(c: TakeoffCandidate): string {
  const f = c.facts as Record<string, unknown>;
  const num = (v: unknown) => (typeof v === "number" ? v : null);
  const item = foundationItem(c);
  if (item !== null) return foundationLine(c, item);
  if (isTankWall(c)) {
    const gaps = Array.isArray(f.gaps_mm) ? (f.gaps_mm as number[]) : [];
    const t = num(f.thickness_used_mm);
    const kind = f.tank_kind === "OHWT" ? "overhead tank wall" : f.tank_kind === "UGWT" ? "underground tank wall" : "tank wall";
    return [kind, t !== null ? `${Math.round(t)} mm thick` : null, gaps.length ? `${gaps.length} opening${gaps.length > 1 ? "s" : ""} inside` : null, "height needed"].filter(Boolean).join(" · ");
  }
  if (isNeckColumn(c)) {
    const size = Array.isArray(f.size_used_mm) ? (f.size_used_mm as number[]) : null;
    return [`neck of footing ${String(f.neck_of)}`, size ? `${(size[0] / 25.4).toFixed(1).replace(/\.0$/, "")}×${(size[1] / 25.4).toFixed(1).replace(/\.0$/, "")} in` : null, `${c.count} nos`, neckText(f)].filter(Boolean).join(" · ");
  }
  if (c.category === "WALL") {
    const gaps = Array.isArray(f.gaps_mm) ? (f.gaps_mm as number[]) : [];
    const t = num(f.thickness_used_mm);
    return [t !== null ? `${Math.round(t)} mm thick` : null, gaps.length ? `${gaps.length} opening${gaps.length > 1 ? "s" : ""} inside (${(gaps.reduce((a, b) => a + b, 0) / 1000).toFixed(2)} m)` : null].filter(Boolean).join(" · ");
  }

  if (c.category === "ROOM") {
    const label = num(f.label_area_m2);
    const p = num(f.perimeter_m);
    return [p !== null ? `perimeter ${p.toFixed(2)} m` : null, label !== null ? `label says ${label.toFixed(2)} m²` : null].filter(Boolean).join(" · ");
    }

  if (c.category === "BEAM") {
    const len = num(f.length_m);
    const t = num(f.wall_thickness_mm);
    const walls = num(f.wall_count);
    const gaps = num(f.openings_m);
    const depth = num((c.params as Record<string, unknown>).depth_mm);
    if (f.from_strips === true) {
      const strips = num(f.strip_count);
      const w = num(f.beam_width_mm);
      const cols = num(f.columns_taken);
      return [len !== null ? `${len.toFixed(2)} m along ${strips ?? 0} hatched strip${strips === 1 ? "" : "s"}${cols ? `, between column faces (${cols} column${cols === 1 ? "" : "s"} taken off)` : ""}` : null, w !== null ? `${(w / 25.4).toFixed(1).replace(/\.0$/, "")} in wide` : null, depth !== null ? `${Math.round(depth)} mm deep` : "depth needed"].filter(Boolean).join(" · ");
    }
    if (f.derived_from !== "WALLS") return "";
    return [f.beam_role === "PLINTH" ? "plinth beam" : "roof beam", len !== null ? `${len.toFixed(2)} m over ${walls ?? 0} wall${walls === 1 ? "" : "s"}` : null, t !== null ? `${(t / 25.4).toFixed(1).replace(/\.0$/, "")} in wide` : null, gaps ? `${gaps.toFixed(2)} m of it over openings` : null, depth !== null ? `${Math.round(depth)} mm deep` : "depth needed"].filter(Boolean).join(" · ");
  }

  if (c.category === "SLAB") {
    const dims = Array.isArray(f.dims_mm) ? (f.dims_mm as number[]) : null;
    const t = num(f.thickness_mm);
    const area = num(f.area_m2);
    const choices = slabThicknessChoices(c);
    const options = choices.length > 1 ? `thickness printed as ${choices.map((o) => `${(o.mm / 25.4).toFixed(1).replace(/\.0$/, "")} in (${o.sources.map((x) => SLAB_SOURCE_TEXT[x] ?? x).join(", ")})`).join(" / ")}` : null;
    const proj = (f.projections ?? null) as { applied?: boolean; sides?: Record<string, number> } | null;
    const gross = num(f.gross_area_m2);
    const strip = num(f.projection_area_m2);
    const sideText = proj?.sides ? Object.entries(proj.sides).map(([s, w]) => `${s.toLowerCase()} ${(w / 304.8).toFixed(1).replace(/\.0$/, "")} ft`).join(", ") : "";
    const covered = proj?.applied && gross !== null && strip !== null ? `${gross.toFixed(2)} m² with ${strip.toFixed(2)} m² of roof projection (${sideText})` : area !== null ? `${area.toFixed(2)} m² covered` : null;
    const openings = Array.isArray(f.openings) ? (f.openings as { deduct?: boolean; name?: string }[]) : [];
    const taken = openings.filter((o) => o.deduct === true);
    const less = num(f.openings_area_m2);
    const openingText = taken.length > 0 && less !== null ? `less ${less.toFixed(2)} m² of openings (${[...new Set(taken.map((o) => String(o.name ?? "opening").toLowerCase()))].join(", ")})` : null;
    return [covered, dims ? `${Math.round(dims[0])}×${Math.round(dims[1])} mm printed` : "size not printed", t !== null ? `${Math.round(t)} mm thick` : "thickness needed", openingText, options].filter(Boolean).join(" · ");
  }


  if (c.category === "LINTEL") {
    const sec = Array.isArray(f.section_mm) ? (f.section_mm as number[]) : null;
    const span = Array.isArray(f.opening_size_mm) ? (f.opening_size_mm as number[]) : null;
    const hosted = (f.hosted ?? null) as { thin?: number; rcc?: number } | null;
    return [span ? `opening ${Math.round(span[0])} mm wide` : null, sec ? `section ${(sec[0] / 25.4).toFixed(1).replace(/\.0$/, "")}×${(sec[1] / 25.4).toFixed(1).replace(/\.0$/, "")} in` : "section needed", num(f.bearing_mm) !== null ? `bearing ${((f.bearing_mm as number) / 25.4).toFixed(1).replace(/\.0$/, "")} in assumed` : null, hosted?.thin ? `${hosted.thin} in 4.5 in walls` : null, hosted?.rcc ? `${hosted.rcc} in RCC walls` : null].filter(Boolean).join(" · ");
   }

  if (c.category === "STAIR") {
    const inch = (v: unknown) => (typeof v === "number" ? (v / 25.4).toFixed(1).replace(/\.0$/, "") : null);
    const steps = num(f.steps);
    const width = num(f.stair_width_mm);
    const waist = num(f.waist_mm);
    const way = f.direction === "UP" ? "going up" : f.direction === "DOWN" ? "going down" : null;
    const treads = num(f.treads_drawn);
    const pitch = num(f.tread_drawn_mm);
    const drawnOnly = f.details_printed === false;
    const rise = (f.rise ?? null) as { differs?: boolean; storey_mm?: number } | null;
    const landings = Array.isArray(f.landings) ? f.landings.length : 0;
    const landingArea = num(f.landings_area_m2);
    const landingText = landings > 0 ? `plus ${landings} landing${landings === 1 ? "" : "s"}${landingArea !== null ? ` (${landingArea.toFixed(2)} m²)` : ""}` : null;
    return [way, drawnOnly ? "riser and steps not printed on any sheet" : null, steps !== null ? `${steps} steps` : null, inch(f.riser_mm) ? `riser ${inch(f.riser_mm)} in` : null, inch(f.tread_mm) ? `tread ${inch(f.tread_mm)} in` : null, drawnOnly && treads !== null ? `${treads} treads drawn${pitch !== null ? `, ${Math.round(pitch)} mm apart` : ""}` : f.short_flight === true && treads !== null ? `only ${treads} treads drawn` : null, width !== null ? `${Math.round(width)} mm wide${f.width_source === "PRINTED_BESIDE" ? " (printed beside it)" : f.width_source === "DRAWN" ? " (as drawn)" : ""}` : "size needed", waist !== null ? `waist ${Math.round(waist)} mm ${f.waist_source === "PRINTED" ? "printed" : "assumed"}` : c.missing.includes("waist_mm") ? "waist slab to type" : null, rise ? (rise.differs ? `rise differs from the ${Math.round(rise.storey_mm ?? 0)} mm storey` : "rise matches the storey") : null, landingText].filter(Boolean).join(" · ");
  }

  if (c.category === "SITE") return siteLine(c);

  if (c.category === "COLUMN" && f.from_shapes === true) {
    const size = Array.isArray(f.size_drawn_mm) ? (f.size_drawn_mm as number[]) : null;
    const inch = (v: number) => (v / 25.4).toFixed(1).replace(/\.0$/, "");
    const seen = num(f.shapes_drawn);
    const inferred = num(f.inferred);
    return [
      size ? `${inch(size[0])}×${inch(size[1])} in drawn on the floor plan, no mark` : "drawn on the floor plan, no mark",
      seen !== null && seen > 0 ? `${seen} seen on this plan` : null,
      inferred !== null && inferred > 0 ? `${inferred} taken from the floor above` : null,
      c.missing.includes("height_mm") ? "height needed" : null,
    ].filter(Boolean).join(" · ");
  }

  const sched = Array.isArray(f.size_schedule_mm) ? (f.size_schedule_mm as number[]) : null;
  const drawn = Array.isArray(f.size_drawn_mm) ? (f.size_drawn_mm as number[]) : null;

  const parts: string[] = [];
  if (c.category === "FOOTING" && Array.isArray(f.paired_column)) parts.push(`written beside ${String(f.paired_column[0])} on the foundation plan`);
  if (f.found_by === "SYMBOL_SCAN") {
    const n = num(f.symbols);
    parts.push(`${n ?? c.count} drawn, no mark on the plan`);
    if (drawn) parts.push(`${Math.round(drawn[0])} mm wide`);
    if (drawn && f.height_assumed === true) parts.push(`height assumed ${Math.round(drawn[1])} mm`);
    return parts.join(" · ");
  }
  if (c.category === "COLUMN") {
    const src = (f.steel_source ?? null) as { how?: string; text?: string } | null;
    const alts = Array.isArray(f.steel_alternatives) ? (f.steel_alternatives as { steel_text?: string }[]).map((a) => a.steel_text).filter((t): t is string => typeof t === "string") : [];
    if (typeof f.steel_text === "string" && f.steel_text) parts.push(`steel ${f.steel_text}${src?.how === "DETAIL" ? " (from the column detail)" : ""}`);
    else if (alts.length > 0) parts.push(`column detail prints different bars: ${alts.join(" / ")} (none applied)`);
  }
  if (sched) parts.push(`schedule ${Math.round(sched[0])}×${Math.round(sched[1])}`);
  if (drawn) parts.push(`drawn ${Math.round(drawn[0])}${f.height_assumed === true ? ` mm wide, height assumed ${Math.round(drawn[1])} mm` : `×${Math.round(drawn[1])}`}`);
  const seen = f.symbols as { marks?: unknown; found?: unknown } | undefined;
  if (seen && typeof seen.marks === "number" && typeof seen.found === "number") parts.push(`${seen.found} of ${seen.marks} seen drawn`);
  const width = num(f.width_drawn_mm);
  if (width !== null && !drawn) parts.push(`drawn width ${Math.round(width)} mm`);
  return parts.join(" · ");
}

export function buildAcceptBody(ids: string[], heights: Heights, workItems: Record<string, string>, steel: Record<string, SteelSet>, picks: Record<string, string> = {},
  kinds: Record<string, string> = {}): AcceptBody {
  const body: AcceptBody = { ids };
  for (const f of HEIGHT_ORDER) {
    const n = validHeight(heights[f]);
    if (n !== null) (body as unknown as Record<string, number>)[f] = n;
  }
  const items: Record<string, string> = {};
  for (const id of ids) {
    const kind = kinds[id];
    const code = kind ? (workItems[kind] ?? "").trim() : "";
    if (code) items[kind] = code;
  }
  if (Object.keys(items).length) body.work_items = items;
  const typed = steelForAccept(ids, steel);
  if (typed) body.steel = typed;
  const chosen = Object.fromEntries(ids.filter((id) => picks[id]).map((id) => [id, picks[id]]));
  if (Object.keys(chosen).length) body.section_picks = chosen;
  return body;
}

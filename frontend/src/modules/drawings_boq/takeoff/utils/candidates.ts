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
  | "boundary_side_mm"
  | "boundary_rear_mm"
  | "rain_pipe_length_mm"
  | "sewer_length_mm"
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
  "boundary_side_mm",
  "boundary_rear_mm",
  "rain_pipe_length_mm",
  "sewer_length_mm",
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
  boundary_side_mm: "",
  boundary_rear_mm: "",
  rain_pipe_length_mm: "",
  sewer_length_mm: "",
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
  boundary_side_mm: "Boundary wall: length of one side wall, 0 where there is none (mm)",
  boundary_rear_mm: "Boundary wall: length of the rear wall, 0 where there is none (mm)",
  rain_pipe_length_mm: "Rain water pipe: length of one pipe, roof to ground (mm)",
  sewer_length_mm: "Sewer pipe line: total length of the line (mm)",
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
  | "ARCH_CENTRING"
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
  | "WET_WATERPROOF"
  | "FLOOR_CS_BED"
  | "FLOOR_BRICK_TILES"
  | "FLOOR_MUD_PLASTER"
  | "FLOOR_COMPACTED_MUD"
  | "ROOF_PCC"
  | "ROOF_BALLAST"
  | "ROOF_SCREED"
  | "ROOF_MEMBRANE"
  | "ROOF_POLYTHENE"
  | "BOUNDARY_RETURNS"
  | "BOUNDARY_PLASTER"
  | "BOUNDARY_PAINT"
  | "SCAFFOLD_OUTSIDE"
  | "PROPS_SLAB"
  | "RAIN_PIPE"
  | "SEWER_PIPE"
  | "DRAIN_MANHOLE"
  | "INSPECTION_CHAMBER"
  | "GULLY_TRAP"
  | "PILE_BORE"
  | "PILE_CONCRETE"
  | "RAFT_SLAB"
  | "RAFT_PCC"
  | "RAFT_EDGE_FORM"
  | "ELEC_LIGHT"

  | "ELEC_FAN"
  | "ELEC_SOCKET"
  | "ELEC_SWITCH"
  | "ELEC_LOWV"
  | "ELEC_BOARD"
  | "ELEC_OTHER";

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
  "ARCH_CENTRING",
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
  "FLOOR_CS_BED",
  "FLOOR_BRICK_TILES",
  "FLOOR_MUD_PLASTER",
  "FLOOR_COMPACTED_MUD",
  "ROOF_PCC",
  "ROOF_BALLAST",
"ROOF_SCREED",
  "ROOF_MEMBRANE",
  "ROOF_POLYTHENE",
  "BOUNDARY_RETURNS",
  "BOUNDARY_PLASTER",
  "BOUNDARY_PAINT",
  "SCAFFOLD_OUTSIDE",
  "PROPS_SLAB",
  "RAIN_PIPE",
  "SEWER_PIPE",
  "DRAIN_MANHOLE",
  "INSPECTION_CHAMBER",
  "GULLY_TRAP",
  "PILE_BORE",
  "PILE_CONCRETE",
  "RAFT_SLAB",
  "RAFT_PCC",
  "RAFT_EDGE_FORM",
  "ELEC_LIGHT",
  "ELEC_FAN",
  "ELEC_SOCKET",
  "ELEC_SWITCH",
  "ELEC_LOWV",
  "ELEC_BOARD",
  "ELEC_OTHER",
];

const BOUNDARY_ITEMS: FoundationItem[] = ["BOUNDARY_RETURNS", "BOUNDARY_PLASTER", "BOUNDARY_PAINT"];

export const ZERO_OK_FIELDS: HeightField[] = ["boundary_side_mm", "boundary_rear_mm"];

const LONG_FIELDS: HeightField[] = ["rain_pipe_length_mm", "sewer_length_mm"];

const LAYER_ITEMS: FoundationItem[] = [
  "FLOOR_PCC",  "FLOOR_BALLAST",
  "FLOOR_SAND_FILL",
  "FLOOR_CS_BED",
  "FLOOR_BRICK_TILES",
  "FLOOR_MUD_PLASTER",
  "FLOOR_COMPACTED_MUD",
  "ROOF_PCC",
  "ROOF_BALLAST",
  "ROOF_SCREED",
  "ROOF_MEMBRANE",
  "ROOF_POLYTHENE",
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
  if (BOUNDARY_ITEMS.includes(item)) {
    if (c.missing.includes("side_length_mm")) out.push("boundary_side_mm");
    if (c.missing.includes("rear_length_mm")) out.push("boundary_rear_mm");
    if (c.missing.includes("height_mm")) out.push("site_height_mm");
    if (c.missing.includes("thickness_mm")) out.push("site_thickness_mm");
    return out;
  }
  if (item === "RAIN_PIPE" || item === "SEWER_PIPE") {
    if (c.missing.includes("length_mm")) out.push(item === "RAIN_PIPE" ? "rain_pipe_length_mm" : "sewer_length_mm");
    return out;
  }
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
  ARCH_CENTRING: "Centring to arched openings",
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
  FLOOR_CS_BED: "Cement-sand bed under the floor finish",
  FLOOR_BRICK_TILES: "Brick tiles (specification)",
  FLOOR_MUD_PLASTER: "Mud plaster (specification)",
  FLOOR_COMPACTED_MUD: "Compacted mud layer under the floor",
  ROOF_PCC: "Concrete bed on the roof (specification)",
  ROOF_BALLAST: "Brick ballast on the roof",
   ROOF_SCREED: "Cement-sand bed on the roof",
  ROOF_MEMBRANE: "Waterproofing on the roof",
  ROOF_POLYTHENE: "Polythene sheet on the roof",
  BOUNDARY_RETURNS: "Boundary wall: side and rear walls",
  BOUNDARY_PLASTER: "Plaster on the boundary wall",
  BOUNDARY_PAINT: "Paint on the boundary wall",
  SCAFFOLD_OUTSIDE: "Scaffolding on the outside walls above 3.6 m",
  PROPS_SLAB: "Props under slabs clearer than 3.6 m",
  RAIN_PIPE: "Rain water pipes",
  SEWER_PIPE: "Sewer pipe line",
  DRAIN_MANHOLE: "Manholes",
  INSPECTION_CHAMBER: "Inspection chambers",
  GULLY_TRAP: "Gully traps",
  PILE_BORE: "Boring of piles",
  PILE_CONCRETE: "Concrete in piles",
  RAFT_SLAB: "Raft slab",
  RAFT_PCC: "Concrete bed under the raft",
  RAFT_EDGE_FORM: "Shuttering to the raft edge",
  ELEC_LIGHT: "Electrical lights",
  ELEC_FAN: "Electrical fans",
  ELEC_SOCKET: "Electrical sockets and plugs",
  ELEC_SWITCH: "Electrical switches",
  ELEC_LOWV: "Telephone, TV, data, alarm and bell points",
  ELEC_BOARD: "Electrical boards, earthing and supply",
  ELEC_OTHER: "Other electrical points",
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

export function validHeight(text: string, field?: HeightField): number | null {
  const n = Number(text.trim().replace(/,/g, ""));
  if (field !== undefined && ZERO_OK_FIELDS.includes(field)) return text.trim() !== "" && Number.isFinite(n) && n >= 0 && n <= 60000 ? n : null;
  if (field !== undefined && LONG_FIELDS.includes(field)) return Number.isFinite(n) && n >= 75 && n <= 60000 ? n : null;
  return Number.isFinite(n) && n >= 75 && n <= 20000 ? n : null;
}

export function blockedByHeight(list: TakeoffCandidate[], ids: Set<string>, typed: Heights, picks?: Record<string, string>): TakeoffCandidate[] {
  return list.filter((c) => {
    if (!ids.has(c.id)) return false;
    return fieldsStillNeeded(c, picks).some((f) => validHeight(typed[f], f) === null);
  });
}

export function candidatePoints(c: Pick<TakeoffCandidate, "kind" | "geometry">): Pt[] {
  if (c.kind === "AREA") return (c.geometry as AreaGeometry).outer ?? [];
  return ((c.geometry as LengthGeometry | CountGeometry).points ?? []) as Pt[];
}

function beamSectionText(f: Record<string, unknown>): string | null {
  const mark = typeof f.section_mark === "string" && f.section_mark ? f.section_mark : null;
  return mark ? `section ${mark}${f.section_assumed === true ? " (assumed)" : ""}` : null;
}

const STALE_TEXT: Record<string, string> = {
  SCALE_CHANGED: "The scale of this sheet changed after this was read.",
  SHEET_READ_AGAIN: "The sheet was read again after this was found.",
  NEWER_LOGIC: "The reading rules have been improved since this was found.",
  SHEET_READER_OLDER: "This sheet was stored by an older reader. Prepare the drawing again so it is read with the present rules, then run the extraction again.",
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

  if (item === "ARCH_CENTRING") {
    const count = num(f.opening_count);
    const w = num(f.width_mm);
    const girth = num(f.girth_mm);
    const thick = num(f.wall_thickness_mm);
    return [
      count !== null ? `${count} arched ${f.derived_from === "WINDOWS" ? "window" : "door"}${count === 1 ? "" : "s"}` : null,
      w !== null ? `${Math.round(w)} mm wide` : null,
      girth !== null ? `soffit ${Math.round(girth)} mm (semicircle, assumed)` : null,
      thick !== null ? `${Math.round(thick)} mm wall${f.wall_from === "ASSUMED" ? ", assumed" : ""}` : null,
      "opening still taken off as the full rectangle",
    ].filter(Boolean).join(" · ");
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

  if (item === "RAIN_PIPE" || item === "SEWER_PIPE" || item === "DRAIN_MANHOLE" || item === "INSPECTION_CHAMBER" || item === "GULLY_TRAP") {
    const dia = num(f.diameter_in);
    const labels = num(f.labels_on_sheet);
    if (item === "DRAIN_MANHOLE" || item === "INSPECTION_CHAMBER" || item === "GULLY_TRAP") {
      const marks = Array.isArray(f.marks) ? (f.marks as unknown[]).map(String) : [];
      const total = labels ?? marks.length;
      return [`${total} label${total === 1 ? "" : "s"} counted`, marks.length ? marks.slice(0, 8).join(", ") + (marks.length > 8 ? " …" : "") : null, "number only: depth and size are not taken"].filter(Boolean).join(" · ");
    }
    if (item === "SEWER_PIPE") {
      return [dia !== null ? `${dia} in pipe` : "pipe size not written", "diagram, not to scale", c.missing.includes("length_mm") ? "type the total length" : null].filter(Boolean).join(" · ");
    }
    const drop = num(f.drop_mm);
    const top = num(f.top_mm);
    const bottom = num(f.bottom_mm);
    return [
      dia !== null ? `${dia} in pipe` : "pipe size not written",
      labels !== null ? `${labels} label${labels === 1 ? "" : "s"} on the sheet, one pipe each (assumed)` : null,
      drop !== null ? `${(drop / 304.8).toFixed(2).replace(/\.?0+$/, "")} ft each, roof to ground floor` : "level of the roof or ground floor not printed: type the length",
      top !== null && bottom !== null ? `levels ${(bottom / 304.8).toFixed(2).replace(/\.?0+$/, "")} to ${(top / 304.8).toFixed(2).replace(/\.?0+$/, "")} ft on the sections` : null,
    ].filter(Boolean).join(" · ");
  }

  if (item === "PILE_BORE" || item === "PILE_CONCRETE") {
    const n = num(f.piles);
    const dia = num(f.pile_dia_mm);
    const len = num(f.pile_length_mm);
    const total = num(f.total_length_m);
    const units = f.pile_units as { dia?: string; length?: string } | undefined;
    return [
      f.pile_mark ? `pile ${String(f.pile_mark)}` : null,
      n !== null ? `${n} pile${n === 1 ? "" : "s"}` : null,
      dia !== null ? `${Math.round(dia)} mm dia` : null,
      len !== null ? `${(len / 1000).toFixed(2).replace(/\.?0+$/, "")} m each` : null,
      total !== null && item === "PILE_BORE" ? `${total.toFixed(2)} m in all` : null,
      units && (units.dia === "ASSUMED" || units.length === "ASSUMED") ? "a unit was not written: check it" : null,
      "caps, steel and cut-off are not taken",
    ].filter(Boolean).join(" · ");
  }

  if (item === "RAFT_SLAB" || item === "RAFT_PCC" || item === "RAFT_EDGE_FORM") {
    const t = num(f.raft_thickness_mm);
    const fp = Array.isArray(f.footprint_mm) ? (f.footprint_mm as number[]) : null;
    return [
      t !== null ? `${Math.round(t)} mm thick` : null,
      typeof f.raft_grade === "string" ? f.raft_grade : null,
      fp ? `outline ${(fp[0] / 1000).toFixed(2)} × ${(fp[1] / 1000).toFixed(2)} m, taken from the ${String(f.footprint_floor ?? "lowest floor").toLowerCase()} covered area (assumed)` : null,
      item === "RAFT_PCC" ? "bed 3 in, assumed" : null,
      item === "RAFT_EDGE_FORM" ? "round the outline, as high as the raft is thick (assumed)" : null,
      "excavation and steel are not taken",
    ].filter(Boolean).join(" · ");
  }

  if (item === "ELEC_LIGHT" || item === "ELEC_FAN" || item === "ELEC_SOCKET" || item === "ELEC_SWITCH" || item === "ELEC_LOWV" || item === "ELEC_BOARD" || item === "ELEC_OTHER") {
    const height = num(f.mounting_height_mm);
    const aside = num(f.set_aside_other_size);
    return [
      typeof f.electrical === "string" ? f.electrical : null,
      f.counted_by === "TEXT" ? "counted by its text tag" : "counted by its legend picture: check against the plan",
      height !== null ? `${(height / 304.8).toFixed(2).replace(/\.?0+$/, "")} ft above the floor` : null,
      aside !== null && aside > 0 ? `${aside} of another size not counted` : null,
      "number only: wiring and conduit are not taken",
    ].filter(Boolean).join(" · ");
  }

  if (item === "SCAFFOLD_OUTSIDE" || item === "PROPS_SLAB") {
    const ft = (mm: number | null) => (mm === null ? null : `${(mm / 304.8).toFixed(2).replace(/\.?0+$/, "")} ft`);
    const area = num(f.area_m2);
    const threshold = num(f.threshold_mm);
    if (item === "SCAFFOLD_OUTSIDE") {
      const face = num(f.face_length_m);
      const above = num(f.above_mm);
      const level = num(f.floor_level_mm);
      const top = num(f.top_mm);
      return [
        area !== null ? `${area.toFixed(2)} m²` : null,
        face !== null ? `${face.toFixed(2)} m of outside face` : null,
        above !== null ? `${ft(above)} of wall above ${threshold !== null ? `${(threshold / 1000).toFixed(1)} m` : "the threshold"}` : null,
        level !== null && top !== null ? `floor from ${ft(level)} to ${ft(top)} on the sections` : null,
        num(f.whole_storey_m2) !== null ? `${(num(f.whole_storey_m2) as number).toFixed(2)} m² if the whole storey is billed` : null,
      ].filter(Boolean).join(" · ");
    }
    const clear = num(f.clear_mm);
    const steps = num(f.steps);
    const slab = num(f.slab_area_m2);
    return [
      area !== null ? `${area.toFixed(2)} m²${steps !== null && slab !== null ? ` (${slab.toFixed(2)} m² of slab x ${steps} extra metre${steps === 1 ? "" : "s"}, assumed)` : " of slab"}` : null,
      clear !== null ? `${ft(clear)} clear height on the sections` : null,
      threshold !== null ? `over ${(threshold / 1000).toFixed(1)} m` : null,
    ].filter(Boolean).join(" · ");
  }

  if (BOUNDARY_ITEMS.includes(item)) {
    const ft = (mm: number | null) => (mm === null ? null : `${(mm / 304.8).toFixed(2).replace(/\.?0+$/, "")} ft`);
    const front = num(f.front_length_mm);
    const high = num(f.height_mm);
    const gate = f.gate_deducted === true ? num(f.gate_mm) : null;
    return [
      ft(front) ? `front wall ${ft(front)} long` : null,
      ft(high) ? `${ft(high)} high` : "height needed",
      item === "BOUNDARY_RETURNS" ? "side and rear walls: type their lengths" : "both faces, with the side and rear walls from the lengths you type",
      gate !== null ? `gate ${ft(gate)} taken out` : null,
    ].filter(Boolean).join(" · ");
  }

  if (LAYER_ITEMS.includes(item)) {
    const roof = f.layer_of === "ROOF";
    const area = num(f.area_m2);
    const rooms = num(f.room_count);
    const t = num(f.thickness_mm);
    const n = num(f.layers);
    const mix = typeof f.mix === "string" && f.mix ? ` (${f.mix})` : "";
    const head = typeof f.spec_heading === "string" && f.spec_heading ? f.spec_heading : null;
    return [
      area !== null ? `${area.toFixed(2)} m² of ${roof ? "roof" : "floor"}` : null,
      rooms !== null ? `total of ${rooms} room${rooms === 1 ? "" : "s"}` : null,
      t !== null ? `${inch(t)} in thick${mix}` : null,
      n !== null ? `${n} ${f.layer_unit === "coat" ? "coat" : "layer"}${n === 1 ? "" : "s"}` : null,
      head ? `under the "${head}" heading` : "layer not tied to a floor heading",
    ].filter(Boolean).join(" · ");
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
  const said = f.sizes_assumed && typeof f.sizes_assumed === "object" ? (f.sizes_assumed as Record<string, unknown>) : null;
  const sizes = (f.sizes_mm ?? {}) as Record<string, unknown>;
  const worked = said
    ? ([["length_mm", "long"], ["width_mm", "wide"], ["height_mm", "high"]] as const)
        .filter(([token]) => token in said && num(sizes[token]) !== null)
        .map(([token, word]) => `${ft(num(sizes[token]))} ${word}`)
    : [];
  const wall = said && "thickness_mm" in said ? num(sizes.thickness_mm) : null;
  const slabs = f.tank_slabs_mm as { top_mm?: unknown; bottom_mm?: unknown } | null | undefined;
  const inches = (mm: number) => `${(mm / 25.4).toFixed(1).replace(/\.0$/, "")} in`;
  const slabText = slabs && num(slabs.top_mm) !== null && num(slabs.bottom_mm) !== null ? `slabs ${inches(num(slabs.top_mm) as number)} top, ${inches(num(slabs.bottom_mm) as number)} bottom, as the section prints them` : null;
  const assumed = worked.length || wall !== null ? `assumed from the tank drawings: ${[...worked, wall !== null ? `${inches(wall)} walls` : null].filter(Boolean).join(", ")}` : null;
  return [repeats !== null && repeats > 1 ? `labelled ${repeats} times on this sheet` : null, assumed, slabText, need].filter(Boolean).join(" · ");
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

function setAsideText(f: Record<string, unknown>): string | null {
  const a = f.set_aside as { by?: unknown; page_no?: unknown } | null | undefined;
  if (!a || typeof a !== "object") return null;
  if (a.by === "FLOOR_CHOICE" && typeof a.page_no === "number") return `set aside: this floor is read from page ${a.page_no}`;
  if (a.by === "DRAIN_REPEAT" && typeof a.page_no === "number") return `set aside: the same pipe is read on page ${a.page_no}; restore it if it is another pipe`;
  return "set aside: the same item is on another sheet";
}

function steelText(f: Record<string, unknown>): string | null {
  const s = f.steel_summary as { state?: string; kg?: unknown; source?: unknown; lines?: { role?: unknown; count?: unknown; bar?: unknown; cut_m?: unknown }[] } | null | undefined;
  if (!s || typeof s !== "object") return null;
  if (s.state === "NO_SIZE") return "bars read, size needed to weigh them";
  const kg = Number(s.kg);
  if (s.state !== "WEIGHED" || !Number.isFinite(kg)) return null;
  const parts = (s.lines ?? []).map((l) => {
    const cut = Number(l.cut_m);
    return `${String(l.role ?? "bars")} ${l.count ?? ""}${l.bar ? ` #${l.bar}` : ""}${Number.isFinite(cut) ? ` × ${cut.toFixed(2)} m` : ""}`.replace(/\s+/g, " ").trim();
  });
  return `steel ${kg.toFixed(1)} kg per member${s.source === "ASSUMED" ? " (assumed)" : ""}${parts.length ? `: ${parts.join("; ")}` : ""}`;
}

const QS_INPUTS: [string, string][] = [
  ["FOOTING_DEPTH_QS", "footing depth"],
  ["NECK_HEIGHT_ASSUMED", "neck column height"],
  ["HEIGHT_FROM_QS", "height"],
  ["TANK_SLABS_QS", "tank slab thicknesses"],
  ["SITE_WALL_QS_ESTIMATE", "boundary wall thickness"],
];

function qsText(c: TakeoffCandidate): string | null {
  if ((c as { decision?: string }).decision === "ACCEPTED") return null;
  const codes = new Set((c.notes ?? []).map((n) => n.code));
  const printed = codes.has("HEIGHT_FROM_SECTION") || codes.has("HEIGHT_FROM_NOTE");
  const names = QS_INPUTS.filter(([code]) => codes.has(code) && !(code === "HEIGHT_FROM_QS" && printed)).map(([, name]) => name);
  return names.length ? `from the QS's workbook, not printed: ${names.join(", ")}` : null;
}

function sectionText(f: Record<string, unknown>): string | null {
  const parts: string[] = [];
  const t = typeof f.host_thickness_mm === "number" ? f.host_thickness_mm : null;
  if (f.frame_width_from === "WALL") parts.push(`frame as wide as the wall${t !== null ? ` (${(t / 25.4).toFixed(1).replace(/\.0$/, "")} in)` : ""}, assumed`);
  if (f.bed_depth_from === "STRIP_SECTION") parts.push("bed thickness taken from the wall footing section, assumed");
  const sec = f.footing_section as { caption_wall_in?: unknown; masonry_only?: unknown } | null | undefined;
  if (sec && typeof sec === "object") {
    if (typeof sec.caption_wall_in === "number") parts.push(`section read for the wall its picture shows (its caption says ${sec.caption_wall_in} in)`);
    if (sec.masonry_only === true) parts.push("masonry steps on the bed, no reinforced footing");
  }
  if (f.upstand === true) parts.push("upstand beam: concrete above the slab, shuttered on both sides, no soffit");
  const dug = f.depth_assumed as { mm?: unknown; text?: unknown } | null | undefined;
  if (dug && typeof dug === "object" && typeof dug.mm === "number") {
    const layers = typeof f.layers === "number" ? `, ${f.layers} layers` : "";
    parts.push(`depth ${Math.round(dug.mm)} mm assumed${layers}: ${typeof dug.text === "string" ? dug.text : "not printed on the plans"}`);
  }
  if (f.depth_from === "QS_ANSWER") parts.push("bed thickness is the QS's answer");
  const ws = f.working_space as { used_mm?: unknown; qs_answer_mm?: unknown; trench_width_qs_mm?: unknown; extra_m3?: unknown } | null | undefined;
  if (ws && typeof ws === "object" && typeof ws.used_mm === "number" && typeof ws.qs_answer_mm === "number" && typeof ws.trench_width_qs_mm === "number" && typeof ws.extra_m3 === "number") {
    const inches = (mm: number) => `${(mm / 25.4).toFixed(1).replace(/\.0$/, "")} in`;
    parts.push(`working space ${inches(ws.used_mm)} a side as the workbook shows; with the QS's ${inches(ws.qs_answer_mm)} a side the trench is ${Math.round(ws.trench_width_qs_mm)} mm wide and ${ws.extra_m3.toFixed(1)} m³ more to dig`);
  }
  return parts.length ? parts.join(" · ") : null;
}

export function factLine(c: TakeoffCandidate): string {
  const f = (c.facts ?? {}) as Record<string, unknown>;
  return [setAsideText(f), factLineBase(c), steelText(f), qsText(c), sectionText(f)].filter(Boolean).join(" · ");
}

function factLineBase(c: TakeoffCandidate): string {
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
      return [len !== null ? `${len.toFixed(2)} m along ${strips ?? 0} hatched strip${strips === 1 ? "" : "s"}${cols ? `, between column faces (${cols} column${cols === 1 ? "" : "s"} taken off)` : ""}` : null, w !== null ? `${(w / 25.4).toFixed(1).replace(/\.0$/, "")} in wide` : null, depth !== null ? `${Math.round(depth)} mm deep` : "depth needed", beamSectionText(f)].filter(Boolean).join(" · ");
    }
    if (f.derived_from !== "WALLS") return "";
    return [f.beam_role === "PLINTH" ? "plinth beam" : "roof beam", len !== null ? `${len.toFixed(2)} m over ${walls ?? 0} wall${walls === 1 ? "" : "s"}` : null, t !== null ? `${(t / 25.4).toFixed(1).replace(/\.0$/, "")} in wide` : null, gaps ? `${gaps.toFixed(2)} m of it over openings` : null, depth !== null ? `${Math.round(depth)} mm deep` : "depth needed", beamSectionText(f)].filter(Boolean).join(" · ");
  }

  if (c.category === "SLAB") {
    const dims = Array.isArray(f.dims_mm) ? (f.dims_mm as number[]) : null;
    const t = num(f.thickness_mm);
    const area = num(f.area_m2);
    const choices = slabThicknessChoices(c);
    const options = choices.length > 1 ? `thickness printed as ${choices.map((o) => `${(o.mm / 25.4).toFixed(1).replace(/\.0$/, "")} in (${o.sources.map((x) => SLAB_SOURCE_TEXT[x] ?? x).join(", ")})`).join(" / ")}` : null;
    const proj = (f.projections ?? null) as { applied?: boolean; sides?: Record<string, number>; strips?: { status?: string; assumed?: boolean }[] } | null;
    const lengthAssumed = (proj?.strips ?? []).some((s) => s.status === "ADDED" && s.assumed === true);
    const gross = num(f.gross_area_m2);
    const strip = num(f.projection_area_m2);
    const sideText = proj?.sides ? Object.entries(proj.sides).map(([s, w]) => `${s.toLowerCase()} ${(w / 304.8).toFixed(1).replace(/\.0$/, "")} ft`).join(", ") : "";
    const covered = proj?.applied && gross !== null && strip !== null ? `${gross.toFixed(2)} m² with ${strip.toFixed(2)} m² of roof projection (${sideText}${lengthAssumed ? ", length of the side assumed" : ""})` : area !== null ? `${area.toFixed(2)} m² covered` : null;
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
    const n = validHeight(heights[f], f);
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

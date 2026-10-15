import type { AcceptBody, AreaGeometry, CandidateCategory, CountGeometry, LengthGeometry, Pt, TakeoffCandidate } from "../types/takeoff.types";
import { steelForAccept } from "./steel";
import type { SteelSet } from "./steel";

export const CATEGORY_ORDER: CandidateCategory[] = ["WALL", "COLUMN", "FOOTING", "BEAM", "SLAB", "LINTEL", "STAIR", "DOOR", "WINDOW", "ROOM"];

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
};

export type HeightField =
  | "wall_height_mm"
  | "column_height_mm"
  | "footing_depth_mm"
  | "slab_thickness_mm"
  | "beam_depth_mm"
  | "plinth_beam_depth_mm"
  | "excavation_depth_mm"
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
  | "stair_waist_mm";

const HEIGHT_ORDER: HeightField[] = [
  "wall_height_mm",
  "column_height_mm",
  "footing_depth_mm",
  "slab_thickness_mm",
  "beam_depth_mm",
  "plinth_beam_depth_mm",
  "excavation_depth_mm",
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
  "stair_waist_mm",
];

export type Heights = Record<HeightField, string>;
export const NO_HEIGHTS: Heights = {
  wall_height_mm: "",
  column_height_mm: "",
  footing_depth_mm: "",
  slab_thickness_mm: "",
  beam_depth_mm: "",
  plinth_beam_depth_mm: "",
  excavation_depth_mm: "",
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
  stair_waist_mm: "",
};

export const HEIGHT_LABEL: Record<HeightField, string> = {
  wall_height_mm: "Wall height (mm)",
  column_height_mm: "Column height (mm)",
  footing_depth_mm: "Footing depth (mm)",
  slab_thickness_mm: "Slab thickness (mm)",
  beam_depth_mm: "Roof beam depth (mm)",
  plinth_beam_depth_mm: "Plinth beam depth (mm)",
  excavation_depth_mm: "Excavation depth over the basement (mm)",
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
  stair_waist_mm: "Stair waist slab thickness under the steps (mm)",
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
  | "DOOR_FRAME";

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
];

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

const SLAB_SOURCE_TEXT: Record<string, string> = { PLAN_NOTE: "plan note", OTHER_SHEET: "other sheet", SECTIONS: "building sections" };

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

function foundationFields(c: Pick<TakeoffCandidate, "category" | "missing" | "facts">): HeightField[] {
  const item = foundationItem(c);
  if (item === null) return [];
  const out: HeightField[] = [];
  if (c.missing.includes("strip_width_mm")) {
    out.push((c.facts as Record<string, unknown> | null)?.strip_class === "THIN" ? "pcc_strip_width_thin_mm" : "pcc_strip_width_mm");
  }
  if (c.missing.includes("depth_mm")) {
    out.push(item === "EXCAVATION_AREA" ? "excavation_depth_mm" : item === "TRENCH" ? "trench_depth_mm" : "pcc_thickness_mm");
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
  return out;
}

export function heightFieldsFor(c: Pick<TakeoffCandidate, "category" | "missing"> & Partial<Pick<TakeoffCandidate, "notes" | "facts">>): HeightField[] {
  if (c.missing.includes("size")) return [];
  const found = foundationFields({ category: c.category, missing: c.missing, facts: c.facts ?? {} });
  if (found.length) return found;
  const one = heightFieldFor(c);
  return one === null ? [] : [one];
}

export function heightFieldFor(c: Pick<TakeoffCandidate, "category" | "missing"> & Partial<Pick<TakeoffCandidate, "notes" | "facts">>): HeightField | null {
  if (c.missing.includes("size")) return null;
  const found = foundationFields({ category: c.category, missing: c.missing, facts: c.facts ?? {} });
  if (found.length) return found[0];
  if (c.category === "WALL" && c.missing.includes("height_mm")) return "wall_height_mm";
  if (c.category === "COLUMN" && c.missing.includes("height_mm")) return "column_height_mm";
  if (c.category === "FOOTING" && c.missing.includes("depth_mm")) return "footing_depth_mm";
  if (c.category === "SLAB" && c.missing.includes("thickness_mm")) return "slab_thickness_mm";
  if (c.category === "SLAB" && slabThicknessDisputed({ category: c.category, notes: c.notes ?? [] })) return "slab_thickness_mm";
  if (c.category === "BEAM" && c.missing.includes("depth_mm")) return (c.facts as Record<string, unknown> | undefined)?.beam_role === "PLINTH" ? "plinth_beam_depth_mm" : "beam_depth_mm";
  if (c.category === "STAIR" && c.missing.includes("waist_mm")) return "stair_waist_mm";
  return null;
}

export function notMeasurable(c: Pick<TakeoffCandidate, "category" | "missing" | "status"> & Partial<Pick<TakeoffCandidate, "facts">>): boolean {
  return (c.category === "BEAM" && !isWallBeam({ category: c.category, facts: c.facts ?? {} })) || c.missing.includes("size") || c.status === "INVALID";
}

export type Level = "high" | "medium" | "low";

export function confidenceLevel(confidence: string | number): Level {
  const n = Number(confidence);
  if (!Number.isFinite(n) || n < 0.65) return "low";
  return n >= 0.85 ? "high" : "medium";
}

export function groupByCategory(list: TakeoffCandidate[]): Array<{ category: CandidateCategory; items: TakeoffCandidate[] }> {
  const out: Array<{ category: CandidateCategory; items: TakeoffCandidate[] }> = [];
  for (const category of CATEGORY_ORDER) {
    const items = list.filter((c) => c.category === category);
    if (items.length) out.push({ category, items });
  }
  return out;
}

export function neededHeights(list: TakeoffCandidate[]): HeightField[] {
  const set = new Set<HeightField>();
  for (const c of list) {
    for (const f of heightFieldsFor(c)) set.add(f);
  }
  return HEIGHT_ORDER.filter((f) => set.has(f));
}

export function validHeight(text: string): number | null {
  const n = Number(text.trim().replace(/,/g, ""));
  return Number.isFinite(n) && n >= 75 && n <= 20000 ? n : null;
}

export function blockedByHeight(list: TakeoffCandidate[], ids: Set<string>, typed: Heights): TakeoffCandidate[] {
  return list.filter((c) => {
    if (!ids.has(c.id)) return false;
    return heightFieldsFor(c).some((f) => validHeight(typed[f]) === null);
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
    return [count !== null ? `${count} door${count === 1 ? "" : "s"}` : null, size ? `${Math.round(size[0])}×${Math.round(size[1])} mm` : null, f.frame_class === "THIN" ? "in thin walls" : "in thick walls", width !== null ? `${Math.round(width)} mm frame` : "frame width needed"].filter(Boolean).join(" · ");
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

export function factLine(c: TakeoffCandidate): string {
  const f = c.facts as Record<string, unknown>;
  const num = (v: unknown) => (typeof v === "number" ? v : null);
  const item = foundationItem(c);
  if (item !== null) return foundationLine(c, item);
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
    return [covered, dims ? `${Math.round(dims[0])}×${Math.round(dims[1])} mm printed` : "size not printed", t !== null ? `${Math.round(t)} mm thick` : "thickness needed", options].filter(Boolean).join(" · ");
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
    return [way, steps !== null ? `${steps} steps` : null, inch(f.riser_mm) ? `riser ${inch(f.riser_mm)} in` : null, inch(f.tread_mm) ? `tread ${inch(f.tread_mm)} in` : null, width !== null ? `${Math.round(width)} mm wide` : "size needed", waist !== null ? `waist ${Math.round(waist)} mm ${f.waist_source === "PRINTED" ? "printed" : "assumed"}` : c.missing.includes("waist_mm") ? "waist slab to type" : null].filter(Boolean).join(" · ");
  }

  const sched = Array.isArray(f.size_schedule_mm) ? (f.size_schedule_mm as number[]) : null;
  const drawn = Array.isArray(f.size_drawn_mm) ? (f.size_drawn_mm as number[]) : null;

  const parts: string[] = [];
  if (sched) parts.push(`schedule ${Math.round(sched[0])}×${Math.round(sched[1])}`);
  if (drawn) parts.push(`drawn ${Math.round(drawn[0])}×${Math.round(drawn[1])}`);
  return parts.join(" · ");
}
/** The body of an accept call: only the heights that read as numbers, only the work items typed, and the steel typed for the members being accepted. */
export function buildAcceptBody(ids: string[], heights: Heights, workItems: Record<string, string>, steel: Record<string, SteelSet>): AcceptBody {
  const body: AcceptBody = { ids };
  for (const f of HEIGHT_ORDER) {
    const n = validHeight(heights[f]);
    if (n !== null) (body as unknown as Record<string, number>)[f] = n;
  }
  const items = Object.fromEntries(ids.map((id) => [id, (workItems[id] ?? "").trim()]).filter(([, v]) => v !== ""));
  if (Object.keys(items).length) body.work_items = items;
  const typed = steelForAccept(ids, steel);
  if (typed) body.steel = typed;
  return body;
}

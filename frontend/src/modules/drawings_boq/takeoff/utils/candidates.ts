import type { AreaGeometry, CandidateCategory, CountGeometry, LengthGeometry, Pt, TakeoffCandidate } from "../types/takeoff.types";

export const CATEGORY_ORDER: CandidateCategory[] = ["WALL", "COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW", "ROOM"];

export const CATEGORY_TEXT: Record<CandidateCategory, { one: string; many: string }> = {
  WALL: { one: "Wall", many: "Walls" },
  COLUMN: { one: "Column", many: "Columns" },
  FOOTING: { one: "Footing", many: "Footings" },
  BEAM: { one: "Beam", many: "Beams" },
  DOOR: { one: "Door", many: "Doors" },
  WINDOW: { one: "Window", many: "Windows" },
  ROOM: { one: "Room", many: "Rooms" },
};

export type HeightField = "wall_height_mm" | "column_height_mm" | "footing_depth_mm";

export type Heights = Record<HeightField, string>;
export const NO_HEIGHTS: Heights = { wall_height_mm: "", column_height_mm: "", footing_depth_mm: "" };

export const HEIGHT_LABEL: Record<HeightField, string> = {
  wall_height_mm: "Wall height (mm)",
  column_height_mm: "Column height (mm)",
  footing_depth_mm: "Footing depth (mm)",
};

export function heightFieldFor(c: Pick<TakeoffCandidate, "category" | "missing">): HeightField | null {
  if (c.missing.includes("size")) return null;
  if (c.category === "WALL" && c.missing.includes("height_mm")) return "wall_height_mm";
  if (c.category === "COLUMN" && c.missing.includes("height_mm")) return "column_height_mm";
  if (c.category === "FOOTING" && c.missing.includes("depth_mm")) return "footing_depth_mm";
  return null;
}

export function notMeasurable(c: Pick<TakeoffCandidate, "category" | "missing" | "status">): boolean {
  return c.category === "BEAM" || c.missing.includes("size") || c.status === "INVALID";
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
    const f = heightFieldFor(c);
    if (f) set.add(f);
  }
  return (["wall_height_mm", "column_height_mm", "footing_depth_mm"] as HeightField[]).filter((f) => set.has(f));
}

export function validHeight(text: string): number | null {
  const n = Number(text.trim().replace(/,/g, ""));
  return Number.isFinite(n) && n >= 100 && n <= 20000 ? n : null;
}

export function blockedByHeight(list: TakeoffCandidate[], ids: Set<string>, typed: Heights): TakeoffCandidate[] {
  return list.filter((c) => {
    if (!ids.has(c.id)) return false;
    const f = heightFieldFor(c);
    return f !== null && validHeight(typed[f]) === null;
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

export function factLine(c: TakeoffCandidate): string {
  const f = c.facts as Record<string, unknown>;
  const num = (v: unknown) => (typeof v === "number" ? v : null);
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

  const sched = Array.isArray(f.size_schedule_mm) ? (f.size_schedule_mm as number[]) : null;
  const drawn = Array.isArray(f.size_drawn_mm) ? (f.size_drawn_mm as number[]) : null;
  const parts: string[] = [];
  if (sched) parts.push(`schedule ${Math.round(sched[0])}×${Math.round(sched[1])}`);
  if (drawn) parts.push(`drawn ${Math.round(drawn[0])}×${Math.round(drawn[1])}`);
  return parts.join(" · ");
}
import type { MarkRow } from "../types/takeoff.types";

export const MARK_CATEGORIES = ["COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW", "WALL_SECTION", "SECTION_REF", "SLAB_PANEL", "UNKNOWN"] as const;

const CATEGORY_TEXT: Record<string, string> = {
  COLUMN: "Column", FOOTING: "Footing", BEAM: "Beam", DOOR: "Door", WINDOW: "Window / ventilator", WALL_SECTION: "Wall section (not counted)",
  SECTION_REF: "Section label (not counted)", SLAB_PANEL: "Slab panel (not counted)", UNKNOWN: "Nothing known (not counted)",
};

const BASIS_TEXT: Record<string, string> = {
  SECTION_TITLE: "A section title says so", SCHEDULE: "A schedule says so", LEGEND: "A legend says so", SECTION_SYMBOL: "Printed beside a section-cut symbol",
  DEFAULT: "Read by its letters only", PERSON: "Set by a person",
};

export function categoryText(category: string): string {
  return CATEGORY_TEXT[category] ?? category;
}

export function basisText(basis: string): string {
  return BASIS_TEXT[basis] ?? basis;
}

export function isCounted(category: string): boolean {
  return ["COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW"].includes(category);
}

export function wallText(row: MarkRow): string | null {
  const mm = row.params?.wall_thickness_mm;
  if (typeof mm !== "number") return null;
  const outside = row.params?.exterior === true;
  return `${Math.round(mm)} mm, ${outside ? "outside" : "inside"} wall`;
}

export function markSource(row: MarkRow): string | null {
  if (row.page_no == null) return null;
  const name = row.drawing_name ? row.drawing_name.replace(/\.pdf$/i, "") : "";
  const short = name.length > 26 ? `${name.slice(0, 24)}…` : name;
  return short ? `${short} · p.${row.page_no}` : `p.${row.page_no}`;
}

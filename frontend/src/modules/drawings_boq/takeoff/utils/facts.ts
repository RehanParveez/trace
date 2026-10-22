import type { DrawingFact, DrawingFactConflict, DrawingFacts, FactKind } from "../types/takeoff.types";

const MM_INCH = 25.4;

function frac8(rest: number): string {
  const g = rest % 4 === 0 ? 4 : rest % 2 === 0 ? 2 : 1;
  return `${rest / g}/${8 / g}`;
}

export function mmToInchText(mm: number): string {
  const eighths = Math.round((mm / MM_INCH) * 8);
  const whole = Math.floor(eighths / 8);
  const rest = eighths % 8;
  if (rest === 0) return `${whole}"`;
  return whole === 0 ? `${frac8(rest)}"` : `${whole} ${frac8(rest)}"`;
}

export function mmToFeetInches(mm: number): string {
  const eighths = Math.round((mm / MM_INCH) * 8);
  const feet = Math.floor(eighths / 96);
  const left = eighths - feet * 96;
  const whole = Math.floor(left / 8);
  const rest = left % 8;
  return `${feet}'-${whole}${rest === 0 ? "" : ` ${frac8(rest)}`}"`;
}

export function mmText(mm: number): string {
  return `${Math.round(mm).toLocaleString("en-US")} mm`;
}

export const FACT_ORDER: FactKind[] = ["SLAB_THICKNESS", "RCC_WALL_THICKNESS", "BRICK_COLUMN", "CONCRETE_CLASS", "STEEL_GRADE", "CLEAR_COVER", "BEARING_CAPACITY", "PLASTER_THICKNESS", "FILL_LAYER", "SOIL_STABILISATION", "STAIR_WIDTH"];

export const FACT_TITLE: Record<FactKind, string> = {
  SLAB_THICKNESS: "Slab thickness",
  RCC_WALL_THICKNESS: "RCC wall thickness",
  BRICK_COLUMN: "Brick columns",
  CONCRETE_CLASS: "Concrete",
  STEEL_GRADE: "Steel",
  CLEAR_COVER: "Clear cover",
  BEARING_CAPACITY: "Soil bearing capacity",
  PLASTER_THICKNESS: "Plaster",
  FILL_LAYER: "Filling",
  SOIL_STABILISATION: "Soil stabilisation",
  STAIR_WIDTH: "Stair width",
};

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function inchAndMm(mm: number | null | undefined): string {
  return mm == null ? "" : `${mmToInchText(mm)} (${mmText(mm)})`;
}

export function factDetail(f: DrawingFact): string {
  switch (f.kind) {
    case "SLAB_THICKNESS":
      return `${cap(f.scope ?? "slab")}: ${inchAndMm(f.value_mm)}`;
    case "RCC_WALL_THICKNESS":
      return inchAndMm(f.value_mm);
    case "BRICK_COLUMN":
      return f.value_mm != null && f.value2_mm != null ? `${mmToInchText(f.value_mm)} × ${mmToInchText(f.value2_mm)}` : "";
    case "CONCRETE_CLASS":
      return `Class ${f.concrete_class ?? "?"}${f.mix ? ` (${f.mix})` : ""}${f.scope ? ` · ${f.scope}` : ""}`;
    case "STEEL_GRADE":
      return `Grade ${f.grade ?? "?"}${f.scope ? ` · ${f.scope}` : ""}`;
    case "CLEAR_COVER":
      return `${cap(f.scope ?? "")} ${inchAndMm(f.value_mm)}${f.where ? ` · ${f.where}` : ""}`.trim();
    case "BEARING_CAPACITY":
      return f.value != null ? `${f.value} ${f.unit ?? ""}`.trim() : "";
    case "PLASTER_THICKNESS":
      return inchAndMm(f.value_mm);
    case "FILL_LAYER":
      return `${inchAndMm(f.value_mm)} per compacted layer`;
    case "SOIL_STABILISATION":
      return soilNoteText(f);
    case "STAIR_WIDTH":
      return f.value_mm != null ? `${mmToFeetInches(f.value_mm)} (${mmText(f.value_mm)})` : "";
    default:
      return f.text;
  }
}

export function soilNoteText(f: DrawingFact): string {
  const pct = f.cement_pct != null ? `${f.cement_pct} % cement` : "cement";
  const depth = f.value_mm != null ? ` · ${inchAndMm(f.value_mm)} deep` : "";
  return `${pct}${f.loose ? " · loose soil only" : ""}${depth}`;
}

export function pagesText(pages: number[]): string {
  return [...pages].sort((a, b) => a - b).join(", ");
}

export interface FactGroup { kind: FactKind; facts: DrawingFact[] }

export function groupFacts(facts: DrawingFacts | undefined): FactGroup[] {
  if (!facts) return [];
  return FACT_ORDER
    .map((kind) => ({ kind, facts: facts.items.filter((f) => f.kind === kind) }))
    .filter((g) => g.facts.length > 0);
}

export function conflictValueText(v: DrawingFactConflict["values"][number]): string {
  if (v.value_mm != null) return inchAndMm(v.value_mm);
  if (v.value != null) return `${v.value} ${v.unit ?? ""}`.trim();
  return "";
}

export function floorToFloor(facts: DrawingFacts | undefined): number | null {
  const mm = facts?.ladder?.typical_floor_to_floor_mm;
  return mm != null && mm > 0 ? mm : null;
}

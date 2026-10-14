import type { DrawingFacts, SheetView, StructureLevel, StructureMark } from "../types/takeoff.types";
import { mmText, mmToFeetInches } from "./facts";

const INCH_MM = 25.4;

export function lengthText(mm: number): string {
  return mm < 24 * INCH_MM ? `${Math.round((mm / INCH_MM) * 10) / 10}"` : mmToFeetInches(mm);
}

export function sectionText(size: Array<number | null> | null | undefined): string {
  const [a, b] = size ?? [];
  if (a == null || b == null) return "";
  const one = Math.max(a, b) < 24 * INCH_MM ? (mm: number) => `${Math.round((mm / INCH_MM) * 10) / 10}"` : mmToFeetInches;
  return `${one(a)} × ${one(b)} (${Math.round(a)} × ${Math.round(b)} mm)`;
}

export function markText(m: StructureMark): string {
  const name = m.tag && m.tag.trim() ? m.tag : "—";
  const size = sectionText(m.size_mm);
  return size ? `${name} ×${m.count} · ${size}` : `${name} ×${m.count}`;
}

export function marksText(marks: StructureMark[] | undefined): string {
  return (marks ?? []).map(markText).join("; ");
}

export function levelHasStructure(l: StructureLevel): boolean {
  return l.columns + l.footings + l.beams > 0 || l.slab_panels > 0;
}

export function structureLevels(facts: DrawingFacts | undefined): StructureLevel[] {
  return (facts?.structure ?? []).filter(levelHasStructure);
}

export function planViews(facts: DrawingFacts | undefined): SheetView[] {
  return (facts?.views ?? []).filter((v) => v.structural);
}

export function hasStructure(facts: DrawingFacts | undefined): boolean {
  return structureLevels(facts).length > 0 || planViews(facts).length > 0;
}

export function slabParts(l: Pick<StructureLevel, "slab_panels" | "slab_thickness_mm">): { panels: number; thickness: string | null } {
  return { panels: l.slab_panels, thickness: l.slab_thickness_mm ? `${lengthText(l.slab_thickness_mm)} (${mmText(l.slab_thickness_mm)})` : null };
}

export function scaleText(v: SheetView): string | null {
  return v.scale_ratio ? `1:${Math.round(v.scale_ratio)}` : null;
}

export function markNeedsSize(m: StructureMark): boolean {
  return !m.size_mm || m.size_mm[0] == null || m.size_mm[1] == null;
}

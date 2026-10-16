import type { TakeoffCandidate } from "../types/takeoff.types";

export interface SectionOption { mark: string; depth_mm: number | null; steel_text: string | null }

type Facts = Record<string, unknown>;
const facts = (c: Partial<Pick<TakeoffCandidate, "facts">>): Facts => (c.facts as Facts | null | undefined) ?? {};

export function isNeckColumn(c: Pick<TakeoffCandidate, "category"> & Partial<Pick<TakeoffCandidate, "facts">>): boolean {
  return c.category === "COLUMN" && typeof facts(c).neck_of === "string";
}

export function isTankWall(c: Pick<TakeoffCandidate, "category"> & Partial<Pick<TakeoffCandidate, "facts">>): boolean {
  return c.category === "WALL" && facts(c).enclosure === "TANK";
}

export function sectionOptions(c: Pick<TakeoffCandidate, "category" | "facts">): SectionOption[] {
  if (c.category !== "BEAM" || facts(c).derived_from !== "WALLS") return [];
  const raw = facts(c).section_options;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((o): o is Record<string, unknown> => typeof o === "object" && o !== null && typeof (o as Record<string, unknown>).mark === "string")
    .map((o) => ({
      mark: o.mark as string,
      depth_mm: typeof o.depth_mm === "number" ? o.depth_mm : null,
      steel_text: typeof o.steel_text === "string" ? o.steel_text : null,
    }));
}

const inchText = (mm: number) => `${Math.round((mm / 25.4) * 10) / 10}`.replace(/\.0$/, "");

export function sectionLabel(o: SectionOption): string {
  return [o.mark, o.depth_mm != null ? `${inchText(o.depth_mm)} in deep` : "depth not read", o.steel_text].filter(Boolean).join(" · ");
}

export function offersSectionChoice(c: Pick<TakeoffCandidate, "category" | "facts" | "missing">): boolean {
  return c.missing.includes("depth_mm") && sectionOptions(c).length > 0;
}

export function pickGivesDepth(c: Pick<TakeoffCandidate, "category" | "facts" | "id">, picks: Record<string, string> | undefined): boolean {
  const mark = picks?.[c.id];
  if (!mark) return false;
  return sectionOptions(c).some((o) => o.mark === mark && o.depth_mm != null);
}

export function isTankItem(c: Pick<TakeoffCandidate, "category" | "facts">): boolean {
  const kind = facts(c).site_kind;
  return c.category === "SITE" && (kind === "OHWT" || kind === "UGWT" || kind === "SEPTIC");
}

export function sizeTextToMm(text: string): number | null {
  const t = text.replace(/\s+/g, "").replace(/[’′]/g, "'").replace(/[”″]/g, '"');
  const ft = /^(\d{1,2})'-?(\d{1,2})?"?$/.exec(t);
  if (ft && (t.includes("'") )) return Math.round(((Number(ft[1]) * 12 + Number(ft[2] ?? 0)) * 25.4) * 10) / 10;
  const inch = /^(\d{1,3})"$/.exec(t);
  if (inch) return Math.round(Number(inch[1]) * 25.4 * 10) / 10;
  return null;
}

export interface SizeChoice { text: string; mm: number }

export function tankSizeChoices(list: Array<Pick<TakeoffCandidate, "category" | "facts">>): SizeChoice[] {
  const seen = new Map<number, string>();
  for (const c of list) {
    if (!isTankWall(c) && !isTankItem(c)) continue;
    const drawings = facts(c).tank_drawings;
    if (!Array.isArray(drawings)) continue;
    for (const d of drawings) {
      const sizes = (d as Record<string, unknown>)?.sizes;
      if (!Array.isArray(sizes)) continue;
      for (const s of sizes) {
        const mm = typeof s === "string" ? sizeTextToMm(s) : null;
        if (mm !== null && mm >= 75 && !seen.has(mm)) seen.set(mm, s as string);
      }
    }
  }
  return [...seen.entries()].sort((a, b) => a[0] - b[0]).map(([mm, text]) => ({ text, mm }));
}
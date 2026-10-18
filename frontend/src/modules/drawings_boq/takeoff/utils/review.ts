import type { ConflictValue, LinkGroup, LinkItem, LinkStatus, SteelConventions, SteelFamily, ValueConflict } from "../types/review.types";

export const POLICY_KINDS = ["SLAB_THICKNESS", "BEAM_SECTION"] as const;
export const POLICY_OPTIONS: Array<{ key: string; label: string }> = [
  { key: "STRUCTURAL", label: "Structural sheet" },
  { key: "ARCHITECTURAL", label: "Architectural sheet" },
  { key: "LARGER", label: "Larger quantity" },
  { key: "SMALLER", label: "Smaller quantity" },
  { key: "AS_READ", label: "As read (no policy)" },
];
export const KIND_LABEL: Record<string, string> = {
  SLAB_THICKNESS: "Slab thickness",
  BEAM_SECTION: "Beam section",
  SOURCE_COUNT: "Count differs between the two sheets of a floor",
};
export const DISCIPLINE_LABEL: Record<string, string> = { STRUCTURAL: "Structural", ARCHITECTURAL: "Architectural", UNKNOWN: "Other sheet" };
export const BY_LABEL: Record<string, string> = { CHOSEN: "your choice", POLICY: "the policy", AS_READ: "as the reader took it" };

export const LINK_GROUP_LABEL: Record<string, string> = {
  BEAM: "Beams", PLINTH_BEAM: "Plinth beams", FOOTING_STRIP: "Wall strip footings", FOOTING_PAD: "Pad footings", NECK_COLUMN: "Neck columns", COLUMN: "Columns", TANK: "Tanks",
};
export const LINK_STATUS_LABEL: Record<LinkStatus, string> = { LINKED: "Linked", CHOICE: "Choose a section", PARTLY: "Partly", NOT_LINKED: "Not linked" };
export const LINK_REASON: Record<string, string> = {
  SECTIONS_LISTED_NOT_TIED_TO_WALLS: "The drawing lists sections but does not say which beam takes which.",
  NO_SECTION_PRINTED_FOR_THIS_BEAM: "No section is printed for this beam.",
  NO_USABLE_FOOTING_SECTION_FOR_THIS_WALL: "No footing section on the drawing could be read for this wall.",
  FOOTING_DEPTH_NOT_PRINTED_AS_A_NUMBER: "The footing depth is drawn as a letter, not a number.",
  NECK_HEIGHT_FOLLOWS_FOOTING_DEPTH: "The neck column's height follows the footing depth, which is not known yet.",
  NO_DETAIL_FOUND_FOR_THIS_MARK: "No detail was found for this column mark.",
  TANK_DRAWINGS_NOT_USED_FOR_SIZES: "The tank drawings are listed but are not to scale, so type the sizes.",
  UNKNOWN: "Not enough on the drawing to link this.",
};
export const NEED_LABEL: Record<string, string> = {
  depth_mm: "depth", width_mm: "width", length_mm: "length", height_mm: "height", thickness_mm: "thickness",
};

export const STEEL_STATUS_LABEL: Record<string, string> = {
  BELOW_RANGE: "Below the usual range", IN_RANGE: "In the usual range", ABOVE_RANGE: "Above the usual range",
};
export const STEEL_FIELDS: Array<{ key: keyof SteelConventions; label: string; unit: string }> = [
  { key: "cover_mm", label: "Cover", unit: "mm" },
  { key: "hook_dia", label: "Hook (× bar diameter)", unit: "×" },
  { key: "lap_dia", label: "Lap (× bar diameter)", unit: "×" },
  { key: "anchor_dia", label: "Anchorage (× bar diameter)", unit: "×" },
  { key: "wastage_pct", label: "Wastage", unit: "%" },
];

const nf = (n: number, digits: number) => n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function mmText(mm: number | null | undefined): string {
  if (mm === null || mm === undefined || !Number.isFinite(mm)) return "";
  return `${nf(mm, Number.isInteger(mm) ? 0 : 1)} mm`;
}

export function quantityText(c: ValueConflict, v: ConflictValue): string {
  if (v.quantity === null || v.quantity === undefined) return "";
  return c.unit === "nos" ? `${nf(v.quantity, 0)} nos` : `${nf(v.quantity, 2)} ${c.unit}`;
}

export function deltaText(c: ValueConflict, v: ConflictValue): string {
  if (v.delta === null || v.delta === undefined || v.governing || Math.abs(v.delta) < 0.005) return "";
  const sign = v.delta > 0 ? "+" : "−";
  const abs = Math.abs(v.delta);
  const q = c.unit === "nos" ? `${nf(abs, 0)} nos` : `${nf(abs, 2)} ${c.unit}`;
  const pct = v.delta_pct === null || v.delta_pct === undefined ? "" : ` (${v.delta_pct > 0 ? "+" : "−"}${nf(Math.abs(v.delta_pct), 1)}%)`;
  return `${sign}${q}${pct}`;
}

export function sourcesText(v: ConflictValue): string {
  const parts = (v.sources ?? []).map((s) => {
    const who = DISCIPLINE_LABEL[s.discipline] ?? String(s.discipline);
    return s.page_no ? `${who}, page ${s.page_no}` : who;
  });
  return Array.from(new Set(parts)).join(" · ");
}

export function choiceOf(v: ConflictValue): number | null {
  if (v.value_mm !== null && v.value_mm !== undefined) return v.value_mm;
  if (v.count !== null && v.count !== undefined) return v.count;
  return null;
}

export function canChoose(c: ValueConflict): boolean {
  return c.decision === "NEW";
}

export function conflictsByKind(list: ValueConflict[]): Array<{ kind: string; items: ValueConflict[] }> {
  const order = ["SLAB_THICKNESS", "BEAM_SECTION", "SOURCE_COUNT"];
  const out = new Map<string, ValueConflict[]>();
  for (const c of list) out.set(c.kind, [...(out.get(c.kind) ?? []), c]);
  return order.filter((k) => out.has(k)).map((k) => ({ kind: k, items: out.get(k) as ValueConflict[] }));
}

export function undecided(c: ValueConflict): boolean {
  return c.decision === "NEW" && c.governing_by !== "CHOSEN";
}

export function linkTone(status: LinkStatus): "green" | "gold" | "red" | "blue" {
  return status === "LINKED" ? "green" : status === "NOT_LINKED" ? "red" : status === "PARTLY" ? "gold" : "blue";
}

export function groupLine(g: LinkGroup): string {
  const open = g.total - g.linked;
  return open === 0 ? `${g.linked} of ${g.total} linked` : `${g.linked} of ${g.total} linked · ${open} open`;
}

export function needsText(item: LinkItem): string {
  return item.needs.map((n) => NEED_LABEL[n] ?? n).join(", ");
}

export function steelTone(f: SteelFamily): "green" | "gold" | "red" | "blue" {
  return f.status === "IN_RANGE" ? "green" : f.status === null ? "blue" : "gold";
}

export function kgText(kg: number): string {
  return kg >= 1000 ? `${nf(kg / 1000, 2)} t` : `${nf(kg, 0)} kg`;
}

export function rangeText(f: SteelFamily): string {
  return f.range ? `${nf(f.range[0], 0)}–${nf(f.range[1], 0)} kg/m³` : "";
}

export function conventionsFromInputs(inputs: Record<string, string>): { conventions: Partial<SteelConventions>; bad: string[] } {
  const conventions: Partial<SteelConventions> = {};
  const bad: string[] = [];
  for (const f of STEEL_FIELDS) {
    const raw = (inputs[f.key] ?? "").trim();
    if (!raw) continue;
    const n = Number(raw.replace(",", "."));
    if (!Number.isFinite(n) || n < 0 || (f.key === "wastage_pct" && n > 50) || (f.key === "cover_mm" && n > 150)) bad.push(f.key);
    else conventions[f.key] = n;
  }
  return { conventions, bad };
}

export function reviewOpenCount(conflictsUndecided: number, linksOpen: number): number {
  return Math.max(0, conflictsUndecided) + Math.max(0, linksOpen);
}

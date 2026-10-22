import type { GradeMember, GradesConflict, GradesReport, PlasterInfo, SoilInfo } from "../types/grades.types";

const MM_IN = 25.4;
const PARAM_WORDS: Record<string, string> = {
  plaster_thickness_mm: "plaster thickness",
  soil_stab_cement_pct: "cement for the soil",
  soil_stab_depth_mm: "depth of the stabilised soil",
};

export function inchText(mm: number | null | undefined): string {
  if (mm === null || mm === undefined || !Number.isFinite(mm)) return "";
  return `${Math.round((mm / MM_IN) * 100) / 100}"`;
}

export function pagesText(pages: number[] | null | undefined): string {
  const p = [...(pages ?? [])].sort((a, b) => a - b);
  if (!p.length) return "";
  return `${p.length === 1 ? "sheet" : "sheets"} ${p.join(", ")}`;
}

export function concreteText(m: GradeMember): string {
  if (m.concrete_clash.length) return `Two mixes are printed (${m.concrete_clash.join(" and ")}): none is given`;
  if (!m.concrete) return "";
  const klass = m.concrete.class ? `Class ${m.concrete.class} ` : "";
  return `${klass}${m.concrete.mix}`;
}

export function steelText(m: GradeMember): string {
  if (m.steel_clash.length) return `Two grades are printed (${m.steel_clash.join(" and ")}): none is given`;
  return m.steel ? m.steel.label : "";
}

export function noteSource(m: GradeMember): string {
  const bits: string[] = [];
  if (m.concrete) bits.push(`concrete: "${m.concrete.scope || "all RCC work"}" ${pagesText(m.concrete.pages)}`.trim());
  if (m.steel) bits.push(`steel: "${m.steel.scope || "all RCC work"}" ${pagesText(m.steel.pages)}`.trim());
  return bits.join(" · ");
}

export function memberStatus(m: GradeMember): string {
  if (!m.measured) return m.found ? `${m.found} found, none measured yet` : "";
  const bits = [`${m.measured} measured`];
  if (m.stamped) bits.push(`${m.stamped} with the printed mix`);
  if (m.typed) bits.push(`${m.typed} with a grade you typed`);
  if (m.open) bits.push(`${m.open} can take it`);
  return bits.join(", ");
}

export function plasterText(p: PlasterInfo | null | undefined): string {
  if (!p || p.thickness_mm === null || p.thickness_mm === undefined) return "";
  const where = pagesText(p.note?.pages);
  return `${p.thickness_mm} mm (${inchText(p.thickness_mm)}) is printed${where ? `, ${where}` : ""}. The mortar behind the plaster is added to the bill at this thickness.`;
}

export function soilText(s: SoilInfo | null | undefined): string[] {
  if (!s) return [];
  const out: string[] = [];
  const first = s.notes[0];
  const pages = pagesText(first?.pages);
  out.push(`Soil note${pages ? ` (${pages})` : ""}: ${s.cement_pct !== null ? `${s.cement_pct} % cement` : "cement percentage not agreed between notes"}${first?.loose_only ? ", for loose soil only" : ""}.`);
  out.push(s.depth_mm !== null && s.depth_mm !== undefined
    ? `Layer depth printed: ${s.depth_mm} mm (${inchText(s.depth_mm)}).`
    : "No depth is printed, so type the depth in the site assumptions before this can be measured.");
  out.push("Nothing is measured until you switch soil stabilisation on in the site assumptions: whether the soil is loose is found on site.");
  return out;
}

export function conflictText(c: GradesConflict): string {
  const values = (c.values ?? []).map((v) => v.value_mm ?? v.value).filter((v) => v !== undefined && v !== null);
  return `Two different values are printed for the ${PARAM_WORDS[c.param] ?? c.param}${values.length ? ` (${values.join(" and ")})` : ""}: none is used.`;
}

export function ourConflicts(r: GradesReport | undefined): GradesConflict[] {
  return (r?.conflicts ?? []).filter((c) => c.param in PARAM_WORDS);
}

export function summaryLine(r: GradesReport | undefined): string {
  if (!r) return "";
  const s = r.summary ?? {};
  const parts: string[] = [];
  const c = s.concrete_notes ?? 0;
  const st = s.steel_notes ?? 0;
  if (c) parts.push(`${c} concrete note${c === 1 ? "" : "s"}`);
  if (st) parts.push(`${st} steel note${st === 1 ? "" : "s"}`);
  if (r.plaster?.thickness_mm != null) parts.push("plaster thickness");
  if (r.soil) parts.push("soil note");
  if (s.open) parts.push(`${s.open} measured member${s.open === 1 ? "" : "s"} can take the printed mix`);
  if (s.clashes) parts.push(`${s.clashes} clash${s.clashes === 1 ? "" : "es"}`);
  return parts.join(" · ");
}

export function isEmpty(r: GradesReport | undefined): boolean {
  if (!r) return true;
  return !r.concrete.length && !r.steel.length && r.plaster?.thickness_mm == null && !r.soil && !ourConflicts(r).length;
}

export function canStamp(r: GradesReport | undefined): boolean {
  return (r?.summary?.open ?? 0) > 0;
}

export function canUnstamp(r: GradesReport | undefined): boolean {
  return (r?.summary?.stamped ?? 0) > 0;
}

export function confirmedNote(r: GradesReport | undefined): string {
  const n = r?.summary?.confirmed_open ?? 0;
  return n ? `${n} of them ${n === 1 ? "is" : "are"} confirmed. They are left alone unless you tick the box, and then they go back to draft.` : "";
}

export function changedText(n: number, kind: "stamp" | "unstamp"): string {
  if (!n) return kind === "stamp" ? "No measurement needed the printed mix." : "Nothing to take back.";
  const what = `${n} measured member${n === 1 ? "" : "s"}`;
  return kind === "stamp" ? `The printed mix was given to ${what}.` : `The printed mix was taken back from ${what}.`;
}
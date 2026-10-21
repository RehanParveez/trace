import type { BeamPerMetre, ColumnPerPiece, DepthGap, DepthOption, DetailDecision, DetailOnlyBeam, DetailOnlyColumn, DetailOnlyReport, PlaceProposal } from "../types/detailOnly.types";
import type { ReadingGapsMark } from "../../types/readingGaps.types";

export const DETAIL_ONLY_COLOUR = "#8a5cc2";
export const MAX_OVERLAY_MARKS = 200;

const MM_IN = 25.4;

export function inches(mm: number | null | undefined): string {
  if (mm === null || mm === undefined || !Number.isFinite(mm)) return "—";
  return `${Math.round((mm / MM_IN) * 10) / 10}"`;
}

function range(v: number[] | null | undefined, digits: number, unit: string): string {
  if (!v || v.length < 2 || !Number.isFinite(v[0]) || !Number.isFinite(v[1])) return "";
  const a = v[0].toFixed(digits);
  const b = v[1].toFixed(digits);
  return a === b ? `${a} ${unit}` : `${a} to ${b} ${unit}`;
}

export function sizeText(size: number[] | null | undefined): string {
  if (!size || size.length < 2) return "size not read";
  return `${inches(size[0])} × ${inches(size[1])}`;
}

export function perPieceText(p: ColumnPerPiece | null | undefined): string {
  if (!p) return "No size was read from the detail, so no quantity can be worked out.";
  const concrete = range(p.concrete_m3, 3, "m³");
  const form = range(p.formwork_m2, 2, "m²");
  if (!concrete) return `One column: ${p.section_m2.toFixed(3)} m² section; no column height was read on the plans, so no volume.`;
  return `One column at the heights read on the plans: ${concrete} concrete, ${form} formwork before shared faces.`;
}

export function perMetreText(p: BeamPerMetre | null | undefined, depthRead: boolean): string {
  if (!p) return depthRead ? "The width was not read, so no quantity can be worked out." : "The depth was not read from the section, so no quantity can be worked out.";
  return `One metre of this beam: ${p.concrete_m3.toFixed(3)} m³ concrete, ${p.formwork_m2.toFixed(2)} m² formwork before the slab and shared faces.`;
}

export function pagesText(pages: number[]): string {
  if (!pages.length) return "";
  return `${pages.length === 1 ? "sheet" : "sheets"} ${pages.join(", ")}`;
}

export function proposalText(p: PlaceProposal): string {
  const where = p.page_no ? `Sheet ${p.page_no}` : "A sheet";
  const level = p.level ? ` · ${p.level.toLowerCase()}` : "";
  return `${where}${level}: ${p.count} shape${p.count === 1 ? "" : "s"} of ${sizeText(p.size_mm)} with no mark`;
}

export function optionText(o: DepthOption): string {
  return `${inches(o.depth_mm)} (printed for ${o.marks.join(", ")})`;
}

export function stakeText(g: DepthGap): string | null {
  if (!g.stake) return null;
  const c = g.stake.concrete_m3;
  const span = c.length >= 2 && c[0] !== c[1] ? `${c[0].toFixed(2)} to ${c[1].toFixed(2)} m³` : `${(c[0] ?? 0).toFixed(2)} m³`;
  return `${g.stake.length_m.toFixed(1)} m of ${inches(g.stake.width_mm)}-wide beam: ${span} of concrete depending on the depth.`;
}

export function gapText(g: DepthGap): string {
  const where = g.has_section ? "its section prints no depth that could be read" : "no section of this mark was found";
  return `${g.mark}: ${where}`;
}

export function decisionText(d: DetailDecision): string {
  const where = d.page_no ? ` (sheet ${d.page_no})` : "";
  if (d.kind === "COLUMN_MARK") return d.applied ? `Unmarked shapes are ${d.mark}${where}` : `${d.mark} was chosen for shapes that no longer offer it${where}`;
  return d.applied ? `Beams ${d.mark} take a depth of ${inches(d.value_mm)}` : `A depth of ${inches(d.value_mm)} was chosen for ${d.mark}; no beam takes it now`;
}

export function summaryLine(r: DetailOnlyReport | undefined): string {
  const s = r?.summary ?? {};
  const n = s.detail_only ?? 0;
  const g = s.depth_gaps ?? 0;
  if (!n && !g) return "";
  const parts: string[] = [];
  if (n) parts.push(`${n} mark${n === 1 ? "" : "s"} with a detail and no place on the plans`);
  if (g) parts.push(`${g} beam mark${g === 1 ? "" : "s"} without a depth`);
  return parts.join(" · ");
}

export function isEmpty(r: DetailOnlyReport | undefined): boolean {
  return !r || (!r.columns.length && !r.beams.length && !r.depth_gaps.length && !r.decisions.length);
}

function finite(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

export function detailOnlyMarks(r: DetailOnlyReport | null | undefined, sheetId: string | null | undefined): ReadingGapsMark[] {
  if (!r || !sheetId) return [];
  const out: ReadingGapsMark[] = [];
  for (const col of r.columns ?? []) {
    for (const p of col.proposals ?? []) {
      if (p.sheet_id !== sheetId) continue;
      for (const pt of p.points ?? []) {
        if (out.length >= MAX_OVERLAY_MARKS) return out;
        if (finite(pt?.[0]) && finite(pt?.[1])) out.push({ x: pt[0], y: pt[1], text: `${col.mark}?`, colour: DETAIL_ONLY_COLOUR });
      }
    }
  }
  return out;
}

export function offeredMarks(c: DetailOnlyColumn, p: PlaceProposal): string[] {
  return p.offered.length ? p.offered : [c.mark];
}

export function beamLine(b: DetailOnlyBeam): string {
  const bits = [b.kind.toLowerCase(), b.depth_mm ? `${inches(b.depth_mm)} deep` : "depth not read"];
  if (b.width_mm) bits.push(`${inches(b.width_mm)} wide`);
  if (b.steel_text) bits.push(b.steel_text);
  return bits.join(", ");
}

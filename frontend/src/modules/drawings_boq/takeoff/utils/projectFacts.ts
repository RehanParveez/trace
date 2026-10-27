import type { FactSource, FloorEntry, FloorSource, FloorSources, ProjectFacts } from "../types/takeoff.types";
import { floorText } from "./sheetRole";

const KIND_TEXT: Record<string, string> = { WORKING: "working drawing", FURNITURE: "furniture layout", OVERLAY: "services overlay", FRAMING: "framing plan", FOUNDATION: "foundation plan" };

export interface ProjectDrawingNames { [drawingId: string]: string }

export interface FactRow {
  key: string;
  label: string;
  value: string;
  sources: FactSource[];
}

export function drawingNames(facts: ProjectFacts | undefined): ProjectDrawingNames {
  const out: ProjectDrawingNames = {};
  for (const d of facts?.drawings ?? []) out[d.drawing_id] = d.name;
  return out;
}

export function shortName(name: string | null | undefined): string {
  if (!name) return "";
  const base = name.replace(/\.pdf$/i, "");
  return base.length > 28 ? `${base.slice(0, 26)}…` : base;
}

export function sourceGroups(sources: FactSource[] | undefined, names: ProjectDrawingNames): Array<{ drawingId: string; name: string; pages: number[] }> {
  const by = new Map<string, number[]>();
  for (const s of sources ?? []) {
    const pages = by.get(s.drawing_id) ?? [];
    if (!pages.includes(s.page_no)) pages.push(s.page_no);
    by.set(s.drawing_id, pages);
  }
  return Array.from(by, ([drawingId, pages]) => ({ drawingId, name: shortName(names[drawingId]) || "PDF", pages: pages.sort((a, b) => a - b) }));
}

export function pagesText(pages: number[]): string {
  return pages.map((p) => `p.${p}`).join(", ");
}

function sourcesOf(value: unknown): FactSource[] {
  if (!value || typeof value !== "object") return [];
  const own = (value as { sources?: unknown }).sources;
  return Array.isArray(own) ? (own as FactSource[]) : [];
}

function mmText(v: unknown): string {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? `${Math.round(n)} mm` : "";
}

export function factRows(facts: ProjectFacts | undefined): FactRow[] {
  if (!facts) return [];
  const f = facts.facts;
  const rows: FactRow[] = [];
  for (const [floor, h] of Object.entries(f.storey_heights ?? {})) {
    const v = mmText((h as { clear_mm?: number }).clear_mm);
    if (v) rows.push({ key: `height-${floor}`, label: `${floorText(floor) || floor} clear height`, value: v, sources: sourcesOf(h) });
  }
  for (const s of f.slab_values ?? []) {
    const v = mmText((s as { mm?: number }).mm);
    if (v) rows.push({ key: `slab-${v}`, label: "Slab thickness", value: v, sources: sourcesOf(s) });
  }
  for (const b of f.beam_sections ?? []) {
    const x = b as { mark?: string; depth_mm?: number; kind?: string };
    if (x.mark) rows.push({ key: `beam-${x.mark}`, label: `Beam ${x.mark}${x.kind ? ` (${String(x.kind).toLowerCase()})` : ""}`, value: mmText(x.depth_mm) || "section read", sources: sourcesOf(b) });
  }
  const openings = (f.schedule as { openings?: Array<{ mark: string; width_mm?: number; height_mm?: number }> } | undefined)?.openings ?? [];
  for (const o of openings) {
    const w = mmText(o.width_mm);
    const h = mmText(o.height_mm);
    if (o.mark && (w || h)) rows.push({ key: `opening-${o.mark}`, label: `Opening ${o.mark}`, value: [w, h].filter(Boolean).join(" × "), sources: sourcesOf(o) });
  }
  const units = f.units as { imperial?: boolean | null } | undefined;
  if (units && typeof units.imperial === "boolean") rows.push({ key: "units", label: "Dimensions in", value: units.imperial ? "feet and inches" : "millimetres, metres", sources: sourcesOf(units) });
  return rows;
}

export interface PlanRow {
  sheetId: string;
  pageNo: number;
  drawingId: string | null;
  drawingName: string;
  kindText: string;
  dims: number;
  base: boolean;
  setAside: boolean;
  taking: boolean;
  caption: string;
}

export interface PlanFloor {
  floor: string;
  floorText: string;
  choosable: boolean;
  baseSheetId: string | null;
  reason: string | null;
  plans: PlanRow[];
}

export function planRow(s: FloorSource): PlanRow {
  const kind = s.plan_kind ?? null;
  return {
    sheetId: s.sheet_id, pageNo: s.page_no, drawingId: s.drawing_id ?? null, drawingName: shortName(s.drawing_name),
    kindText: kind ? (KIND_TEXT[kind] ?? kind.toLowerCase()) : "plan", dims: s.dims ?? 0, base: Boolean(s.base), setAside: s.set_aside,
    taking: kind !== "OVERLAY" && kind !== "FRAMING" && kind !== "FOUNDATION", caption: s.caption ?? "",
  };
}

export function planFloors(data: FloorSources | undefined): PlanFloor[] {
  return (data?.floors ?? [])
    .filter((e: FloorEntry) => e.sources.length > 1)
    .map((e: FloorEntry) => ({
      floor: e.floor, floorText: floorText(e.floor) || e.floor, choosable: e.choosable, baseSheetId: e.base_sheet_id ?? null, reason: e.base_reason ?? null,
      plans: e.sources.map(planRow),
    }));
}

export function planSummary(floors: PlanFloor[], drawings: number): string {
  if (!floors.length) return "";
  const alternatives = floors.filter((f) => f.choosable).length;
  const more = drawings > 1 ? `, from ${drawings} PDFs` : "";
  return `${floors.length} floor${floors.length === 1 ? "" : "s"} shown on more than one plan${more}${alternatives ? `; ${alternatives} with a base plan` : ""}`;
}

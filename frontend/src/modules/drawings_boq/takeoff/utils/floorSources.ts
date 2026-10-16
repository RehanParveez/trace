import type { FloorChoiceResult, FloorEntry, FloorSource, LeftOut, PlanRead, TakeoffCandidate } from "../types/takeoff.types";

const FLOOR_NAMES: Record<string, string> = {
  FOUNDATION: "Foundation", BASEMENT: "Basement", GROUND: "Ground floor", MEZZANINE: "Mezzanine", FIRST: "First floor", SECOND: "Second floor",
  THIRD: "Third floor", FOURTH: "Fourth floor", TYPICAL: "Typical floor", ROOF: "Roof",
};

export function floorName(key: string): string {
  return FLOOR_NAMES[key] ?? key.charAt(0) + key.slice(1).toLowerCase();
}

export function sourceName(s: FloorSource): string {
  return s.from_plans ? `Page ${s.page_no} (one plan among the plans of the sheet)` : `Page ${s.page_no}`;
}

export function metres(v: number): string {
  return `${v.toLocaleString("en", { maximumFractionDigits: 1, minimumFractionDigits: v > 0 && v < 10 ? 1 : 0 })} m`;
}

export function sourceLine(s: FloorSource): string {
  if (s.items === 0) return "nothing read for this floor";
  const parts = [`${s.walls} walls, ${metres(s.wall_m)}`, `${s.items} items`];
  if (s.accepted > 0) parts.push(`${s.accepted} accepted`);
  if (s.set_aside) parts.push("set aside");
  else if (s.open > 0) parts.push(`${s.open} open`);
  return parts.join(" · ");
}

export type FloorTone = "gold" | "green" | "red" | "slate";

export function floorState(f: FloorEntry): { tone: FloorTone; text: string } {
  const page = (id: string | null) => f.sources.find((s) => s.sheet_id === id)?.page_no;
  if (f.conflict) return { tone: "red", text: "Measured from two sheets" };
  if (f.state === "DOUBLE") return { tone: "gold", text: "Read twice: counted twice if both are accepted" };
  if (f.state === "CHOSEN") return { tone: "green", text: `Using page ${page(f.chosen_sheet_id)}` };
  if (f.state === "NONE") return { tone: "slate", text: "Nothing open" };
  if (f.state === "LISTED") return { tone: "slate", text: "Read from several sheets" };
  return { tone: "slate", text: "Read once" };
}

export function wallGap(f: FloorEntry): string {
  const [a, b] = [...f.sources].sort((x, y) => y.wall_m - x.wall_m);
  if (!a || !b || a.wall_m < 5) return "";
  const pct = Math.round(((a.wall_m - b.wall_m) / a.wall_m) * 100);
  return pct >= 1 ? `The two readings of the walls differ by ${pct}% (${metres(a.wall_m)} against ${metres(b.wall_m)}).` : "The two readings of the walls agree.";
}

export function floorsToShow(floors: FloorEntry[] | undefined): FloorEntry[] {
  return (floors ?? []).filter((f) => f.sources.length > 0);
}

export function choiceToast(r: FloorChoiceResult): { ok: string | null; problem: string | null } {
  const ok = r.chosen.length
    ? r.chosen.map((c) => `${floorName(c.floor)}: page ${c.page_no} in use${c.set_aside ? `, ${c.set_aside} items set aside` : ""}${c.restored ? `, ${c.restored} brought back` : ""}`).join("; ")
    : null;
  return { ok, problem: r.blocked.length ? r.blocked.map((b) => `${floorName(b.floor)}: ${b.message}`).join(" ") : null };
}

export function autoChoiceLine(chosen: FloorChoiceResult["chosen"] | undefined): string | null {
  if (!chosen?.length) return null;
  return chosen.map((c) => `${floorName(c.floor)}: page ${c.page_no} is used${c.set_aside ? `, ${c.set_aside} items of the other sheet set aside` : ""}`).join("; ");
}

export interface PlanBox { bbox: [number, number, number, number]; label: string; kind: "READ" | "LEFT_OUT" }

function box(v: unknown): [number, number, number, number] | null {
  return Array.isArray(v) && v.length === 4 && v.every((n) => typeof n === "number" && Number.isFinite(n)) ? [v[0], v[1], v[2], v[3]] : null;
}

export function planBoxes(stats: Record<string, unknown> | undefined): PlanBox[] {
  const regions = stats?.plan_regions as { count?: number; plans?: PlanRead[]; left_out?: LeftOut[] } | undefined;
  if (!regions?.count) return [];
  const out: PlanBox[] = [];
  for (const p of regions.plans ?? []) {
    const b = box(p.bbox);
    if (b) out.push({ bbox: b, kind: "READ", label: `${p.level_hint ? floorName(p.level_hint) : p.caption} · read` });
  }
  for (const e of regions.left_out ?? []) {
    const b = box(e.bbox);
    if (b) out.push({ bbox: b, kind: "LEFT_OUT", label: `${e.caption ?? "Drawing not named"} · left out` });
  }
  return out;
}

export function planBoxOf(stats: Record<string, unknown> | undefined, floor: string): { x0: number; y0: number; x1: number; y1: number } | null {
  const regions = stats?.plan_regions as { plans?: PlanRead[] } | undefined;
  const b = box((regions?.plans ?? []).find((p) => p.level_hint === floor)?.bbox);
  return b ? { x0: b[0], y0: b[1], x1: b[2], y1: b[3] } : null;
}

export function hasPlans(stats: Record<string, unknown> | undefined): boolean {
  return planBoxes(stats).length > 0;
}

const FLOOR_ORDER = ["FOUNDATION", "BASEMENT", "GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH", "TYPICAL", "ROOF"];

export function candidateFloor(c: TakeoffCandidate): string | null {
  const view = (c.facts as { view?: { level_hint?: string | null } } | undefined)?.view;
  return view?.level_hint ?? null;
}

export function setAsideBy(c: TakeoffCandidate): number | null {
  const mark = (c.facts as { set_aside?: { by?: string; page_no?: number } } | undefined)?.set_aside;
  return mark?.by === "FLOOR_CHOICE" && typeof mark.page_no === "number" ? mark.page_no : null;
}

export interface FloorGroup { key: string; title: string; items: TakeoffCandidate[] }

export function groupByFloor(list: TakeoffCandidate[]): FloorGroup[] {
  const floors = new Set(list.map(candidateFloor).filter((f): f is string => f !== null));
  if (floors.size < 2) return list.length ? [{ key: "", title: "", items: list }] : [];
  const rank = (f: string) => (FLOOR_ORDER.includes(f) ? FLOOR_ORDER.indexOf(f) : FLOOR_ORDER.length);
  const out: FloorGroup[] = [...floors].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b)).map((f) => ({ key: f, title: floorName(f), items: list.filter((c) => candidateFloor(c) === f) }));
  const rest = list.filter((c) => candidateFloor(c) === null);
  if (rest.length) out.push({ key: "OTHER", title: "Other items on the sheet", items: rest });
  return out;
}

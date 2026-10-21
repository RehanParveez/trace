import type {
  FamilyScore, ImportLabelsBody, LabelsSummary, MatchRuleValues, MemberRef, NotJudged, RegressionReason, RunScoreBody, ScoreBaseline, ScoreListItem, ScoreMode, ScoreStatus, ScoreTotalsView, SizeCounts,
} from "../types/readingScore.types";

export const FAMILY_NAMES: Record<string, string> = {
  COLUMN: "Columns", FOOTING: "Footings", BEAM: "Beams", DOOR: "Doors", WINDOW: "Windows", WALL: "Walls", ROOM: "Rooms", SLAB: "Slabs", LINTEL: "Lintels", STAIR: "Stairs", SITE: "Site items",
};
export const SITE_NAMES: Record<string, string> = {
  OHWT: "Overhead tank", UGWT: "Underground tank", SEPTIC: "Septic tank", BOUNDARY_WALL: "Boundary wall", GATE: "Gate", PORCH_RAMP: "Porch ramp",
};

export function familyName(family: string): string {
  const [cat, kind] = family.split(":");
  if (cat === "SITE" && kind) return SITE_NAMES[kind] ?? `Site: ${kind}`;
  return FAMILY_NAMES[cat ?? ""] ?? family;
}

export function percent(v: number | null | undefined, upperBound = false): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return `${upperBound ? "≤ " : ""}${(v * 100).toFixed(1)} %`;
}

export function pointsDelta(d: number | null | undefined): string {
  if (d === null || d === undefined || !Number.isFinite(d)) return "—";
  const pts = Math.round(d * 1000) / 10;
  if (pts === 0) return "0.0 pts";
  return `${pts > 0 ? "+" : "−"}${Math.abs(pts).toFixed(1)} pts`;
}

export type DeltaTone = "good" | "bad" | "same" | "none";
export function deltaTone(d: number | null | undefined): DeltaTone {
  if (d === null || d === undefined || !Number.isFinite(d)) return "none";
  const pts = Math.round(d * 1000) / 10;
  return pts === 0 ? "same" : pts > 0 ? "good" : "bad";
}

export const STATUS_TEXT: Record<ScoreStatus, string> = { OK: "OK", REGRESSION: "Regression", PARTIAL: "Partial", NO_LABELS: "No labels" };
export function statusLabel(s: ScoreStatus): string {
  return STATUS_TEXT[s] ?? s;
}
export function statusTone(s: ScoreStatus): "green" | "red" | "gold" | "slate" {
  return s === "OK" ? "green" : s === "REGRESSION" ? "red" : s === "PARTIAL" ? "gold" : "slate";
}

export function sizeText(size: SizeCounts | undefined): string {
  if (!size) return "—";
  const judged = size.ok + size.wrong;
  if (judged === 0) return size.unread ? `${size.unread} not read` : "—";
  return `${size.ok} of ${judged} (${percent(size.ok / judged)})${size.unread ? `, ${size.unread} not read` : ""}`;
}

export interface FamilyRow {
  family: string;
  name: string;
  labels: number;
  found: number;
  right: number;
  missed: number;
  wrong: number;
  unlabelled: number;
  precision: string;
  recall: string;
  f1: string;
  size: string;
  upperBound: boolean;
  nothingLabelled: boolean;
}

export function familyRows(families: FamilyScore[]): FamilyRow[] {
  return [...families].sort((a, b) => familyName(a.family).localeCompare(familyName(b.family))).map((f) => ({
    family: f.family,
    name: familyName(f.family),
    labels: f.labels,
    found: f.found,
    right: f.tp,
    missed: f.fn,
    wrong: f.fp,
    unlabelled: f.unlabelled,
    precision: percent(f.precision, Boolean(f.upper_bound) && f.precision !== null),
    recall: percent(f.recall),
    f1: percent(f.f1),
    size: sizeText(f.size),
    upperBound: Boolean(f.upper_bound),
    nothingLabelled: f.labels === 0,
  }));
}

export function headline(t: ScoreTotalsView): string {
  return `F1 ${percent(t.f1)} · recall ${percent(t.recall)} · precision ${percent(t.precision)}`;
}

export function versionLabel(s: Pick<ScoreListItem, "extract_version" | "mode" | "label_drawing_id">): string {
  const v = s.extract_version === null ? "reader version unknown" : `reader version ${s.extract_version}`;
  const how = s.mode === "DRY_RUN" ? "read again" : "stored items";
  return `${v} · ${how}${s.label_drawing_id ? " · labels of another drawing" : ""}`;
}

export function rulePairs(rule: MatchRuleValues | undefined): string[] {
  if (!rule) return [];
  return [
    rule.positions ? `no mark: match within ${rule.position_tol_pt} pt` : "positions not compared (members without a mark are not judged)",
    `size within ${rule.size_tol_pct} % or ${rule.size_tol_mm} mm`,
    `regression when F1 falls by more than ${(rule.regression_tol * 100).toFixed(1)} pts`,
    `a kind is gated from ${rule.gate_min_units} labelled members`,
  ];
}

export function notJudgedLine(c: NotJudged): string {
  return `Sheet ${c.page_no}${c.title ? ` (${c.title})` : ""}: ${c.detail}`;
}

export function memberText(m: MemberRef): string {
  const where = m.x !== null && m.y !== null ? ` at (${Math.round(m.x)}, ${Math.round(m.y)})` : "";
  return `${m.mark ?? "no mark"}${where}`;
}

export const WHY_TEXT: Record<string, string> = {
  NOT_FOUND: "labelled, not found",
  REJECTED_BY_PERSON: "found, a person rejected it",
  NOT_ON_SHEET: "found, not in the labels of a complete sheet",
};

export function regressionLines(baseline: ScoreBaseline | null | undefined): string[] {
  if (!baseline) return [];
  return baseline.reasons.map((r: RegressionReason) => `${r.scope === "ALL" ? "Overall" : familyName(r.scope)}: best ${percent(r.best)}, now ${percent(r.now)}`);
}

export function baselineLine(baseline: ScoreBaseline | null | undefined): string | null {
  if (!baseline) return null;
  if (baseline.score_id === null) return baseline.note ?? "Nothing to compare with yet.";
  return baseline.reasons.length ? "Below the best score of these labels by more than the tolerance." : `Not below the best score of these labels (F1 ${percent(baseline.f1 ?? null)}).`;
}

export function toggleCompare(selected: string[], id: string): string[] {
  if (selected.includes(id)) return selected.filter((x) => x !== id);
  return [...selected, id].slice(-2);
}

export function labelsLine(l: LabelsSummary | undefined): string {
  if (!l || l.labels === 0) return "No labels yet.";
  const parts = [`${l.positive} members that stand`, `${l.negative} wrong finds`, `on ${l.sheets.length} sheet${l.sheets.length === 1 ? "" : "s"}`];
  return parts.join(" · ");
}

export interface RunOptions {
  mode: ScoreMode;
  marksOnly: boolean;
  labelDrawingId: string;
  note: string;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function isUuid(s: string): boolean {
  return UUID.test(s.trim());
}

export function runBody(o: RunOptions): RunScoreBody {
  const body: RunScoreBody = { mode: o.mode };
  if (o.marksOnly) body.rule = { positions: false };
  if (o.labelDrawingId.trim() && isUuid(o.labelDrawingId)) body.label_drawing_id = o.labelDrawingId.trim();
  if (o.note.trim()) body.note = o.note.trim();
  return body;
}

export function runBlocked(o: RunOptions, labels: LabelsSummary | undefined): string | null {
  if (o.labelDrawingId.trim() && !isUuid(o.labelDrawingId)) return "The drawing id of the labels is not an id.";
  if (!o.labelDrawingId.trim() && (!labels || labels.labels === 0)) return "Make labels from the register or import a ground-truth file first.";
  return null;
}

export function importFormatOf(filename: string): ImportLabelsBody["format"] | null {
  const n = filename.toLowerCase();
  return n.endsWith(".csv") ? "CSV" : n.endsWith(".json") ? "JSON" : null;
}

export function sheetBasisText(basis: "COMPLETE" | "NEGATIVES_ONLY"): string {
  return basis === "COMPLETE" ? "Every member of this sheet is labelled" : "Only some members are labelled: wrong finds are counted only when a person rejected them";
}

export function totalsOf(families: FamilyScore[]): { labels: number; right: number; missed: number; wrong: number } {
  return families.reduce((a, f) => ({ labels: a.labels + f.labels, right: a.right + f.tp, missed: a.missed + f.fn, wrong: a.wrong + f.fp }), { labels: 0, right: 0, missed: 0, wrong: 0 });
}

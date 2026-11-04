import type { Box, ClassRow, MisreadKind, ReadStatus, ReportItem, ReportSheet, ScaleState, SheetStatus } from "../types/readingReport.types";

export const STATUS_ORDER: ReadStatus[] = ["READ", "UNSURE", "CONFLICT", "NOT_READ"];
export const STATUS_TEXT: Record<string, string> = { READ: "Read", UNSURE: "Unsure", NOT_READ: "Not read", CONFLICT: "Conflict", NOT_RUN: "Not run", NOTHING_EXPECTED: "Nothing expected" };
export const STATUS_COLOUR: Record<string, string> = { READ: "#12805c", UNSURE: "#b7791f", NOT_READ: "#b42318", CONFLICT: "#6941c6", NOT_RUN: "#98a2b3", NOTHING_EXPECTED: "#98a2b3" };
export const STATUS_VAR: Record<string, string> = {
  READ: "var(--color-success, #12805c)", UNSURE: "var(--color-warning, #b7791f)", NOT_READ: "var(--color-danger, #b42318)", CONFLICT: "var(--color-info, #6941c6)", NOT_RUN: "var(--color-border-strong, #98a2b3)",
  NOTHING_EXPECTED: "var(--color-border-strong, #98a2b3)",
};

export function statusText(s: SheetStatus | string | undefined): string {
  return (s && STATUS_TEXT[s]) || "—";
}

export const REASON_TEXT: Record<string, string> = {
  NO_SYMBOLS_FOUND: "No symbols found",
  LABELS_OUTLINED: "Labels are outlines",
  OCR_LOW_CONFIDENCE: "Low-confidence OCR",
  ROLE_UNEXPECTED: "Not expected on this sheet",
  SHEET_NOT_PREPARED: "Sheet not prepared",
  NOT_READ: "Reader has not run",
  NO_SCALE: "No scale",
  SCALE_UNVERIFIED: "Scale not checked",
  ROLE_UNKNOWN: "Sheet role unknown",
  RASTER_SHEET: "Picture sheet",
  NO_ITEMS: "Nothing found",
  NOTHING_EXPECTED: "Nothing expected here",
};
export function reasonText(code: string): string {
  return REASON_TEXT[code] ?? code.toLowerCase().replace(/_/g, " ");
}

export const CLASS_TEXT: Record<string, string> = {
  GRID: "Grid", COLUMN: "Columns", FOOTING_STRIP: "Strip footings", FOOTING_PAD: "Pad footings", PLINTH_BEAM: "Plinth beams", BEAM: "Beams", SLAB_PANEL: "Slab panels",
  SLAB_BAR_CALLOUT: "Slab bar callouts", WALL: "Walls", ROOM: "Rooms", DOOR: "Doors", WINDOW: "Windows", STAIR: "Stairs", LINTEL_TYPE: "Lintels", ELECTRICAL_POINT: "Electrical points",
  DISTRIBUTION_BOARD: "Distribution boards", PLUMBING_FIXTURE: "Plumbing fixtures", PIPE_RUN: "Pipe runs", DRAIN_POINT: "Drain points", COLUMN_SCHEDULE_CELL: "Column schedule cells",
  NOTE_FACT: "Note facts", OTHER: "Other",
};
export function classText(c: string): string {
  return CLASS_TEXT[c] ?? c.replace(/_/g, " ").toLowerCase();
}
export const CLASS_CHOICES = Object.keys(CLASS_TEXT);

export const ROLE_TEXT: Record<string, string> = { PLAN: "Plan", SCHEDULE: "Schedule", NOTES: "Notes", DETAIL: "Detail", SECTION: "Section", ELEVATION: "Elevation", COVER: "Cover" };
export const TEXT_TYPE_TEXT: Record<string, string> = { TEXT: "Text", OUTLINED: "Outlined", PARTIAL: "Part outlined", RASTER: "Picture" };
export const SCALE_TEXT: Record<ScaleState, string> = { SET: "Scale set", UNVERIFIED: "Scale unchecked", MISSING: "No scale", UNKNOWN: "Scale unknown" };

export function roleText(r: string | null): string {
  return r ? ROLE_TEXT[r] ?? r : "Role unknown";
}

export function sheetHeading(s: ReportSheet): string {
  return s.title?.trim() || `Page ${s.page_no}`;
}

export function sheetSubline(s: ReportSheet): string {
  const parts = [roleText(s.role)];
  if (s.plan_kind) parts.push(s.plan_kind.replace(/_/g, " ").toLowerCase());
  if (s.floor) parts.push(s.floor.toLowerCase());
  return parts.join(" · ");
}

export interface BarPart {
  status: ReadStatus;
  count: number;
  pct: number;
}

/** The share of each status in a class row, in a fixed order. A class with nothing found is one full NOT_READ part, so the bar is never blank. */
export function barParts(row: Pick<ClassRow, "by_status" | "status">): BarPart[] {
  const total = STATUS_ORDER.reduce((n, s) => n + (row.by_status[s] ?? 0), 0);
  if (total === 0) return [{ status: row.status === "READ" ? "READ" : row.status === "UNSURE" ? "UNSURE" : "NOT_READ", count: 0, pct: 100 }];
  return STATUS_ORDER.filter((s) => (row.by_status[s] ?? 0) > 0).map((s) => ({ status: s, count: row.by_status[s] ?? 0, pct: ((row.by_status[s] ?? 0) / total) * 100 }));
}

export function barLabel(row: ClassRow): string {
  const found = STATUS_ORDER.filter((s) => (row.by_status[s] ?? 0) > 0).map((s) => `${row.by_status[s]} ${statusText(s).toLowerCase()}`);
  return found.length ? found.join(", ") : row.count > 0 ? `${row.count} found` : "none found";
}

export function totalsLine(by: Record<string, number>): string {
  const parts = STATUS_ORDER.filter((s) => (by[s] ?? 0) > 0).map((s) => `${by[s]} ${statusText(s).toLowerCase()}`);
  return parts.length ? parts.join(" · ") : "no items";
}

export function sheetsByFloor(sheets: ReportSheet[]): { floor: string; sheets: ReportSheet[] }[] {
  const out: { floor: string; sheets: ReportSheet[] }[] = [];
  for (const s of sheets) {
    const floor = s.floor?.trim() || "";
    let g = out.find((x) => x.floor === floor);
    if (!g) {
      g = { floor, sheets: [] };
      out.push(g);
    }
    g.sheets.push(s);
  }
  return out;
}

export function visibleItems(items: ReportItem[], hidden: ReadonlySet<string>, classFilter: string | null): ReportItem[] {
  return items.filter((i) => !hidden.has(i.status) && (!classFilter || i.class === classFilter));
}

function dist2(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2));
  const cx = ax + t * dx;
  const cy = ay + t * dy;
  return (px - cx) ** 2 + (py - cy) ** 2;
}

function inside(px: number, py: number, pts: number[][]): boolean {
  let hit = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i] as number[];
    const [xj, yj] = pts[j] as number[];
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

/** The item nearest to a point of the page, within `radius` page points. Areas count when the point is inside. */
export function itemAt(items: ReportItem[], x: number, y: number, radius: number): ReportItem | null {
  let best: ReportItem | null = null;
  let bestD = radius * radius;
  for (const it of items) {
    const pts = it.points;
    if (!pts.length) continue;
    let d = Infinity;
    if (it.kind === "AREA" && pts.length >= 3 && inside(x, y, pts)) d = 0;
    else if (pts.length === 1) d = ((pts[0] as number[])[0] - x) ** 2 + ((pts[0] as number[])[1] - y) ** 2;
    else {
      const closed = it.kind === "AREA";
      const n = closed ? pts.length : pts.length - 1;
      for (let i = 0; i < n; i++) {
        const a = pts[i] as number[];
        const b = pts[(i + 1) % pts.length] as number[];
        d = Math.min(d, dist2(x, y, a[0] as number, a[1] as number, b[0] as number, b[1] as number));
      }
    }
    if (d <= bestD) {
      best = it;
      bestD = d;
    }
  }
  return best;
}

export function normaliseBox(a: [number, number], b: [number, number]): Box {
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
}

export function boxTooSmall(b: Box, minPt = 2): boolean {
  return b[2] - b[0] < minPt || b[3] - b[1] < minPt;
}

export const MISREAD_TEXT: Record<MisreadKind, string> = {
  WRONG_VALUE: "A value is wrong", WRONG_CLASS: "It is the wrong kind of item", WRONG_POSITION: "It is in the wrong place", INVENTED: "It is not on the drawing", MISSED: "The reader missed it", OTHER: "Something else",
};

export function sourceText(source: string): string {
  const t: Record<string, string> = { VECTOR_SNAP: "Drawing lines", TAG_SCAN: "Text labels", PRINTED: "Printed value", MANUAL: "Typed by a person", OCR: "Outline labels (OCR)" };
  return t[source] ?? source.toLowerCase().replace(/_/g, " ");
}

export function confidenceText(c: number | null): string {
  return c === null || !Number.isFinite(c) ? "—" : `${Math.round(c * 100)} %`;
}

/** Why an item is shown the way it is, as short sentences: its reasons, the conflict, the inputs still missing. */
export function itemNotes(it: ReportItem): string[] {
  const out = it.reasons.map(reasonText);
  if (it.conflict) out.push(it.conflict);
  if (it.missing.length) out.push(`Still needs: ${it.missing.map((m) => m.replace(/_/g, " ")).join(", ")}`);
  return out;
}

export function emptyCardLines(s: ReportSheet): string[] {
  const lines = s.reasons.map((r) => r.text);
  return lines.length ? lines : ["The reader found nothing here and gave no reason."];
}

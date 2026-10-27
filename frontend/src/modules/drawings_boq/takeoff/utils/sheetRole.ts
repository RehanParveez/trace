import type { FloorOrdered, SheetIdentity, TakeoffSheet } from "../types/takeoff.types";

export type ReadState = "PLAN" | "SYMBOLS" | "DETAILS" | "SKIPPED" | "UNREAD";
export type RoleTone = "blue" | "gold" | "green" | "red" | "slate";

const ROLE_TEXT: Record<string, string> = {
  PLAN: "Plan", STRUCTURAL: "Structural plan", COMPOSITE: "Several views", SECTION: "Section", ELEVATION: "Elevation", DETAIL: "Detail", SCHEDULE: "Schedule", SITE: "Site plan",
  LEGEND: "Legend", SPEC: "Specification", COVER: "Cover", DIVIDER: "Divider", UNKNOWN: "Not recognised",
};

const KIND_TEXT: Record<string, string> = { WORKING: "working drawing", FURNITURE: "furniture layout", OVERLAY: "services overlay", FRAMING: "framing plan", FOUNDATION: "foundation plan" };

const FLOOR_TEXT: Record<string, string> = {
  BASEMENT: "Basement", GROUND: "Ground floor", FIRST: "First floor", SECOND: "Second floor", THIRD: "Third floor", FOURTH: "Fourth floor", MEZZANINE: "Mezzanine", ROOF: "Roof", FOUNDATION: "Foundation", TYPICAL: "Typical floor",
};

const BASIS_TEXT: Record<string, string> = { TITLE: "written on the sheet", VIEW: "from the captions of its plans", ORDER: "guessed from the sheet order", PERSON: "set by you" };

const GUESS_TEXT: Record<string, string> = {
  SHARES_ROOM_SIZES: "same room sizes as a floor that is named",
  PORCH_OR_LAWN_LABELS: "porch, lawn or drive labels",
  MUMTY_OR_STAIR_TOWER_LABELS: "mumty or stair tower labels with no bedrooms",
  PAGE_ORDER: "its place in the PDF, above the lowest named floor",
};

const DISCIPLINE_TEXT: Record<string, string> = { ARCHITECTURAL: "Architecture", STRUCTURAL: "Structure", ELECTRICAL: "Electrical", PLUMBING: "Plumbing", HVAC: "HVAC", FIRE: "Fire", GAS: "Gas", SITE: "Site" };

export interface SheetRoleRow {
  sheetId: string;
  pageNo: number;
  title: string;
  role: string | null;
  roleText: string;
  discipline: string | null;
  disciplineText: string;
  planKind: string | null;
  planKindText: string;
  floor: string | null;
  floorText: string;
  basis: string | null;
  basisText: string;
  readAs: string | null;
  state: ReadState;
  stateText: string;
  tone: RoleTone;
  person: boolean;
  mixed: boolean;
  guessed: boolean;
  canReadAsPlan: boolean;
}

export function roleText(role: string | null | undefined): string {
  return role ? (ROLE_TEXT[role] ?? role.toLowerCase()) : "";
}

export function floorText(floor: string | null | undefined): string {
  return floor ? (FLOOR_TEXT[floor] ?? floor.toLowerCase()) : "";
}

export function readState(identity: SheetIdentity | null | undefined): ReadState {
  const readAs = identity?.read_as;
  if (!identity || !readAs) return "UNREAD";
  if (readAs === "SKIP") return "SKIPPED";
  if (readAs === "DETAILS_ONLY") return "DETAILS";
  if (readAs === "SYMBOLS_ONLY") return "SYMBOLS";
  return "PLAN";
}

export function stateOf(identity: SheetIdentity | null | undefined): { state: ReadState; text: string; tone: RoleTone } {
  const state = readState(identity);
  const role = roleText(identity?.role).toLowerCase();
  if (state === "SKIPPED") return { state, text: role ? `not read: ${role}` : "not read", tone: "slate" };
  if (state === "DETAILS") return { state, text: "details only", tone: "blue" };
  if (state === "SYMBOLS") return { state, text: "symbols only", tone: "blue" };
  if (state === "PLAN") return { state, text: identity?.mixed ? "read as plan (also holds services)" : "read as plan", tone: "green" };
  return { state, text: "not read yet", tone: "gold" };
}

export function basisText(basis: string | null | undefined, guess?: string | null): string {
  if (!basis) return "";
  if (basis === "ORDER" && guess && GUESS_TEXT[guess]) return `${BASIS_TEXT.ORDER}: ${GUESS_TEXT[guess]}`;
  return BASIS_TEXT[basis] ?? basis.toLowerCase();
}

export function rowOf(sheet: TakeoffSheet, ordered: FloorOrdered[]): SheetRoleRow {
  const identity = sheet.identity ?? null;
  const guess = ordered.find((o) => o.sheet_id === sheet.id) ?? null;
  const floor = identity?.floor ?? guess?.floor ?? null;
  const basis = identity?.floor ? (identity.floor_basis ?? "TITLE") : guess ? "ORDER" : null;
  const st = stateOf(identity);
  const readAs = identity?.read_as ?? null;
  const planKind = identity?.plan_kind ?? null;
  const discipline = identity?.discipline ?? null;
  return {
    sheetId: sheet.id,
    pageNo: sheet.page_no,
    title: sheet.label || identity?.title || identity?.role_title || "",
    role: identity?.role ?? null,
    roleText: roleText(identity?.role),
    discipline,
    disciplineText: discipline ? (DISCIPLINE_TEXT[discipline] ?? discipline.toLowerCase()) : "",
    planKind,
    planKindText: planKind ? (KIND_TEXT[planKind] ?? planKind.toLowerCase()) : "",
    floor,
    floorText: floorText(floor),
    basis,
    basisText: basisText(basis, guess?.reason ?? null),
    readAs,
    state: st.state,
    stateText: st.text,
    tone: st.tone,
    person: identity?.basis === "PERSON" || (identity?.person_set?.length ?? 0) > 0,
    mixed: Boolean(identity?.mixed),
    guessed: basis === "ORDER",
    canReadAsPlan: sheet.prep_status === "READY" && (st.state === "SKIPPED" || st.state === "DETAILS" || st.state === "SYMBOLS"),
  };
}

export function rowsOf(sheets: TakeoffSheet[], ordered: FloorOrdered[]): SheetRoleRow[] {
  return [...sheets].sort((a, b) => a.page_no - b.page_no).map((s) => rowOf(s, ordered));
}

export interface RoleSummary { plan: number; partial: number; skipped: number; unread: number; guessed: number }

export function summary(rows: SheetRoleRow[]): RoleSummary {
  const out: RoleSummary = { plan: 0, partial: 0, skipped: 0, unread: 0, guessed: 0 };
  for (const r of rows) {
    if (r.state === "PLAN") out.plan += 1;
    else if (r.state === "SYMBOLS" || r.state === "DETAILS") out.partial += 1;
    else if (r.state === "SKIPPED") out.skipped += 1;
    else out.unread += 1;
    if (r.guessed) out.guessed += 1;
  }
  return out;
}

export function summaryText(s: RoleSummary): string {
  const parts = [`${s.plan} read as plan`];
  if (s.partial) parts.push(`${s.partial} read in part`);
  if (s.skipped) parts.push(`${s.skipped} not read`);
  if (s.unread) parts.push(`${s.unread} not read yet`);
  if (s.guessed) parts.push(`${s.guessed} with a guessed floor`);
  return parts.join(", ");
}

export const READ_AS_PLAN_BODY = { identity: { role: "PLAN", read_as: "PLAN_ITEMS" } } as const;

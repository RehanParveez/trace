import type { FloorDatums, FloorLevel, FootingLevelState, LevelDecision, LevelSource, MemberZ, ZDatum, ZGrade } from "../types/takeoff.types";

const FLOOR_NAME: Record<string, string> = {
  BASEMENT: "Basement", GROUND: "Ground floor", FIRST: "First floor", SECOND: "Second floor", THIRD: "Third floor", FOURTH: "Fourth floor", ROOF: "Roof",
};

export function floorName(key: string): string {
  return FLOOR_NAME[key] ?? key.charAt(0) + key.slice(1).toLowerCase();
}

export function levelText(mm: number | null | undefined): string {
  if (mm === null || mm === undefined || !Number.isFinite(mm)) return "—";
  if (mm === 0) return "±0";
  const m = (Math.abs(mm) / 1000).toFixed(3);
  return mm > 0 ? `+${m} m` : `−${m} m`;
}

const SOURCE: Record<string, string> = {
  SECTION: "storey height printed on a building section",
  PLAN_NOTES: "storey height printed in the room notes of the plans",
  LEVEL_MARKS: "level marks on the elevations",
  TYPICAL: "typical floor-to-floor height",
  DATUM: "the floor level every height is measured from",
};

export function sourceText(source: string | null | undefined): string {
  return source ? (SOURCE[source] ?? source) : "—";
}

const LEVEL_SOURCE: Record<string, string> = {
  PRINTED_MARK: "level printed on the drawing",
  TYPED_LEVEL: "level you gave as a reference level",
  SUM_OF_STOREYS: "level of the floor below plus its storey height",
  AT_DATUM: "the datum itself",
};

const KIND_TEXT: Record<string, string> = { PERSON: "you", SECTION: "a building section", PLAN_NOTES: "the plan notes", LEVEL_MARKS: "the level marks", ASSUMED: "an assumption" };
const FIELD_TEXT: Record<string, string> = { level_mm: "level", clear_mm: "clear height", floor_to_floor_mm: "floor to floor" };

function metres(mm: number): string {
  return `${(mm / 1000).toFixed(3)} m`;
}

export function sourceLine(s: LevelSource): string {
  const value = s.field === "level_mm" ? levelText(s.value) : metres(s.value);
  return `${FIELD_TEXT[s.field] ?? s.field} ${value} from ${KIND_TEXT[s.kind] ?? s.kind}${s.used ? " (used)" : ""}`;
}

export function decisionLine(d: LevelDecision): string {
  const show = (v: number) => (d.id.startsWith("level:") ? levelText(v) : metres(v));
  const options = d.options.map((o) => `${show(o.value)} (${o.sources.map((k) => KIND_TEXT[k] ?? k).join(", ")})`).join(" or ");
  return `${d.question}: ${options}. ${d.chosen === null ? "The most trusted is used until you decide." : `You chose ${show(d.chosen)}.`}`;
}

const DATUM_TEXT: Record<ZDatum, string> = {
  DRAWING_LEVEL_ZERO: "Heights are the levels printed on the drawing, measured from its own zero mark (±0).",
  GROUND_FLOOR_LEVEL: "The drawing does not print the level of its ground floor, so heights are measured up from the ground floor level (±0 here).",
};

export function datumText(datum: string | null | undefined): string {
  return DATUM_TEXT[(datum as ZDatum) ?? "GROUND_FLOOR_LEVEL"] ?? DATUM_TEXT.GROUND_FLOOR_LEVEL;
}

const GRADE: Record<ZGrade, { label: string; tone: "green" | "blue" | "gold" }> = {
  PRINTED: { label: "printed", tone: "green" },
  TYPED: { label: "given by you", tone: "blue" },
  ASSUMED: { label: "assumed", tone: "gold" },
};

export function gradeLabel(grade: ZGrade): string {
  return GRADE[grade].label;
}

export function gradeTone(grade: ZGrade): "green" | "blue" | "gold" {
  return GRADE[grade].tone;
}

export interface FloorRow {
  key: string;
  name: string;
  level: string;
  soffit: string;
  top: string;
  source: string;
  levelSource: string;
  grade: ZGrade;
  reason: string | null;
  placed: boolean;
  sources: string[];
  decisions: string[];
  open: boolean;
}

export function floorRows(datums: Pick<FloorDatums, "floors"> | undefined): FloorRow[] {
  return (datums?.floors ?? []).map((f: FloorLevel) => ({
    key: f.key, name: floorName(f.key), level: levelText(f.level_mm), soffit: levelText(f.soffit_mm), top: levelText(f.top_mm), source: sourceText(f.source),
    levelSource: f.level_source ? (LEVEL_SOURCE[f.level_source] ?? f.level_source) : "—", grade: f.grade, reason: f.reason, placed: f.level_mm !== null,
    sources: (f.sources ?? []).map(sourceLine), decisions: (f.decisions ?? []).map(decisionLine), open: (f.decisions ?? []).some((d) => d.chosen === null),
  }));
}

export function unplacedFloors(datums: Pick<FloorDatums, "floors"> | undefined): string[] {
  return (datums?.floors ?? []).filter((f) => f.level_mm === null).map((f) => floorName(f.key));
}

export interface FootingNote { tone: "green" | "gold" | "red"; text: string }

export function footingNote(f: FootingLevelState | undefined): FootingNote {
  if (!f || (f.ngl_mm === null && f.bottom_below_ngl_mm === null)) {
    return { tone: "red", text: "Footings are not placed in height. Give the natural ground level and the footing level in the site assumptions." };
  }
  if (f.ngl_mm === null) return { tone: "red", text: "Footings are not placed in height: the natural ground level below the floor is not known." };
  if (f.bottom_below_ngl_mm === null) return { tone: "red", text: "Footings are not placed in height: how far a footing bottom lies below natural ground is not known." };
  if (f.ngl_source === "LEVEL_MARK") {
    return { tone: "gold", text: `Footings are placed from the lowest level mark on the drawing (${levelText(f.ngl_mm)}) taken as natural ground. Give the natural ground level to make it firm.` };
  }
  return { tone: "green", text: `Footings are placed from natural ground at ${levelText(f.ngl_mm)} and the footing bottom ${(f.bottom_below_ngl_mm / 1000).toFixed(3)} m below it.` };
}

export function memberZ(properties: Record<string, unknown> | null | undefined): MemberZ | null {
  const pdf = properties?._pdf as Record<string, unknown> | undefined;
  const z = pdf?.z as Record<string, unknown> | undefined;
  if (!z || typeof z !== "object") return null;
  const n = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
  return {
    base_mm: n(z.base_mm), top_mm: n(z.top_mm), base_source: String(z.base_source ?? ""), top_source: String(z.top_source ?? ""),
    grade: (z.grade === "PRINTED" || z.grade === "TYPED" ? z.grade : "ASSUMED") as ZGrade, notes: Array.isArray(z.notes) ? z.notes.map(String) : [],
    floor: typeof z.floor === "string" ? z.floor : null, datum: String(z.datum ?? ""),
  };
}

const WHY: Record<string, string> = {
  NO_FLOOR: "its floor has no level on the building",
  NO_SIZE: "its height or depth is not known",
  NEEDS_FOOTING_LEVEL: "the footing level is not known",
  NEEDS_OPENING_HEAD: "how high the opening head stands is not printed",
};

export function zText(z: MemberZ | null): string {
  if (!z) return "";
  if (z.base_mm === null || z.top_mm === null) {
    const why = WHY[z.base_mm === null ? z.base_source : z.top_source];
    const known = z.base_mm !== null ? `from ${levelText(z.base_mm)}` : z.top_mm !== null ? `up to ${levelText(z.top_mm)}` : "";
    return [known, `no height range: ${why ?? "not enough on the drawing"}`].filter(Boolean).join(", ");
  }
  return `${levelText(z.base_mm)} to ${levelText(z.top_mm)}`;
}

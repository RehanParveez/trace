import type { SheetIdentity } from "../types/takeoff.types";

export const DISCIPLINES = ["ARCHITECTURAL", "STRUCTURAL", "ELECTRICAL", "PLUMBING", "HVAC", "FIRE", "SITE"] as const;
export const SHEET_TYPES = ["PLAN", "POINTS_PLAN", "SECTION", "ELEVATION", "DETAIL", "SCHEDULE", "LEGEND", "SPEC"] as const;

export const DISCIPLINE_TEXT: Record<string, string> = {
  ARCHITECTURAL: "Architectural",
  STRUCTURAL: "Structural",
  ELECTRICAL: "Electrical",
  PLUMBING: "Plumbing and drainage",
  HVAC: "Air conditioning",
  FIRE: "Fire fighting",
  SITE: "Site",
};

export const SHEET_TYPE_TEXT: Record<string, string> = {
  PLAN: "Plan",
  POINTS_PLAN: "Points plan",
  SECTION: "Section",
  ELEVATION: "Elevation",
  DETAIL: "Detail",
  SCHEDULE: "Schedule",
  LEGEND: "Legend",
  SPEC: "Specification or notes",
};

export const FLOOR_TEXT: Record<string, string> = {
  BASEMENT: "Basement",
  GROUND: "Ground floor",
  FIRST: "First floor",
  SECOND: "Second floor",
  THIRD: "Third floor",
  FOURTH: "Fourth floor",
  MEZZANINE: "Mezzanine",
  ROOF: "Roof",
  FOUNDATION: "Foundation",
  TYPICAL: "Typical",
};

export const BASIS_TEXT: Record<string, string> = {
  TITLE_BLOCK: "from the title block",
  TITLE: "from the largest lettering",
  TEXT: "from the words on the sheet",
  PERSON: "set by you",
  NONE: "not found",
};

const SERVICES = ["ELECTRICAL", "PLUMBING", "HVAC", "FIRE"];
const PLAN_TYPES = ["PLAN", "POINTS_PLAN"];

export function leavesBackdropOut(identity: SheetIdentity | null | undefined): boolean {
  if (!identity || !identity.discipline || !identity.sheet_type) return false;
  if (!SERVICES.includes(identity.discipline) || !PLAN_TYPES.includes(identity.sheet_type)) return false;
  if (identity.basis === "PERSON") return true;
  if (/\bSITE\b/i.test(identity.title ?? "")) return false;
  return (identity.confidence ?? 0) >= (identity.basis === "TEXT" ? 0.7 : 0.55);
}

export function identityLine(identity: SheetIdentity | null | undefined): string {
  if (!identity) return "";
  const parts = [
    identity.discipline ? DISCIPLINE_TEXT[identity.discipline] ?? identity.discipline : null,
    identity.sheet_type ? SHEET_TYPE_TEXT[identity.sheet_type] ?? identity.sheet_type : null,
    identity.floor ? FLOOR_TEXT[identity.floor] ?? identity.floor : null,
  ].filter(Boolean);
  return parts.join(" · ");
}

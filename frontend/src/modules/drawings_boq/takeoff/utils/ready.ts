import type { HeldItem, ReadyItem, ReadyToAccept } from "../types/takeoff.types";

export const HELD_TEXT: Record<string, string> = {
  ALREADY_DECIDED: "already accepted or rejected",
  ERROR: "an error found on it",
  WARNING: "a warning on it",
  NOT_MEASURABLE: "beam marks only counted",
  VALUE_MISSING: "a value is missing",
  ASSUMED: "an assumed value",
  CHECK_WARNS: "a check warns about it",
  FLOOR_SOURCE_UNDECIDED: "the floor is open on two sheets",
  NOT_A_PLAN_SHEET: "the sheet is a section, elevation, detail or specification, not a floor plan",
  STAIR_TWIN_ABOVE: "the second view of a stair measured on another floor; it has no quantity of its own",
  BEAM_FROM_FRAMING_PLAN: "the framing plan of this floor draws its roof beams and is the one to measure; this beam is worked out from the walls and has no quantity of its own",
  MARK_ACCEPTED_ELSEWHERE: "the same mark is already accepted from another sheet; open that sheet, or accept it there on purpose",
  MARK_ON_SEVERAL_SHEETS: "the same mark is shown on another sheet with the same count and size; choose the sheet in the list of marks",
  MARK_SHEETS_DISAGREE: "the same mark is shown on several sheets with a different count or size; choose the sheet in the list of marks",
};

export function readyOnSheet(data: ReadyToAccept | undefined, pageNo: number): ReadyItem[] {
  return (data?.ready ?? []).filter((r) => r.page_no === pageNo);
}

export function heldOnSheet(data: ReadyToAccept | undefined, pageNo: number): HeldItem[] {
  return (data?.held ?? []).filter((r) => r.page_no === pageNo && !r.reasons.every((x) => x.code === "ALREADY_DECIDED"));
}

export function heldLine(held: HeldItem[]): string {
  const n: Record<string, number> = {};
  for (const h of held) for (const r of h.reasons) if (r.code !== "ALREADY_DECIDED") n[r.code] = (n[r.code] ?? 0) + 1;
  return Object.entries(n).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([code, k]) => `${k} ${HELD_TEXT[code] ?? code}`).join(", ");
}
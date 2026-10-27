import type { DetectedScale, ScaleNote } from "../types/takeoff.types";

export type Tone = "green" | "gold" | "red" | "slate";

export const AGREEMENT: Record<string, { tone: Tone; text: string }> = {
  VERIFIED: { tone: "green", text: "Two independent readings of this sheet (the printed scale, the printed dimensions, the room sizes or the scale bar) give the same scale." },
  VERIFIED_WEAK: { tone: "gold", text: "Two readings give the same scale, but only a few dimensions or rooms were found to check it." },
  ROOMS_ONLY: { tone: "gold", text: "No scale or dimension is printed, but the room sizes written on the plan give one." },
  WITNESS_CONFLICT: { tone: "red", text: "The scale found on this sheet disagrees with a second reading of it (the room sizes, or the scale bar). Check one known length." },
  CONFLICT: { tone: "red", text: "The printed scale and the printed dimensions disagree. The dimensions are usually right." },
  CONFLICT_UNRESOLVED: { tone: "red", text: "The printed scale and the dimensions disagree and neither can be trusted. Calibrate by hand." },
  MULTI_SCALE: { tone: "gold", text: "This sheet shows more than one scale." },
  DIMENSIONS_ONLY: { tone: "gold", text: "No scale is printed, but the printed dimensions give one." },
  DIMENSIONS_WEAK: { tone: "gold", text: "Only a few dimensions were found and no scale is printed. Check it with a known length." },
  DECLARED_ONLY: { tone: "gold", text: "A scale is printed but no dimension could check it. Plots are often not at the printed scale." },
  NONE: { tone: "slate", text: "No scale or dimension could be read. Calibrate with two points and a known distance." },
};

export const NOTE_TEXT: Record<string, { tone: Tone; text: string }> = {
  SHEET_REDUCED: { tone: "red", text: "This sheet looks printed smaller than its label says (a reduced print). Trust the measured scale, not the label." },
  SCALE_CONFLICT: { tone: "red", text: "Two different scales were found on this sheet." },
  SCALE_CONFLICT_UNRESOLVED: { tone: "red", text: "Two different scales were found and neither could be confirmed." },
  SCALE_FROM_ROOMS: { tone: "gold", text: "No scale or dimension is printed on this sheet. The scale comes from the room sizes written on the plan." },
  SCALE_WITNESS_CONFLICT: { tone: "red", text: "The room sizes or the scale bar and the other readings of this sheet give different scales." },
  SCALE_BAR_UNCONFIRMED: { tone: "gold", text: "A graphic scale bar was found, but nothing printed confirms it. A bar alone is not used to set the scale." },
  SCALE_BAR_DIFFERS: { tone: "gold", text: "The scale bar of the sheet is not the scale the few readable dimensions give." },
  SCALE_TEXT_REPAIRED: { tone: "gold", text: "The printed scale was misread (its quote marks were lost) and was put right using the scale bar." },
  SCALE_FROM_TITLE_STRIP: { tone: "gold", text: "The scale was read from the scale box of the title strip. No dimension confirmed it." },
  NOT_TO_SCALE: { tone: "red", text: "The sheet says NOT TO SCALE. Only measure along printed dimensions." },
  MULTI_SCALE: { tone: "gold", text: "Different parts of the sheet are drawn at different scales." },
  FEW_DIMENSIONS: { tone: "gold", text: "Few printed dimensions were found, so the scale is less certain." },
  NO_SCALE_FOUND: { tone: "slate", text: "No scale text was found." },
  NO_TEXT_LAYER: { tone: "gold", text: "This sheet has no readable text (outlined or scanned), so printed dimensions could not be used." },
  RASTER_SHEET: { tone: "gold", text: "This sheet is a scanned image. Measure by hand; precision is lower." },
  PAGE_TRUNCATED: { tone: "gold", text: "The sheet was very large and only part of it was read." },
  NON_STANDARD_PAPER: { tone: "slate", text: "The paper size is not a standard size, which can mean the sheet was resized." },
};

export function noteInfo(note: ScaleNote): { tone: Tone; text: string } {
  return NOTE_TEXT[note.code] ?? { tone: "slate", text: typeof note.message === "string" ? note.message : note.code };
}

export function needsAcknowledgement(scale: DetectedScale | undefined): boolean {
  if (!scale) return false;
  if (scale.agreement === "CONFLICT" || scale.agreement === "CONFLICT_UNRESOLVED" || scale.agreement === "WITNESS_CONFLICT") return true;
  return (scale.notes ?? []).some((n) => n.code === "SHEET_REDUCED" || n.code === "SCALE_CONFLICT" || n.code === "SCALE_CONFLICT_UNRESOLVED" || n.code === "SCALE_WITNESS_CONFLICT" || n.code === "NOT_TO_SCALE");
}

export function checkBand(errorPct: string | number | null | undefined): { tone: Tone; text: string } {
  if (errorPct === null || errorPct === undefined || errorPct === "") return { tone: "gold", text: "No check dimension" };
  const e = Math.abs(Number(errorPct));
  if (!Number.isFinite(e)) return { tone: "gold", text: "No check dimension" };
  if (e <= 0.5) return { tone: "green", text: `Check dimension agrees (${e.toFixed(2)}%)` };
  if (e <= 1) return { tone: "green", text: `Check dimension agrees within 1% (${e.toFixed(2)}%)` };
  if (e <= 2) return { tone: "gold", text: `Check dimension is off by ${e.toFixed(2)}%` };
  return { tone: "red", text: `Check dimension is off by ${e.toFixed(2)}%: not usable` };
}
import type { PdfReadability, ReadabilityReason, ReadabilityState } from "../types/takeoff.types";

export const READABILITY_TEXT: Record<Exclude<ReadabilityState, "NOT_READ">, string> = {
  READABLE: "Read with no open question",
  READ_WITH_QUESTIONS: "Read, with questions",
  READ_BADLY: "Read badly",
};

export const READABILITY_TONE: Record<Exclude<ReadabilityState, "NOT_READ">, "green" | "gold" | "red"> = {
  READABLE: "green",
  READ_WITH_QUESTIONS: "gold",
  READ_BADLY: "red",
};

export const READABILITY_REASON_TEXT: Record<string, string> = {
  TEXT_NOT_RECOVERED: "Lettering drawn as outlines could not be read",
  STAGE_FAILED: "A reading step failed",
  SCALE_LOOKS_WRONG: "The scale looks wrong",
  SCALE_CONFLICT: "The scale is in conflict",
  SCALE_UNVERIFIED: "The scale is not checked against a dimension",
  TEXT_FROM_PICTURE: "Lettering read from the picture",
  TIME_LIMIT: "Reading took too long",
  VALUES_DISAGREE: "The drawing disagrees with itself",
  SHEET_KIND_UNKNOWN: "Kind of sheet not known",
};

export function reasonTitle(reason: ReadabilityReason): string {
  return READABILITY_REASON_TEXT[reason.code] ?? reason.code;
}

export function pagesLabel(pages: number[], sheets: number): string {
  if (!pages.length) return "";
  const shown = pages.join(", ");
  return sheets > pages.length ? `page ${shown} and ${sheets - pages.length} more` : `page ${shown}`;
}

export function shownState(value: PdfReadability | null | undefined): Exclude<ReadabilityState, "NOT_READ"> | null {
  if (!value || value.state === "NOT_READ") return null;
  return value.state;
}

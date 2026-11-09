import { formatCurrency } from "../../../utils/drawings-boq.utils";
import type { ReviewKind, ReviewLine, ReviewRow, ReviewSource } from "../types/review.types";

export const KINDS: ReviewKind[] = ["AI_CANDIDATE", "READING", "CONFLICT", "QUESTION"];

export const KIND_TEXT: Record<ReviewKind, string> = {
  AI_CANDIDATE: "AI read",
  READING: "Reading to confirm",
  CONFLICT: "Printed two ways",
  QUESTION: "Question",
};

export const SOURCE_TEXT: Record<ReviewSource, string> = {
  PRINTED: "Printed on the sheet",
  AI_READ: "Read by the AI",
  ASSUMED: "Assumed",
};

export const SOURCE_TONE: Record<ReviewSource, "green" | "gold" | "blue"> = {
  PRINTED: "green",
  AI_READ: "blue",
  ASSUMED: "gold",
};

export const REASON_TEXT: Record<string, string> = {
  WRONG_NUMBER: "The number is wrong",
  WRONG_UNIT: "The unit is wrong",
  WRONG_NAME: "The name is wrong",
  WRONG_FLOOR: "It belongs to another floor",
  NOT_ON_DRAWING: "The drawing does not say this",
  ALREADY_COUNTED: "It is already counted",
  NOT_FOR_THIS_JOB: "It is not for this job",
  DRAWING_IS_WRONG: "The drawing itself is wrong",
  OTHER: "Another reason",
};

export function reasonsFor(row: ReviewRow, action: "correct" | "reject"): string[] {
  return row.reasons?.[action] ?? [];
}

export function moneyText(value: number | null): string {
  return value === null ? "No rate loaded" : formatCurrency(value);
}

export function lineQuantity(line: ReviewLine): string {
  if (line.quantity === null) return "not quantified yet";
  const range = line.range ? ` (${line.range[0]} to ${line.range[1]})` : "";
  return `${line.quantity} ${line.unit ?? ""}${range}`.trim();
}

export function visibleRows(rows: ReviewRow[], kind: ReviewKind | null, openOnly: boolean): ReviewRow[] {
  return rows.filter((r) => (kind === null || r.kind === kind) && (!openOnly || r.state === "OPEN"));
}

export function countsByKind(rows: ReviewRow[], openOnly: boolean): Record<ReviewKind, number> {
  const out: Record<ReviewKind, number> = { AI_CANDIDATE: 0, READING: 0, CONFLICT: 0, QUESTION: 0 };
  for (const r of rows) if (!openOnly || r.state === "OPEN") out[r.kind] += 1;
  return out;
}

export function touchedText(touched: string[]): string {
  return touched.length === 0 ? "No BOQ item changed." : `Re-ran ${touched.length} item${touched.length === 1 ? "" : "s"}: ${touched.join(", ")}.`;
}

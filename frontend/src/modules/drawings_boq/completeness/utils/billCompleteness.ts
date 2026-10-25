import type { BillCompleteness, CompletenessSeverity, CompletenessStep, CompletenessVerdict } from "../types/billCompleteness.types";

export function verdictTone(v: CompletenessVerdict): "green" | "gold" | "red" {
  return v === "EMPTY" ? "red" : v === "PARTIAL" ? "gold" : "green";
}

export function severityTone(s: CompletenessSeverity): "red" | "gold" | "slate" {
  return s === "BLOCKER" ? "red" : s === "WARNING" ? "gold" : "slate";
}

export function stepTone(s: CompletenessStep): "green" | "gold" | "slate" {
  return s.ran ? "green" : s.gap ? "gold" : "slate";
}

export function verdictText(v: CompletenessVerdict): string {
  return v === "EMPTY" ? "The bill is empty or nearly empty" : v === "PARTIAL" ? "The bill is short" : "No known gaps";
}

export function funnelLine(d: BillCompleteness): string {
  const { confirmed, draft, undecided } = d.funnel;
  const total = confirmed + draft + undecided;
  if (total === 0) return "";
  return `${confirmed} of ${total} read items are in the run` + (draft ? `, ${draft} accepted but not confirmed` : "") + (undecided ? `, ${undecided} not accepted` : "");
}

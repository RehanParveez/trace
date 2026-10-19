import type { TakeoffCandidate } from "../types/takeoff.types";
import { confidenceLevel } from "./candidates";

export type OverlayMode = "ITEM" | "CHECK" | "GRADE";
export type CheckResult = "ok" | "warns" | "error";

export const OVERLAY_MODES: OverlayMode[] = ["ITEM", "CHECK", "GRADE"];
export const MODE_TEXT: Record<OverlayMode, string> = { ITEM: "By work item", CHECK: "By check result", GRADE: "By grade" };

export const CHECK_COLOUR: Record<CheckResult, string> = { ok: "#1e9d63", warns: "#d98a1f", error: "#c24a3a" };
export const CHECK_TEXT: Record<CheckResult, string> = { ok: "No warning", warns: "A warning on it", error: "An error on it" };
export const GRADE_COLOUR: Record<"high" | "medium" | "low", string> = { high: "#1e9d63", medium: "#d98a1f", low: "#c24a3a" };
export const GRADE_TEXT: Record<"high" | "medium" | "low", string> = { high: "High (85% and over)", medium: "Medium", low: "Low (under 65%)" };

export function checkResult(c: Pick<TakeoffCandidate, "status" | "notes">): CheckResult {
  if (c.status === "INVALID" || (c.notes ?? []).some((n) => n.severity === "error")) return "error";
  if (c.status === "WARNING" || (c.notes ?? []).some((n) => n.severity === "warning")) return "warns";
  return "ok";
}

export function markColours(mode: OverlayMode, candidates: readonly TakeoffCandidate[]): Record<string, string> {
  const out: Record<string, string> = {};
  if (mode === "ITEM") return out;
  for (const c of candidates) {
    if (c.decision !== "ACCEPTED" || !c.measurement_id) continue;
    out[c.measurement_id] = mode === "CHECK" ? CHECK_COLOUR[checkResult(c)] : GRADE_COLOUR[confidenceLevel(c.confidence)];
  }
  return out;
}

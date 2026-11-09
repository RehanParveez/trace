import type { QsMethodAspect, QsMethodProfile, QsMethodRow, QsMethodState } from "../types/qsMethods.types";

export const ASPECT_ORDER: QsMethodAspect[] = ["deductions", "faces", "heights", "laps", "wastage", "working_space", "projections"];

export const ASPECT_TEXT: Record<QsMethodAspect, string> = {
  deductions: "What is taken off",
  faces: "Which faces",
  heights: "Heights and thicknesses",
  laps: "Laps and steel allowance",
  wastage: "Wastage and extras",
  working_space: "Working space and strips",
  projections: "Projections and outside work",
};

export const STATE_TEXT: Record<QsMethodState, string> = {
  IN_FORCE: "In your rule book",
  SAME_AS_TRACE: "Trace already does this",
  WOULD_CHANGE: "Changes what Trace measures",
  YOURS: "You set your own figure; kept",
  NOT_SETTABLE: "Decided for each drawing",
};

export const STATE_TONE: Record<QsMethodState, "green" | "blue" | "gold" | "slate"> = {
  IN_FORCE: "green",
  SAME_AS_TRACE: "slate",
  WOULD_CHANGE: "gold",
  YOURS: "blue",
  NOT_SETTABLE: "slate",
};

export function valueText(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).map(([k, v]) => `${k} ${String(v)}`).join(", ");
  }
  return String(value);
}

export function scopeText(scope: Record<string, unknown>): string {
  const parts = Object.entries(scope ?? {}).map(([k, v]) => `${k} ${String(v)}`);
  return parts.length ? ` (${parts.join(", ")})` : "";
}

export function byAspect(methods: QsMethodRow[]): Array<[QsMethodAspect, QsMethodRow[]]> {
  const out: Array<[QsMethodAspect, QsMethodRow[]]> = [];
  for (const aspect of ASPECT_ORDER) {
    const rows = methods.filter((m) => m.aspect === aspect);
    if (rows.length) out.push([aspect, rows]);
  }
  return out;
}

export function summaryText(profile: QsMethodProfile): string {
  const parts = [`${profile.methods.length} methods`];
  if (profile.would_change) parts.push(`${profile.would_change} change what Trace measures`);
  if (profile.same_as_trace) parts.push(`${profile.same_as_trace} Trace already does`);
  if (profile.kept) parts.push(`${profile.kept} of yours kept`);
  if (profile.not_settable) parts.push(`${profile.not_settable} decided for each drawing`);
  return parts.join(", ");
}

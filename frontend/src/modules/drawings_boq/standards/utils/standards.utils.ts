import type { IssueSeverity, RuleSetStatus } from "../types/standards.types";

export const CANONICAL_UNITS = ["m3", "m2", "m", "kg", "nos"] as const;

export function formatRuleSetStatus(status: RuleSetStatus): string {
  switch (status) {
    case "DRAFT": return "Draft";
    case "ACTIVE": return "Active";
    case "SUPERSEDED": return "Superseded";
    case "ARCHIVED": return "Archived";
    default: return status;
  }
}

export function getRuleSetStatusTone(status: RuleSetStatus): "green" | "gold" | "red" | "slate" | "blue" {
  switch (status) {
    case "ACTIVE": return "green";
    case "DRAFT": return "gold";
    default: return "slate";
  }
}

export function getIssueTone(severity: IssueSeverity): "green" | "gold" | "red" | "slate" | "blue" {
  return severity === "error" ? "red" : severity === "warning" ? "gold" : "blue";
}

export function formatFactor(value: number | string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  const pct = (numeric - 1) * 100;
  if (Math.abs(pct) < 1e-9) return "No extra";
  return `+${Number.isInteger(pct) ? pct : pct.toFixed(2)}%`;
}

export function formatAreaRange(lower: number | string, upper: number | string | null): string {
  return upper == null || upper === "" ? `≥ ${Number(lower)} m²` : `${Number(lower)} to < ${Number(upper)} m²`;
}

export function shortHash(hash: string | null): string {
  return hash ? hash.slice(0, 10) : "—";
}

export function formatRuleSetDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function ruleSetLabel(code: string, version: number): string {
  return `${code} v${version}`;
}
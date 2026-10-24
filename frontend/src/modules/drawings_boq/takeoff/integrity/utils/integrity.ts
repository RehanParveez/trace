import type { IntegrityCheck, IntegrityReport, IntegrityState } from "../types/integrity.types";

export const STATE_TEXT: Record<IntegrityState, string> = {
  OK: "Nothing to look at",
  PARTIAL: "Partly read",
  LOOK: "Look before you rely on it",
};

export const STATE_TONE: Record<IntegrityState, "green" | "red" | "blue" | "gold" | "slate"> = { OK: "green", PARTIAL: "gold", LOOK: "red" };

export function toLookAt(report: IntegrityReport | undefined): IntegrityCheck[] {
  return (report?.checks ?? []).filter((c) => c.status !== "OK");
}

export function okChecks(report: IntegrityReport | undefined): IntegrityCheck[] {
  return (report?.checks ?? []).filter((c) => c.status === "OK");
}

export function pagesText(pages: number[] | null | undefined): string {
  const p = [...new Set(pages ?? [])].sort((a, b) => a - b);
  if (!p.length) return "";
  return `${p.length === 1 ? "page" : "pages"} ${p.join(", ")}`;
}

export function summaryLine(report: IntegrityReport | undefined): string {
  if (!report || !report.checks.length) return "";
  const s = report.summary;
  const bits: string[] = [];
  if (s.warn) bits.push(`${s.warn} to look at`);
  if (s.info) bits.push(`${s.info} for information`);
  if (s.ok) bits.push(`${s.ok} fine`);
  return bits.join(" · ");
}

export function isEmpty(report: IntegrityReport | undefined): boolean {
  return !report || report.checks.length === 0;
}

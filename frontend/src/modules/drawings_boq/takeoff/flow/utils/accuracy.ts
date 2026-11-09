import type { AccuracyBandRow, AccuracyCoverage, AccuracyReport, RankedBy } from "../types/flow.types";

export const RANK_TEXT: Record<RankedBy, string> = {
  LOW_CONFIDENCE_MONEY: "Lines with the most money at Low confidence",
  LOW_CONFIDENCE_COUNT: "Lines at Low confidence (no rates are loaded, so there is no money to rank by)",
  ASSUMED_MONEY: "Lines with the most money resting on assumptions (confidence is not shown)",
  ASSUMED_NO_RATES: "Lines resting on assumptions or open questions (no rates are loaded, so there is no money to rank by)",
};

export function pctText(value: number | null | undefined): string {
  return value === null || value === undefined ? "-" : `${value.toFixed(1)}%`;
}

export function notReadTotal(coverage: AccuracyCoverage): number {
  return coverage.sections.reduce((sum, s) => sum + s.NOT_READ, 0);
}

export function sectionsByGap(coverage: AccuracyCoverage): AccuracyCoverage["sections"] {
  const gap = coverage.sections.filter((s) => s.NOT_READ > 0);
  return [...gap, ...coverage.sections.filter((s) => s.NOT_READ === 0)];
}

export function bandTone(band: AccuracyBandRow["band"] | null): "green" | "gold" | "blue" | "slate" {
  return band === "High" ? "green" : band === "Low" ? "gold" : band === "Medium" ? "blue" : "slate";
}

export function bandShare(rows: AccuracyBandRow[]): number {
  return Math.round(rows.reduce((sum, r) => sum + r.pct, 0) * 10) / 10;
}

export function hasConfidence(report: AccuracyReport): boolean {
  return report.confidence.shown === true && report.confidence.bands.length > 0;
}

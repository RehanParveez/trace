import type { RangeTotal } from "../types/takeoff.types";
import { EVIDENCE_GRADES, type EvidenceGrade } from "./evidence";

export interface MixSlice { grade: EvidenceGrade; share: number }

export function mixSlices(mix: Record<string, number> | undefined): MixSlice[] {
  if (!mix) return [];
  return EVIDENCE_GRADES.map((grade) => ({ grade, share: Number(mix[grade] ?? 0) || 0 })).filter((s) => s.share > 0);
}

export function sharePct(share: number): string {
  return `${Math.round(share * 100)}%`;
}

function figure(v: number): string {
  const rounded = Math.abs(v) >= 100 ? Math.round(v) : Math.round(v * 100) / 100;
  return rounded.toLocaleString("en-US");
}

export function totalLine(t: RangeTotal): string {
  return `${figure(t.low)} to ${figure(t.high)} ${t.unit}, likely ${figure(t.likely)} ${t.unit}`.replace(/\s+/g, " ");
}

export function totalCaveat(t: RangeTotal): string {
  const parts: string[] = [];
  if (t.unbounded > 0) parts.push(`${t.unbounded} of ${t.rows} items have no range because a value is missing and are not in it`);
  if (t.leaves_out > 0) parts.push(`${t.leaves_out} leave something out (a landing, a roof projection, a well to deduct)`);
  return parts.join("; ");
}

export function rangedTotals(totals: RangeTotal[] | undefined): RangeTotal[] {
  return (totals ?? []).filter((t) => t.unit && t.unit !== "nos");
}

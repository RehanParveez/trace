import type { OneTotalPrefer, OneTotalRule, OneTotalRuleKind, OneTotalSources } from "../api/oneTotal.api";
import type { PdfVariance } from "../types/drawings-boq.types";

export const PREFER_LABEL: Record<OneTotalPrefer, string> = {
  DRAWING: "Use the drawing",
  MODEL: "Use the model",
  BOTH: "Count both",
};

export const PREFER_HELP: Record<OneTotalPrefer, string> = {
  DRAWING: "Count the drawing's quantity and set the model's aside.",
  MODEL: "Count the model's quantity and set the drawing's aside.",
  BOTH: "Count both. Use it only when the model and the drawing show two different members.",
};

export const PREFER_ORDER: OneTotalPrefer[] = ["DRAWING", "MODEL", "BOTH"];

export function normMark(text: string | null | undefined): string {
  return String(text ?? "").replace(/[^0-9A-Za-z]/g, "").toUpperCase();
}

export function ruleFor(rules: OneTotalRule[] | undefined, kind: OneTotalRuleKind, mark: string | null | undefined, levelName: string | null | undefined): OneTotalRule | null {
  const key = normMark(mark);
  const level = (levelName ?? "").trim().toUpperCase();
  return (rules ?? []).find((r) => r.kind === kind && normMark(r.mark) === key && r.level_name.trim().toUpperCase() === level) ?? null;
}

export function scopeWords(r: { kind: OneTotalRuleKind | string; mark: string; level_name: string }): string {
  const what = r.kind === "ITEM" ? `work item ${r.mark || "—"}` : r.mark ? `${r.mark}` : `every ${String(r.kind).toLowerCase()} mark`;
  return r.level_name ? `${what} on ${r.level_name}` : `${what}, every storey`;
}

export interface SourcesNotice {
  tone: "ok" | "warn" | "none";
  text: string;
  canSwitchOn: boolean;
  canGoAutomatic: boolean;
  canSwitchOff: boolean;
}

export function sourcesNotice(s: OneTotalSources | null | undefined): SourcesNotice {
  const none: SourcesNotice = { tone: "none", text: "", canSwitchOn: false, canGoAutomatic: false, canSwitchOff: false };
  if (!s || !s.both) return none;
  const have = `This project has ${s.model_drawings} model${s.model_drawings === 1 ? "" : "s"} and ${s.pdf_drawings} drawing${s.pdf_drawings === 1 ? "" : "s"} with confirmed measurements.`;
  if (s.one_total.value === 1) {
    return s.one_total.source === "detected"
      ? { tone: "ok", text: `${have} One total is on, found from that: a member in both is counted once.`, canSwitchOn: false, canGoAutomatic: false, canSwitchOff: true }
      : { tone: "ok", text: `${have} One total is on, as you saved it: a member in both is counted once.`, canSwitchOn: false, canGoAutomatic: true, canSwitchOff: true };
  }
  return { tone: "warn", text: `${have} One total is off, as you saved it, so a column that is in both is counted twice or the drawing's is left out whole.`, canSwitchOn: true, canGoAutomatic: true, canSwitchOff: false };
}

export interface ItemClaimView {
  code: string;
  levelName: string | null;
  unit: string;
  drawing: string;
  model: string;
  variancePct: string;
  over: boolean;
  rule: OneTotalPrefer | null;
}

export function itemClaims(variances: PdfVariance[] | undefined | null): ItemClaimView[] {
  return (variances ?? [])
    .map((v) => ({ code: v.work_item_code, levelName: v.level_name ?? null, unit: v.unit, drawing: v.pdf_quantity, model: v.model_quantity, variancePct: v.variance_pct, over: Boolean(v.over_tolerance), rule: v.rule ?? null }))
    .sort((a, b) => Number(b.over) - Number(a.over) || a.code.localeCompare(b.code) || String(a.levelName).localeCompare(String(b.levelName)));
}

export function ruleWords(prefer: string | null | undefined): string {
  switch (prefer) {
    case "DRAWING":
      return "your rule: the drawing";
    case "MODEL":
      return "your rule: the model";
    case "BOTH":
      return "your rule: both";
    default:
      return "";
  }
}

export function ruleKindOf(category: string): OneTotalRuleKind {
  switch (category) {
    case "FOOTING":
    case "SLAB":
    case "STAIR":
    case "COLUMN":
      return category;
    default:
      return "BEAM";
  }
}

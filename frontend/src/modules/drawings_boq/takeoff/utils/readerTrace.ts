import type { ReaderTrace, TraceRule, TraceSheet } from "../types/takeoff.types";

export function basisLabel(basis: TraceRule["basis"]): string {
  return basis === "TUNED" ? "Tuned on one drawing" : basis === "STANDARD" ? "From a standard" : "A default";
}

export function basisTone(basis: TraceRule["basis"]): "red" | "gold" | "green" {
  return basis === "TUNED" ? "red" : basis === "DEFAULT" ? "gold" : "green";
}

export function decidedByLabel(by: string): string {
  switch (by) {
    case "DIMENSIONS": return "Scale read from the drawn dimensions";
    case "PRINTED_SCALE": return "Scale taken from the printed scale";
    case "OVERRIDE": return "Scale set by a person on this sheet";
    case "PERSON": return "Scale confirmed by a person";
    default: return "Scale source not known";
  }
}

export function summaryLine(data: ReaderTrace | undefined): string {
  if (!data || !data.sheets.length) return "";
  const s = data.summary;
  const bits = [s.sheets === 1 ? "1 sheet" : `${s.sheets} sheets`];
  if (s.tuned_rules_fired.length) bits.push(s.tuned_rules_fired.length === 1 ? "1 tuned rule fired" : `${s.tuned_rules_fired.length} tuned rules fired`);
  if (s.default_rules_fired.length) bits.push(s.default_rules_fired.length === 1 ? "1 default used" : `${s.default_rules_fired.length} defaults used`);
  return bits.join(" · ");
}

export function thresholdPairs(rule: TraceRule): string[] {
  return Object.entries(rule.thresholds).map(([k, v]) => `${k.replace(/_/g, " ").toLowerCase()} ${v}`);
}

export function orderedRules(sheet: TraceSheet): TraceRule[] {
  const rank = { TUNED: 0, DEFAULT: 1, STANDARD: 2 } as const;
  return [...sheet.rules].sort((a, b) => rank[a.basis] - rank[b.basis] || b.items - a.items || a.id.localeCompare(b.id));
}

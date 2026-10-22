import type {DecideBody, Decision, DecisionAction, Decisions, Ladder, Patch, PatchHunk, PlanBody, SweepItem, TuningParam, TuningPlan, TuningRegistry, TuningRule,
} from "../types/tuning.types";
import { familyName, isUuid, percent } from "../../reading_score/utils/readingScore";

export const ACTION_TEXT: Record<DecisionAction, string> = {
  CHANGE: "Change proposed", KEEP: "Keep", INSUFFICIENT: "Not enough labels", INERT: "No effect on these sheets", REPORT_ONLY: "Reported only", INCOMPLETE: "Could not compare",
};
export function actionLabel(a: DecisionAction): string {
  return ACTION_TEXT[a] ?? a;
}
export function actionTone(a: DecisionAction): "green" | "red" | "gold" | "slate" {
  return a === "CHANGE" || a === "REPORT_ONLY" ? "gold" : a === "INCOMPLETE" ? "red" : "slate";
}

export function num(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return String(Number(v.toFixed(4)));
}

export function valueText(v: number | null | undefined, unit: string): string {
  const n = num(v);
  return n !== "—" && unit === "mm" ? `${n} mm` : n;
}

export function isChanged(p: TuningParam): boolean {
  return Math.abs(p.live - p.hand) > 1e-9 * Math.max(1, Math.abs(p.hand));
}

export function statusText(p: TuningParam): string {
  if (p.status === "SWEEPABLE") return p.calibratable ? "A score can calibrate it" : "Swept for information; a score does not change it";
  return p.reasons[0] ?? "Cannot be swept";
}

export type ParamFilter = "ALL" | "CALIBRATABLE" | "NOT_SWEEPABLE" | "CHANGED";
export const FILTER_TEXT: Record<ParamFilter, string> = { ALL: "All", CALIBRATABLE: "A score can calibrate", NOT_SWEEPABLE: "Cannot be swept", CHANGED: "Changed from the hand value" };

export function filterParams(params: TuningParam[], filter: ParamFilter): TuningParam[] {
  if (filter === "CALIBRATABLE") return params.filter((p) => p.calibratable);
  if (filter === "NOT_SWEEPABLE") return params.filter((p) => p.status === "NOT_SWEEPABLE");
  if (filter === "CHANGED") return params.filter(isChanged);
  return params;
}

export interface RuleGroup {
  rule: TuningRule;
  params: TuningParam[];
}

/** The rules in the order of the rule register, each with the constants the filter keeps; a rule with none is shown only when nothing is filtered. */
export function groupedRules(reg: TuningRegistry, filter: ParamFilter): RuleGroup[] {
  const byKey = new Map(reg.params.map((p) => [p.key, p]));
  const out: RuleGroup[] = [];
  for (const rule of reg.rules) {
    const mine = filterParams(rule.params.map((k) => byKey.get(k)).filter((p): p is TuningParam => Boolean(p)), filter);
    if (mine.length || (filter === "ALL" && rule.params.length === 0)) out.push({ rule, params: mine });
  }
  return out;
}

export function basisText(b: string): string {
  return b === "TUNED" ? "Tuned by hand" : b === "STANDARD" ? "From a standard" : b === "DEFAULT" ? "Assumed" : b;
}

export function familiesText(families: string[]): string {
  if (!families.length) return "—";
  if (families.includes("*")) return "Every kind";
  return families.map((f) => familyName(f)).join(", ");
}

export function registrySummary(reg: TuningRegistry): string {
  const tuned = reg.rules.filter((r) => r.basis === "TUNED");
  const calibrated = new Set(reg.rules.filter((r) => r.calibratable > 0).map((r) => r.id));
  const calibratable = reg.params.filter((p) => p.calibratable).length;
  const changed = reg.params.filter(isChanged).length;
  return `${reg.params.length} constants in ${reg.rules.length} rules. ${calibratable} can be calibrated by a score, in ${calibrated.size} of the ${tuned.length} tuned rules. ${
    changed ? `${changed} changed from the hand value.` : "None changed from the hand value."}`;
}

export function driftLines(reg: TuningRegistry): string[] {
  return reg.ledger.drift;
}

export function unregisteredLine(reg: TuningRegistry): string {
  const u = reg.unregistered;
  return u.total ? `${u.total} more numbers in ${u.modules.length} reader files are not in the register. Some are units or limits, some are tuned values that no rule lists yet.` : "";
}

export function estimateText(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return "";
  if (seconds < 90) return `about ${Math.max(1, Math.round(seconds))} seconds`;
  const m = seconds / 60;
  return m < 90 ? `about ${Math.round(m)} minutes` : `about ${(m / 60).toFixed(1)} hours`;
}

export const LADDER_TEXT: Record<Ladder, string> = { narrow: "Narrow (2 values each)", standard: "Standard (4 values each)", wide: "Wide (6 values each)" };

export interface PlanForm {
  rule: string;
  ladder: Ladder;
  copies: string;
  controlSeconds: string;
  includeUnswept: boolean;
}

export const MAX_COPIES = 12;

export function planBody(f: PlanForm): { ok: true; body: PlanBody } | { ok: false; error: string } {
  const copies = Array.from(new Set(f.copies.split(/[\s,;]+/).map((s) => s.trim()).filter(Boolean)));
  const bad = copies.find((c) => !isUuid(c));
  if (bad) return { ok: false, error: `"${bad.length > 40 ? `${bad.slice(0, 40)}…` : bad}" is not a drawing id.` };
  if (copies.length > MAX_COPIES) return { ok: false, error: `At most ${MAX_COPIES} copies.` };
  let control: number | undefined;
  if (f.controlSeconds.trim()) {
    control = Number(f.controlSeconds);
    if (!Number.isFinite(control) || control < 0) return { ok: false, error: "The time of one run must be a number of seconds." };
  }
  const body: PlanBody = { ladder: f.ladder, copies };
  if (f.rule) body.rules = [f.rule];
  if (control !== undefined) body.control_seconds = control;
  if (f.includeUnswept) body.include_unswept = true;
  return { ok: true, body };
}

export function planLine(plan: TuningPlan): string {
  const est = estimateText(plan.estimate_seconds);
  return `${plan.constants} constant${plan.constants === 1 ? "" : "s"}, ${plan.n_cells} run${plan.n_cells === 1 ? "" : "s"} of the reader${est ? `, ${est}` : ""}.`;
}

export function sweepLine(s: SweepItem): string {
  const parts = [`${s.cells} runs of ${s.constants} constant${s.constants === 1 ? "" : "s"}`, `${s.label_count} label${s.label_count === 1 ? "" : "s"}`];
  parts.push(s.changes ? `${s.changes} change${s.changes === 1 ? "" : "s"} proposed` : "no change proposed");
  if (s.seconds) parts.push(estimateText(s.seconds).replace("about ", ""));
  return parts.join(" · ");
}

export function sweepNotes(s: SweepItem, current: number): string[] {
  const out: string[] = [];
  if (s.status === "PARTIAL") out.push("The time allowed ran out, so some constants were not swept.");
  if (s.stale) out.push(`The reader has changed since this sweep (version ${s.extract_version}, now ${current}). Sweep again before applying anything.`);
  return out;
}

export function proposedText(d: Decision, unit = ""): string {
  return d.proposed === null ? "" : valueText(d.proposed, unit);
}

export function evidenceLine(d: Decision): string {
  const e = d.evidence;
  if (d.action === "CHANGE" && e.chosen) {
    const kinds = (e.affected_families ?? []).map(familyName).join(", ");
    return `F1 of ${kinds} on the complete sheets ${percent(e.f1_now)} → ${percent(e.chosen.f1)} over ${e.labels ?? 0} labelled members.`;
  }
  if (d.action === "INSUFFICIENT") return `${e.labels ?? 0} labelled members of the kinds this is for; ${e.needed ?? "more"} are needed.`;
  return d.reasons[0] ?? "";
}

export function guardLines(d: Decision): string[] {
  return (d.evidence.guards ?? []).map((g) => `${g.ok ? "✓" : "✗"} ${g.detail}`);
}

export function countsLine(counts: Partial<Record<DecisionAction, number>>): string {
  const order: DecisionAction[] = ["CHANGE", "KEEP", "INSUFFICIENT", "INERT", "REPORT_ONLY", "INCOMPLETE"];
  const parts = order.filter((a) => counts[a]).map((a) => `${counts[a]} ${ACTION_TEXT[a].toLowerCase()}`);
  return parts.join(" · ");
}

export function jointLine(d: Decisions): string {
  if (!d.joint) return d.counts.CHANGE && d.counts.CHANGE > 1 ? "The changes were checked one at a time, not together." : "";
  return d.joint.ok ? `The ${d.joint.changes.length} changes were checked together and hold.` : `The ${d.joint.changes.length} changes do NOT hold together. Apply one at a time, the largest gain first.`;
}

export function hunkText(h: PatchHunk): string {
  if (h.error) return `${h.key}: ${h.error}`;
  return `File: ${h.file}\nFIND (appears once):\n${h.find}\nREPLACE WITH:\n${h.replace}`;
}

export function hasPatch(p: Patch | undefined): boolean {
  return Boolean(p && (p.hunks.length || p.version || p.ledger_json));
}

export function patchText(p: Patch): string {
  const parts = p.hunks.map(hunkText);
  if (p.version) parts.push(p.version.error ?? `File: ${p.version.file}\nFIND:\n${p.version.find}\nREPLACE WITH:\n${p.version.replace}`);
  if (p.ledger_json) parts.push(`Replace app/modules/drawings_boq/takeoff/tuning/ledger.json with:\n${p.ledger_json}`);
  return parts.join("\n\n");
}

export function decideBody(minLabels: string, minGain: string): { ok: true; body: DecideBody } | { ok: false; error: string } {
  const body: DecideBody = {};
  if (minLabels.trim()) {
    const n = Number(minLabels);
    if (!Number.isInteger(n) || n < 1) return { ok: false, error: "The number of labels must be a whole number, 1 or more." };
    body.min_labels = n;
  }
  if (minGain.trim()) {
    const g = Number(minGain);
    if (!Number.isFinite(g) || g < 0 || g > 1) return { ok: false, error: "The gain is a share between 0 and 1, for example 0.01." };
    body.min_gain = g;
  }
  return { ok: true, body };
}

export function planWarnings(plan: TuningPlan): string[] {
  const out = [...plan.warnings];
  if (plan.left_out.length) out.push(`${plan.left_out.length} not swept: ${plan.left_out.slice(0, 3).map((l) => l.key.replace(/^C\./, "")).join(", ")}${plan.left_out.length > 3 ? "…" : ""}.`);
  return out;
}

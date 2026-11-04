import type { SteelDiameter, SteelFigures, SteelFormula, SteelFiguresSource } from "../types/steelFigures.types";

export const FORMULA_ORDER: SteelFormula[] = ["REBAR_BBS_WEIGHT", "REBAR_BBS_AUDITED", "REBAR_RULE_ESTIMATE"];
export const SOURCE_OF: Record<SteelFormula, SteelFiguresSource> = { REBAR_BBS_WEIGHT: "BBS_WEIGHT", REBAR_BBS_AUDITED: "BBS_AUDITED", REBAR_RULE_ESTIMATE: "RULE_ESTIMATE" };
export const FORMULA_WORDS: Record<SteelFormula, string> = {
  REBAR_BBS_WEIGHT: "Bar schedule as billed",
  REBAR_BBS_AUDITED: "Bar schedule, audited",
  REBAR_RULE_ESTIMATE: "Trace rule estimate",
};

function n(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const v = Number(value);
  return Number.isFinite(v) ? v : null;
}

export function kg2(value: string | null | undefined): string {
  const v = n(value);
  return v === null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function tonnes(value: string | null | undefined): string {
  const v = n(value);
  return v === null ? "—" : (v / 1000).toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

export function signed(value: string | null | undefined): string {
  const v = n(value);
  if (v === null) return "—";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function figureCards(f: SteelFigures): { formula: SteelFormula; words: string; kg: string | null; note: string | null; used: boolean }[] {
  return FORMULA_ORDER.map((formula) => ({
    formula, words: FORMULA_WORDS[formula], kg: f.figures[formula]?.kg ?? null, note: f.figures[formula]?.note ?? null,
    used: f.line.formula === formula,
  }));
}

export function gap(a: string | null | undefined, b: string | null | undefined): string | null {
  const x = n(a), y = n(b);
  return x === null || y === null ? null : String(y - x);
}

export function diameterSum(rows: SteelDiameter[], unattributed: string | null): number {
  return rows.reduce((sum, r) => sum + (n(r.audited_kg) ?? 0), 0) + (n(unattributed) ?? 0);
}

export function openSentence(f: SteelFigures): string | null {
  const o = f.open_findings;
  if (!o.count) return null;
  const classes = Object.entries(o.by_class).map(([k, v]) => `${v} ${k}`).join(", ");
  return `${o.count} open finding${o.count === 1 ? "" : "s"} (${classes}), ${signed(o.effect_kg)} kg not applied`;
}

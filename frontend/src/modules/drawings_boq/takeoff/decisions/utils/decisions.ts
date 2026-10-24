import type { DecisionEffect, DecisionFigure, DecisionItem, DecisionsReport } from "../types/decisions.types";

export const FIGURE_LABEL: Record<string, string> = {
  wall_area: "wall area",
  brick: "brick",
  band_concrete: "roof beam, band and lintel concrete",
  lintel_off: "lintel concrete taken off the brick",
  lintels: "lintels",
  plaster: "plaster",
  paint: "paint",
  rcc_wall: "RCC wall concrete",
  wall_formwork: "wall formwork",
};

const UNIT_TEXT: Record<string, string> = { m2: "m²", m3: "m³", cft: "cft", nos: "" };

export function unitText(unit: string): string {
  return unit in UNIT_TEXT ? UNIT_TEXT[unit] : unit;
}

function number(v: number): string {
  return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

export function figureText(f: DecisionFigure): string {
  const u = unitText(f.unit);
  return `${FIGURE_LABEL[f.key] ?? f.key} ${number(f.value)}${u ? " " + u : ""}`;
}

export function diffText(e: DecisionEffect | null | undefined): string {
  if (!e) return "";
  if (e.diff == null) return "needs the sheets read with floor to floor first";
  if (e.diffs && e.diffs.length) {
    return e.diffs.map((d) => `${FIGURE_LABEL[d.key] ?? d.key} ${d.value > 0 ? "+" : "−"}${number(Math.abs(d.value))} ${unitText(d.unit)}`.trim()).join(" · ");
  }
  if (Math.abs(e.diff) < 0.005) return "no change";
  return `${e.diff > 0 ? "+" : "−"}${number(Math.abs(e.diff))} ${unitText(e.diff_unit)}`;
}

export function shown(report: DecisionsReport | undefined): DecisionItem[] {
  return (report?.items ?? []).filter((i) => i.applies || i.made_by_person);
}

export function pagesText(pages: number[] | null | undefined): string {
  const p = [...new Set(pages ?? [])].sort((a, b) => a - b);
  if (!p.length) return "";
  return `${p.length === 1 ? "page" : "pages"} ${p.join(", ")}`;
}

export function summaryLine(items: DecisionItem[]): string {
  const mine = items.filter((i) => i.made_by_person).length;
  const open = items.length - mine;
  const bits: string[] = [];
  if (mine) bits.push(`${mine} chosen by you`);
  if (open) bits.push(`${open} on the default`);
  return bits.join(" · ");
}

import type { IntensityStatus, SteelBasis, SteelFamilyRow, SteelGradeRow, SteelMarkRow, SteelSummary } from "../types/steelSummary.types";

export type Tone = "ok" | "warn" | "bad" | "muted";

export const BASIS_WORDS: Record<SteelBasis, string> = {
  PRINTED: "Bars printed on the drawing",
  SCHEDULE: "Bar bending schedule",
  ESTIMATE_PDF: "Estimated from the size (no bars printed)",
  ESTIMATE_MODEL: "Estimated from the model's concrete volume",
};

export const BASIS_TONE: Record<SteelBasis, Tone> = { PRINTED: "ok", SCHEDULE: "ok", ESTIMATE_PDF: "warn", ESTIMATE_MODEL: "warn" };

export const STATUS_WORDS: Record<IntensityStatus, string> = {
  IN_RANGE: "Within the usual range",
  BELOW_RANGE: "Below the usual range: bars may be missing",
  ABOVE_RANGE: "Above the usual range: check the bars or the size",
};

export const STATUS_TONE: Record<IntensityStatus, Tone> = { IN_RANGE: "ok", BELOW_RANGE: "warn", ABOVE_RANGE: "warn" };

export const WASTAGE_CHOICES: { value: string; label: string }[] = [
  { value: "", label: "As the run made it" },
  { value: "0", label: "None (bars as printed)" },
  { value: "3", label: "3 %" },
  { value: "5", label: "5 %" },
  { value: "7.5", label: "7.5 %" },
];

export const MAX_WASTAGE = 15;

export function parseWastage(text: string): number | null | "wrong" {
  const t = text.trim().replace(",", ".").replace(/%$/, "").trim();
  if (t === "") return null;
  if (!/^\d+(\.\d+)?$/.test(t)) return "wrong";
  const n = Number(t);
  return n >= 0 && n <= MAX_WASTAGE ? n : "wrong";
}

export function kgText(kg: number | null | undefined): string {
  if (kg === null || kg === undefined) return "-";
  return kg.toLocaleString("en-US", { maximumFractionDigits: Math.abs(kg) >= 100 ? 0 : 1 });
}

export function tonnesText(kg: number): string {
  return (kg / 1000).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function diaText(dia: number | string): string {
  const n = Number(dia);
  return `${Number.isInteger(n) ? n : n.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")} mm`;
}

export const NO_GRADE = "NONE";

export function gradeRows(summary: Pick<SteelSummary, "by_grade">): SteelGradeRow[] {
  const rows = summary.by_grade ?? [];
  return rows.length > 1 || rows.some((g) => g.grade !== NO_GRADE) ? rows : [];
}

export function gradeNote(rows: SteelGradeRow[]): string {
  const none = rows.find((g) => g.grade === NO_GRADE);
  const named = rows.filter((g) => g.grade !== NO_GRADE);
  if (!none || !named.length) return "";
  return `${kgText(none.kg)} kg in ${none.members} member${none.members === 1 ? "" : "s"} has no grade: no note on the drawing names a grade for that kind of member.`;
}

export function intensityText(f: Pick<SteelFamilyRow, "kg_per_m3" | "range">): string {
  if (f.kg_per_m3 === null) return "-";
  const usual = f.range ? ` (usual ${f.range[0]} to ${f.range[1]})` : "";
  return `${f.kg_per_m3.toLocaleString("en-US", { maximumFractionDigits: 1 })} kg/m3${usual}`;
}

export function asRunText(summary: Pick<SteelSummary, "wastage">): string {
  const w = summary.wastage;
  if (w.rows_with_bare_weight === 0) return "No row of this run keeps a bare weight, so the toggle changes nothing.";
  const own = w.as_run_pct.length === 0 ? "none" : w.as_run_pct.length === 1 ? `${w.as_run_pct[0]} %` : `between ${w.as_run_pct[0]} % and ${w.as_run_pct[w.as_run_pct.length - 1]} %`;
  const fixed = w.rows_fixed > 0 ? ` ${w.rows_fixed} rows (bar schedule and model estimates) keep their weight as it is.` : "";
  return `The run added ${own} to ${w.rows_with_bare_weight} rows read from the drawing.${fixed}`;
}

export interface MarkFilter {
  family?: string | null;
  dia?: string | null;
}

export function marksFor(marks: SteelMarkRow[], filter: MarkFilter): SteelMarkRow[] {
  return marks.filter((m) => (!filter.family || m.family === filter.family) && (!filter.dia || Object.keys(m.dia).some((d) => Number(d) === Number(filter.dia))));
}

export function filterWords(filter: MarkFilter, labelOf: (family: string) => string): string {
  const bits: string[] = [];
  if (filter.family) bits.push(labelOf(filter.family));
  if (filter.dia) bits.push(diaText(filter.dia));
  return bits.join(", ");
}

export function diaKgOf(m: SteelMarkRow, dia: string | null | undefined): number | null {
  if (!dia) return null;
  const key = Object.keys(m.dia).find((d) => Number(d) === Number(dia));
  return key === undefined ? null : m.dia[key];
}

export function rangeText(low: number, high: number, kg: number): string {
  if (Math.abs(high - low) < 0.5 || (low === kg && high === kg)) return "";
  return `${kgText(low)} to ${kgText(high)} kg`;
}

export function estimateWarning(summary: Pick<SteelSummary, "totals">): string {
  const t = summary.totals;
  if (t.estimated_kg <= 0) return "";
  return `${t.estimated_share_pct.toFixed(1)} % of this steel (${kgText(t.estimated_kg)} kg) is estimated from the size of the members, not read from bars. The total is between ${kgText(t.kg_low)} and ${kgText(t.kg_high)} kg.`;
}

export function apiErrorText(error: unknown, fallback: string): string {
  const e = error as { response?: { data?: { message?: string; detail?: { message?: string } | string; error?: { message?: string } } } } | null;
  const d = e?.response?.data;
  const detail = typeof d?.detail === "string" ? d.detail : d?.detail?.message;
  return d?.error?.message || detail || d?.message || fallback;
}

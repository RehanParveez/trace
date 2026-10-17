export type EvidenceGrade = "PRINTED" | "MEASURED" | "ASSUMED" | "MISSING";

export interface EvidenceInput { name: string; basis: string; how: string }
export interface EvidenceRange {
  bounded: boolean;
  low_pct: number | null;
  high_pct: number | null;
  leaves_out: boolean;
  drivers: Array<{ name: string; basis: string; low_pct: number | null; high_pct: number | null }>;
}
export interface RowEvidence { grade: EvidenceGrade; inputs: EvidenceInput[]; ask: string[]; range: EvidenceRange | null }

export const EVIDENCE_GRADES: EvidenceGrade[] = ["PRINTED", "MEASURED", "ASSUMED", "MISSING"];

export const EVIDENCE_TONE: Record<EvidenceGrade, "green" | "blue" | "gold" | "red"> = {
  PRINTED: "green",
  MEASURED: "blue",
  ASSUMED: "gold",
  MISSING: "red",
};

export const EVIDENCE_LABEL: Record<EvidenceGrade, string> = {
  PRINTED: "Printed",
  MEASURED: "Measured",
  ASSUMED: "Assumed",
  MISSING: "Missing",
};

function isGrade(value: unknown): value is EvidenceGrade {
  return typeof value === "string" && (EVIDENCE_GRADES as string[]).includes(value);
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function parseRange(raw: unknown): EvidenceRange | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.bounded !== "boolean") return null;
  return {
    bounded: r.bounded,
    low_pct: num(r.low_pct),
    high_pct: num(r.high_pct),
    leaves_out: r.leaves_out === true,
    drivers: Array.isArray(r.drivers) ? (r.drivers as EvidenceRange["drivers"]) : [],
  };
}

function figure(v: number): string {
  const rounded = Math.abs(v) >= 100 ? Math.round(v) : Math.round(v * 100) / 100;
  return rounded.toLocaleString("en-US");
}

export function rangeText(range: EvidenceRange | null | undefined, quantity: number | null | undefined, unit: string | null | undefined): string {
  if (!range) return "";
  if (!range.bounded) return "No range: a value is missing";
  const u = unit ? ` ${unit}` : "";
  const lo = range.low_pct ?? 0;
  const hi = range.high_pct ?? 0;
  const pct = `${Math.round(lo * 10) / 10}% / +${Math.round(hi * 10) / 10}%`;
  if (quantity === null || quantity === undefined || !Number.isFinite(quantity)) return pct;
  if (lo === 0 && hi === 0) return `${figure(quantity)}${u}, no spread`;
  return `${figure(quantity * (1 + lo / 100))} to ${figure(quantity * (1 + hi / 100))}${u} (${pct})`;
}

export function rowEvidence(properties: Record<string, unknown> | null | undefined): RowEvidence | null {
  const pdf = properties?._pdf as Record<string, unknown> | undefined;
  const raw = pdf?.evidence as Partial<RowEvidence> | undefined;
  if (!raw || !isGrade(raw.grade)) return null;
  return {
    grade: raw.grade,
    inputs: Array.isArray(raw.inputs) ? raw.inputs : [],
    ask: Array.isArray(raw.ask) ? raw.ask.filter((a): a is string => typeof a === "string") : [],
    range: parseRange((raw as { range?: unknown }).range),
  };
}

export function evidenceTitle(evidence: RowEvidence, quantity?: number | null, unit?: string | null): string {
  const lines = evidence.ask.length > 0
    ? evidence.ask
    : evidence.inputs.map((i) => `${i.name}: ${i.how}`);
  const range = rangeText(evidence.range, quantity, unit);
  return [EVIDENCE_LABEL[evidence.grade], ...lines, ...(range ? [`Range: ${range}`] : [])].join("\n");
}

export function evidenceCheck(evidence: RowEvidence | null): string {
  return evidence ? evidence.ask.join(" | ") : "";
}

export interface EvidenceCounts { printed: number; measured: number; assumed: number; missing: number }

export function evidenceCounts(counts: Record<string, number> | null | undefined): EvidenceCounts | null {
  if (!counts) return null;
  const n = (k: string) => Number(counts[k] ?? 0) || 0;
  const out = { printed: n("PRINTED"), measured: n("MEASURED"), assumed: n("ASSUMED"), missing: n("MISSING") };
  return out.printed + out.measured + out.assumed + out.missing > 0 ? out : null;
}

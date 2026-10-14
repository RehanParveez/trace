export type EvidenceGrade = "PRINTED" | "MEASURED" | "ASSUMED" | "MISSING";

export interface EvidenceInput { name: string; basis: string; how: string }
export interface RowEvidence { grade: EvidenceGrade; inputs: EvidenceInput[]; ask: string[] }

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

export function rowEvidence(properties: Record<string, unknown> | null | undefined): RowEvidence | null {
  const pdf = properties?._pdf as Record<string, unknown> | undefined;
  const raw = pdf?.evidence as Partial<RowEvidence> | undefined;
  if (!raw || !isGrade(raw.grade)) return null;
  return {
    grade: raw.grade,
    inputs: Array.isArray(raw.inputs) ? raw.inputs : [],
    ask: Array.isArray(raw.ask) ? raw.ask.filter((a): a is string => typeof a === "string") : [],
  };
}

export function evidenceTitle(evidence: RowEvidence): string {
  const lines = evidence.ask.length > 0
    ? evidence.ask
    : evidence.inputs.map((i) => `${i.name}: ${i.how}`);
  return [EVIDENCE_LABEL[evidence.grade], ...lines].join("\n");
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

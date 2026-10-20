export type ProposalBasis = "WORKBOOK" | "PRINTED" | "PRACTICE" | "SOFTWARE";
export type ProposalEffect = "VALUE" | "SUGGESTION" | "KEPT" | "HOLD";

export interface QsProposal {
  id: string;
  section: string;
  topic: string;
  question: string;
  proposed: string;
  basis: ProposalBasis;
  effect: ProposalEffect;
  evidence: string;
  params: string[];
  confirm: string | null;
}

export interface QsProposedSet {
  note: string;
  bases: Record<string, string>;
  effects: Record<string, string>;
  params: Record<string, number>;
  evidence: Record<string, string>;
  items: QsProposal[];
  counts: Record<string, number>;
  sizes?: Record<string, QsProposedSize>;
}

export interface QsProposedSize {
  mm: number;
  text: string;
  evidence: string;
}

export function proposedSize(key: string, set: QsProposedSet | null | undefined): QsProposedSize | null {
  const size = set?.sizes?.[key];
  return size && Number.isFinite(size.mm) && size.mm > 0 ? size : null;
}

export const SECTION_TITLES: Record<string, string> = {
  A: "Walls, finishes and openings",
  B: "Columns, footings, beams, slabs, lintels and stairs",
  C: "Parapet and roof",
  D: "Tanks and site works",
  E: "Earthwork and foundation",
  F: "Formwork and steel",
  G: "Rules and output",
};

const SECTION_ORDER = ["E", "F", "G", "A", "B", "C", "D"];

export const EFFECT_ORDER: ProposalEffect[] = ["VALUE", "SUGGESTION", "KEPT", "HOLD"];

export const EFFECT_LABEL: Record<ProposalEffect, string> = {
  VALUE: "Changes a standard value",
  SUGGESTION: "Suggestion on the measurement",
  KEPT: "No change",
  HOLD: "On hold",
};

export const BASIS_LABEL: Record<ProposalBasis, string> = {
  WORKBOOK: "From his workbook",
  PRINTED: "From the drawing",
  PRACTICE: "Usual practice",
  SOFTWARE: "Software behaviour",
};

export function isProposedParam(key: string, set: QsProposedSet | null | undefined): boolean {
  return Boolean(set && Object.prototype.hasOwnProperty.call(set.params, key));
}

export function proposedValue(key: string, set: QsProposedSet | null | undefined): number | null {
  return set && isProposedParam(key, set) ? set.params[key] : null;
}

export interface ProposedTextOptions {
  flag?: boolean;
  unit?: "dia" | "pct" | "kgm2";
}

export function proposedParamText(key: string, set: QsProposedSet | null | undefined, options: ProposedTextOptions = {}): string | null {
  const value = proposedValue(key, set);
  if (value === null || !set) return null;
  const shown = options.flag
    ? value >= 0.5
      ? "Yes"
      : "No"
    : options.unit === "pct"
    ? `${value} percent`
    : options.unit === "dia"
    ? `${value} bar diameters`
    : options.unit === "kgm2"
    ? `${value} kg per square metre`
    : `${value} mm (about ${(value / 25.4).toFixed(1)} in)`;
  const why = set.evidence[key];
  return `Empty: ${shown}, proposed from the QS workbook and not yet confirmed by the QS${why ? `. ${why}` : ""}`;
}

export interface ProposalGroup {
  section: string;
  title: string;
  items: QsProposal[];
}

export function groupProposals(set: QsProposedSet | null | undefined): ProposalGroup[] {
  if (!set) return [];
  const by = new Map<string, QsProposal[]>();
  for (const item of set.items) {
    const list = by.get(item.section) ?? [];
    list.push(item);
    by.set(item.section, list);
  }
  return [...by.keys()]
    .sort((a, b) => SECTION_ORDER.indexOf(a) - SECTION_ORDER.indexOf(b))
    .map((section) => ({ section, title: SECTION_TITLES[section] ?? section, items: by.get(section) ?? [] }));
}

export function proposalCounts(set: QsProposedSet | null | undefined): Record<ProposalEffect, number> {
  const out: Record<ProposalEffect, number> = { VALUE: 0, SUGGESTION: 0, KEPT: 0, HOLD: 0 };
  for (const item of set?.items ?? []) out[item.effect] += 1;
  return out;
}

import type { ReadingGapsMark, ReadingGapsResponse, ReadingGapsSummary, ReadingGapsTag, SetAsideItem, UnclaimedItem } from "../types/readingGaps.types";

export const READING_GAPS_COLOUR = { NO_MEMBER: "#d98a1f", UNKNOWN_KIND: "#8c806e", REJECTED: "#6b6f76", INVALID: "#c24a3a", UNCLAIMED_GEOMETRY: "#3b7fb8" } as const;

export const TAG_REASON_TEXT: Record<ReadingGapsTag["reason"], string> = {
  NO_MEMBER: "Kind known, no member made",
  UNKNOWN_KIND: "Kind not known",
};
export const ASIDE_REASON_TEXT: Record<SetAsideItem["reason"], string> = {
  REJECTED: "Rejected",
  INVALID: "Has an error",
};

export const UNCLAIMED_TEXT: Record<UnclaimedItem["kind"], string> = {
  FILLED_SHAPE: "Filled shape no item covers",
  LINE_RUN: "Line work no item covers",
};

export const MAX_MARKS = 600;

function finite(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

export function readingGapsMarks(data: ReadingGapsResponse | null | undefined): ReadingGapsMark[] {
  if (!data || !data.read) return [];
  const out: ReadingGapsMark[] = [];
  for (const t of data.tags ?? []) {
    for (const p of t.points ?? []) {
      if (out.length >= MAX_MARKS) return out;
      if (finite(p?.[0]) && finite(p?.[1])) out.push({ x: p[0], y: p[1], text: t.tag, colour: READING_GAPS_COLOUR[t.reason] });
    }
  }
  for (const a of data.set_aside ?? []) {
    if (out.length >= MAX_MARKS) return out;
    if (a.anchor && finite(a.anchor[0]) && finite(a.anchor[1])) out.push({ x: a.anchor[0], y: a.anchor[1], text: a.tag || a.label || "item", colour: READING_GAPS_COLOUR[a.reason] });
  }
  for (const u of data.unclaimed ?? []) {
    if (out.length >= MAX_MARKS) return out;
    if (finite(u.anchor?.[0]) && finite(u.anchor?.[1])) out.push({ x: u.anchor[0], y: u.anchor[1], text: u.kind === "FILLED_SHAPE" ? "shape" : "lines", colour: READING_GAPS_COLOUR.UNCLAIMED_GEOMETRY });
  }
  return out;
}

export interface ReadingGapsCounts {
  read: boolean;
  tags: number;
  marks: number;
  noMember: number;
  unknownKind: number;
  setAside: number;
  rejected: number;
  invalid: number;
  unclaimed: number;
  unclaimedCut: number;
  wholeSheet: boolean;
  cut: number;
  empty: boolean;
}

export function readingGapsCounts(data: ReadingGapsResponse | null | undefined): ReadingGapsCounts {
  const s: Partial<ReadingGapsSummary> = data?.summary ?? {};
  const n = (v: number | undefined) => (typeof v === "number" && Number.isFinite(v) ? v : 0);
  const counts = {
    read: Boolean(data?.read),
    tags: n(s.tags),
    marks: n(s.tag_marks),
    noMember: n(s.no_member),
    unknownKind: n(s.unknown_kind),
    setAside: n(s.set_aside),
    rejected: n(s.rejected),
    invalid: n(s.invalid),
    unclaimed: n(s.unclaimed),
    unclaimedCut: n(s.unclaimed_cut),
    wholeSheet: Boolean(s.unclaimed_whole_sheet),
    cut: n(s.tags_cut) + n(s.set_aside_cut) + n(s.unclaimed_cut),
    empty: false,
  };
  counts.empty = counts.read && counts.tags === 0 && counts.setAside === 0 && counts.unclaimed === 0;
  return counts;
}

export function readingGapsNote(status: { loading: boolean; error: unknown; data: ReadingGapsResponse | undefined }): string | null {
  if (status.loading) return "Looking for what the reader left out…";
  if (status.error) return "Could not look at this sheet. Prepare it first, then try again.";
  if (status.data && !status.data.read) return "This sheet has not been read yet. Read it on the Found tab; until then every mark would look left out.";
  return null;
}

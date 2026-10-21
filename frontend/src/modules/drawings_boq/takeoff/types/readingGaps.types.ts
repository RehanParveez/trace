export type ReadingGapsReason = "NO_MEMBER" | "UNKNOWN_KIND";
export type SetAsideReason = "REJECTED" | "INVALID";

export interface readingGapsTag {
  tag: string;
  category: string | null;
  reason: ReadingGapsReason;
  count: number;
  points: number[][];
}

export interface SetAsideItem {
  id: string;
  label: string | null;
  tag: string | null;
  category: string | null;
  reason: SetAsideReason;
  codes: string[];
  anchor: number[] | null;
}

export interface readingGapsSummary {
  tags: number;
  tag_marks: number;
  no_member: number;
  unknown_kind: number;
  set_aside: number;
  rejected: number;
  invalid: number;
  tags_cut: number;
  set_aside_cut: number;
}

export interface readingGapsResponse {
  sheet_id: string;
  read: boolean;
  tags: readingGapsTag[];
  set_aside: SetAsideItem[];
  summary: Partial<readingGapsSummary>;
}

export interface readingGapsMark {
  x: number;
  y: number;
  text: string;
  colour: string;
}

export type ReadingGapsReason = "NO_MEMBER" | "UNKNOWN_KIND";
export type UnclaimedKind = "FILLED_SHAPE" | "LINE_RUN";
export type SetAsideReason = "REJECTED" | "INVALID";

export interface ReadingGapsTag {
  tag: string;
  category: string | null;
  reason: ReadingGapsReason;
  count: number;
  points: number[][];
}

export interface UnclaimedItem {
  reason: "UNCLAIMED_GEOMETRY";
  kind: UnclaimedKind;
  anchor: number[];
  size_pt: number;
  bbox: number[];
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

export interface ReadingGapsSummary {
  tags: number;
  tag_marks: number;
  no_member: number;
  unknown_kind: number;
  set_aside: number;
  rejected: number;
  invalid: number;
  tags_cut: number;
  set_aside_cut: number;
  unclaimed: number;
  unclaimed_cut: number;
  unclaimed_whole_sheet: boolean;
}

export interface ReadingGapsResponse {
  sheet_id: string;
  read: boolean;
  tags: ReadingGapsTag[];
  set_aside: SetAsideItem[];
  unclaimed?: UnclaimedItem[];
  summary: Partial<ReadingGapsSummary>;
}

export interface ReadingGapsMark {
  x: number;
  y: number;
  text: string;
  colour: string;
}

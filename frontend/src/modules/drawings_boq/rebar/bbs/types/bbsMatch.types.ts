export type MatchKind = "MATCH" | "ASK" | "EXTRA" | "MISSING";
export type MatchMethod = "FAMILY_MARK" | "ROOM_PANEL" | "SHEET_ONLY" | "USER";

export interface MatchStats {
  rows: number;
  matched: number;
  ask: number;
  extra: number;
  matched_without_asking: number;
  share_without_asking: number;
  floor_not_read: number;
  room_check_skipped: number;
  by_method: Record<string, number>;
  by_family: Record<string, { rows: number; matched: number }>;
}

export interface MatchRun {
  id: string;
  document_id: string;
  floor_map: Record<string, string[]>;
  floor_map_proposed: Record<string, string[]>;
  floor_map_confirmed: boolean;
  member_count: number;
  stats: MatchStats;
  created_at: string;
}

export interface BbsDrawingElement {
  pdf_key: string | null;
  sheet: number | null;
  class: string;
  mark: string | null;
  floor: string | null;
}

export interface MatchItem {
  id: string;
  row_id: string | null;
  kind: MatchKind;
  family: string | null;
  sheet_name: string | null;
  member: string | null;
  floors: string[];
  method: MatchMethod | null;
  confidence: number;
  basis: string | null;
  reason: string | null;
  elements: BbsDrawingElement[];
}

export interface AskGroup {
  group: string;
  sheet: string | null;
  member: string | null;
  family: string | null;
  rows: number;
  reason: string | null;
}

export interface MatchItemList {
  run_id: string | null;
  total: number;
  page: number;
  page_size: number;
  items: MatchItem[];
  asks: AskGroup[];
  counts_by_kind: Partial<Record<MatchKind, number>>;
}

export interface MatchFilters {
  kind: MatchKind | "";
  family: string;
  page: number;
}

export interface ConfirmPayload {
  group: string;
  elements: Array<{ class: string; mark: string | null; floor: string | null }>;
  note: string | null;
}

export interface BbsDecisions {
  decisions: { bbs_floor_map?: Record<string, string[]>; bbs_member_map?: Record<string, unknown> } & Record<string, unknown>;
}

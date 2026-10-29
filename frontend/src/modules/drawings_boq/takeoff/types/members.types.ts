export interface MemberSighting {
  drawing_id: string;
  page_no: number;
  sheet_id: string | null;
  candidate_key: string;
  basis: "SCHEDULE" | "DETAIL" | "PLAN";
}

export interface Member {
  id: string;
  kind: "COLUMN" | "FOOTING" | "BEAM";
  mark: string | null;
  floor: string | null;
  size_mm: number[] | null;
  height_mm: number | null;
  positioned: boolean;
  sightings: MemberSighting[];
}

export interface MemberDecision {
  id: string;
  question: string;
  options: Array<{ value: unknown; sources: string[] }>;
  chosen: unknown;
  open: boolean;
}

export interface MembersView {
  drawing_id: string;
  project_wide: boolean;
  members: Member[];
  decisions: MemberDecision[];
  summary: Record<string, unknown>;
}

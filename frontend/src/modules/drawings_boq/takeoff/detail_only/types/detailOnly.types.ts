export type DecisionKind = "COLUMN_MARK" | "BEAM_DEPTH";

export interface ColumnPerPiece {
  section_m2: number;
  perimeter_m: number;
  heights_mm: number[] | null;
  concrete_m3: number[] | null;
  formwork_m2: number[] | null;
}

export interface PlaceProposal {
  candidate_id: string;
  sheet_id: string;
  page_no: number | null;
  ckey: string;
  count: number;
  size_mm: number[];
  level: string | null;
  points: number[][];
  offered: string[];
  other_marks: string[];
}

export interface DetailOnlyColumn {
  mark: string;
  family: "COLUMN";
  kind: "COLUMN";
  reason: "NO_PLAN_INSTANCE";
  detail_pages: number[];
  size_mm: number[] | null;
  sizes_in: number[][];
  detail_disagree: boolean;
  size_read: boolean;
  per_piece: ColumnPerPiece | null;
  proposals: PlaceProposal[];
}

export interface BeamPerMetre {
  concrete_m3: number;
  formwork_m2: number;
}

export interface DetailOnlyBeam {
  mark: string;
  family: "BEAM";
  kind: string;
  reason: "NO_PLAN_INSTANCE";
  detail_pages: number[];
  depth_mm: number | null;
  width_mm: number | null;
  detail_disagree: boolean;
  steel_text: string | null;
  depth_read: boolean;
  per_metre: BeamPerMetre | null;
}

export interface DepthOption {
  depth_mm: number;
  marks: string[];
}

export interface DepthGapRow {
  candidate_id: string;
  sheet_id: string;
  page_no: number | null;
  decision: string;
  length_m: number;
  width_mm: number | null;
  chosen: boolean;
}

export interface DepthGap {
  mark: string;
  kind: string;
  has_section: boolean;
  section_pages: number[];
  options: DepthOption[];
  rows: DepthGapRow[];
  stake: { length_m: number; width_mm: number; concrete_m3: number[] } | null;
}

export interface DetailDecision {
  id: string;
  kind: DecisionKind;
  mark: string;
  sheet_id: string | null;
  page_no: number | null;
  ckey: string | null;
  value_mm: number | null;
  applied: boolean;
  decided_by_user_id: string | null;
}

export interface DetailOnlySummary {
  detail_only: number;
  columns: number;
  beams: number;
  with_place: number;
  depth_gaps: number;
  cut: number;
  column_marks_with_detail: number;
  beam_marks_with_section: number;
}

export interface DetailOnlyReport {
  drawing_id: string;
  columns: DetailOnlyColumn[];
  beams: DetailOnlyBeam[];
  depth_gaps: DepthGap[];
  decisions: DetailDecision[];
  summary: Partial<DetailOnlySummary>;
}

export interface ChooseMarkBody {
  candidate_id: string;
  mark: string;
}

export interface ChooseDepthBody {
  mark: string;
  depth_mm: number;
}

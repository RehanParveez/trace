import type { Finding } from "./bbsAudit.types";

export interface ReportSheet {
  idx: number;
  name: string;
  first_page: number;
  last_page: number;
  row_count: number;
  printed_total_kg: string | null;
  computed_kg: string;
  printed_diff_kg: string | null;
  effect_kg: string;
  expected_kg: string;
  findings: number;
  open_findings: number;
}

export interface ReportSummary {
  document_id: string;
  version: number;
  file_name: string | null;
  has_run: boolean;
  run_id: string | null;
  level: string | null;
  run_created_at: string | null;
  bbs_total_kg: string;
  expected_total_kg: string;
  diff_kg: string;
  diff_pct: string | null;
  printed_total_kg: string;
  effect_by_class: Record<string, string>;
  effect_by_basis: Record<string, string>;
  excluded_kg: Record<string, string>;
  counts_by_class: Record<string, number>;
  counts_by_status: Record<string, number>;
  finding_count: number;
  open_questions: number;
  sheets: ReportSheet[];
  unassigned: { findings: number; effect_kg: string };
  note: string;
}

export interface ReportFinding extends Finding {
  no: number;
}

export interface ReportFindingList {
  run_id: string | null;
  total: number;
  page: number;
  page_size: number;
  items: ReportFinding[];
  counts_by_class: Record<string, number>;
  counts_by_status: Record<string, number>;
}

export interface ReportFilters {
  finding_class?: string;
  status?: string;
  sheet?: number | null;
  page: number;
}

export interface ReportQuestion {
  no: number;
  finding_id: string;
  finding_no: number;
  code: string;
  finding_class: string;
  where: string;
  member: string | null;
  question: string;
  text: string;
}

export interface QuestionList {
  items: ReportQuestion[];
  text: string;
}

export interface CropSide {
  png_base64: string | null;
  reason: string | null;
  message: string | null;
  text: string;
}

export interface FindingCrops {
  finding_id: string;
  bbs: CropSide;
  drawing: CropSide;
}

export type FindingAction = "ACCEPTED" | "REJECTED" | "OPEN" | "SIGN";

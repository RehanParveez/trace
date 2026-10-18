export type BillStatus = "MATCH" | "DIFF" | "MISSING" | "EXTRA" | "OUT_OF_SCOPE";
export type BillClass = "READING" | "CONVENTION" | "QS_ERROR" | "MISSING_FEATURE" | "NEEDS_DECISION";
export type BillFilter = "OPEN" | "ALL" | "MATCH";

export interface BillRowRef {
  row: number;
  section: string;
  item: string;
  unit: string;
  quantity: number;
}

export interface BillFloorFigure {
  floor: string;
  label: string;
  qs: number | null;
  software: number | null;
}

export interface BillCompareLine {
  key: string;
  label: string;
  status: BillStatus;
  unit: string;
  qs: number | null;
  software: number | null;
  difference: number | null;
  error_pct: number | null;
  closeness?: number | null;
  suggested_class: BillClass | null;
  class: BillClass | null;
  note: string;
  bill_rows: BillRowRef[];
  software_rows: number;
  software_tags: { tag: string; quantity: number }[];
  floors?: BillFloorFigure[];
  assumed_rows?: number;
}

export interface BillMeasures {
  bill_lines: number;
  compared: number;
  within_tolerance: number;
  line_error_median_pct: number | null;
  coverage_pct: number | null;
  closeness_pct?: number | null;
  closeness_measured_pct?: number | null;
  extra_lines: number;
  unclassified_differences: number;
}

export interface BillCompareResult {
  tolerance_pct: number;
  lines: BillCompareLine[];
  unmapped: BillRowRef[];
  unclassified_software: { name: string; rows: number; quantity: number; unit: string }[];
  measures: BillMeasures;
  bill_sheet: string;
  bill_sheets: string[];
  software_rows: number;
}

export type BillClasses = Record<string, { class: BillClass; note: string }>;

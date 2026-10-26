export type SteelBasis = "PRINTED" | "SCHEDULE" | "MODEL_BARS" | "ESTIMATE_PDF" | "ESTIMATE_MODEL";
export type IntensityStatus = "IN_RANGE" | "BELOW_RANGE" | "ABOVE_RANGE";

export interface SteelDiameterRow {
  dia_mm: number;
  kg: number;
  length_m: number;
  members: number;
  share_pct: number;
  by_family: Record<string, number>;
}

export interface SteelGradeRow {
  grade: string;
  label: string;
  members: number;
  kg: number;
  kg_low: number;
  kg_high: number;
  share_pct: number;
  by_family: Record<string, number>;
}

export interface SteelFamilyRow {
  family: string;
  label: string;
  members: number;
  kg: number;
  kg_low: number;
  kg_high: number;
  bare_kg: number | null;
  concrete_m3: number | null;
  kg_per_m3: number | null;
  intensity_from: number;
  range: number[] | null;
  status: IntensityStatus | null;
  by_basis: Partial<Record<SteelBasis, number>>;
}

export interface SteelMarkRow {
  family: string;
  tag: string;
  level: string;
  basis: SteelBasis;
  count: number;
  kg: number;
  kg_each: number;
  kg_low: number;
  kg_high: number;
  bare_kg: number | null;
  concrete_m3: number | null;
  kg_per_m3: number | null;
  page: number | null;
  dia: Record<string, number>;
  warnings: string[];
}

export interface SteelSummary {
  run_id?: string;
  wastage: { as_run_pct: number[]; applied_pct: number | null; rows_with_bare_weight: number; rows_fixed: number };
  totals: {
    members: number;
    kg: number;
    kg_low: number;
    kg_high: number;
    estimated_kg: number;
    estimated_share_pct: number;
    by_basis: Partial<Record<SteelBasis, { members: number; kg: number }>>;
  };
  by_grade?: SteelGradeRow[];
  by_diameter: SteelDiameterRow[];
  without_diameter: { kg: number; members: number };
  by_family: SteelFamilyRow[];
  marks: SteelMarkRow[];
  marks_truncated: boolean;
   marks_total: number;
  allowances?: SteelAllowances | null;
}

export interface SteelAllowances {
  binding_wire_kg: number;
  chairs_kg: number;
  kg: number;
  bars_kg: number;
  with_bars_kg: number;
  share_pct: number;
}

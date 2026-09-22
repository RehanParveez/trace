export type WHTCategory = "GOODS_SUPPLY" | "SERVICES" | "CONTRACTS_EXECUTION";

export interface WHTRate {
  id: string; category: WHTCategory; filer_rate_percentage: number | string;
  non_filer_rate_percentage: number | string; effective_from: string; is_active: boolean; notes: string | null;
}

export interface WHTPreview {
  category: WHTCategory; rate_percentage: number | string; gross_amount: number | string;
  deducted_amount: number | string; net_after_wht: number | string;
}

export interface WHTDeduction {
  id: string; project_id: string; source_type: string; source_id: string;
  payee_name: string; payee_ntn_or_cnic: string | null; category: WHTCategory;
  gross_amount: number | string; rate_percentage: number | string; is_filer: boolean;
  deducted_amount: number | string; deduction_date: string; currency: string; created_at: string;
}

export interface WHTCategorySummary {
  category: WHTCategory; total_gross_amount: number | string; total_deducted_amount: number | string; deduction_count: number;
}

export interface WHTRegisterSummary {
  period_start: string; period_end: string; by_category: WHTCategorySummary[];
  total_deducted_amount: number | string; currency: string;
}
export type SalesTaxAuthority = "PRA" | "SRB" | "KPRA" | "BRA" | "ICT";

export interface SalesTaxRate {
  id: string; authority: SalesTaxAuthority; rate_percentage: number | string;
  effective_from: string; is_active: boolean; notes: string | null;
}

export interface SalesTaxPreview {
  authority: SalesTaxAuthority; rate_percentage: number | string;
  taxable_amount: number | string; tax_amount: number | string; total_including_tax: number | string;
}

export interface SalesTaxCharge {
  id: string; project_id: string; source_type: string; source_id: string;
  authority: SalesTaxAuthority; rate_percentage: number | string; taxable_amount: number | string;
  tax_amount: number | string; charge_date: string; currency: string; created_at: string;
}

export interface SalesTaxAuthoritySummary {
  authority: SalesTaxAuthority; total_taxable_amount: number | string; total_tax_amount: number | string; charge_count: number;
}

export interface SalesTaxRegisterSummary {
  period_start: string; period_end: string; by_authority: SalesTaxAuthoritySummary[];
  total_tax_amount: number | string; currency: string;
}
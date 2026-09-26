import { apiClient } from "../../../shared/api/client";
import type { SalesTaxAuthority, SalesTaxCharge, SalesTaxPreview, SalesTaxRate, SalesTaxRegisterSummary } from "../types/sales-tax.types";

export const salesTaxApi = {
  async listRates(): Promise<SalesTaxRate[]> { return (await apiClient.get<SalesTaxRate[]>("/sales-tax/rates")).data; },
  async createRate(payload: { authority: SalesTaxAuthority; rate_percentage: number; effective_from: string; notes?: string | null }): Promise<SalesTaxRate> {
    return (await apiClient.post<SalesTaxRate>("/sales-tax/rates", payload)).data;
  },
  async updateRate(rateId: string, payload: { rate_percentage?: number; is_active?: boolean; notes?: string | null }): Promise<SalesTaxRate> {
    return (await apiClient.patch<SalesTaxRate>(`/sales-tax/rates/${rateId}`, payload)).data;
  },
  async preview(authority: SalesTaxAuthority, taxableAmount: number): Promise<SalesTaxPreview> {
    return (await apiClient.get<SalesTaxPreview>("/sales-tax/preview", { params: { authority, taxable_amount: taxableAmount } })).data;
  },
  async listCharges(periodStart?: string, periodEnd?: string, projectId?: string): Promise<SalesTaxCharge[]> {
    return (await apiClient.get<SalesTaxCharge[]>("/sales-tax/charges", { params: { period_start: periodStart, period_end: periodEnd, project_id: projectId } })).data;
  },
  async getRegisterSummary(periodStart: string, periodEnd: string): Promise<SalesTaxRegisterSummary> {
    return (await apiClient.get<SalesTaxRegisterSummary>("/sales-tax/charges/summary", { params: { period_start: periodStart, period_end: periodEnd } })).data;
  },
};
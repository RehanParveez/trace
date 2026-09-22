import { apiClient } from "../../../shared/api/client";
import type { WHTDeduction, WHTPreview, WHTRate, WHTRegisterSummary, WHTCategory } from "../types/withholding-tax.types";

export const withholdingTaxApi = {
  async listRates(): Promise<WHTRate[]> { return (await apiClient.get<WHTRate[]>("/withholding-tax/rates")).data; },
  async createRate(payload: { category: WHTCategory; filer_rate_percentage: number; non_filer_rate_percentage: number; effective_from: string; notes?: string | null }): Promise<WHTRate> {
    return (await apiClient.post<WHTRate>("/withholding-tax/rates", payload)).data;
  },
  async updateRate(rateId: string, payload: { filer_rate_percentage?: number; non_filer_rate_percentage?: number; is_active?: boolean; notes?: string | null }): Promise<WHTRate> {
    return (await apiClient.patch<WHTRate>(`/withholding-tax/rates/${rateId}`, payload)).data;
  },
  async preview(category: WHTCategory, grossAmount: number, isFiler: boolean): Promise<WHTPreview> {
    return (await apiClient.get<WHTPreview>("/withholding-tax/preview", { params: { category, gross_amount: grossAmount, is_filer: isFiler } })).data;
  },
  async listDeductions(periodStart?: string, periodEnd?: string, projectId?: string): Promise<WHTDeduction[]> {
    return (await apiClient.get<WHTDeduction[]>("/withholding-tax/deductions", { params: { period_start: periodStart, period_end: periodEnd, project_id: projectId } })).data;
  },
  async getRegisterSummary(periodStart: string, periodEnd: string): Promise<WHTRegisterSummary> {
    return (await apiClient.get<WHTRegisterSummary>("/withholding-tax/deductions/summary", { params: { period_start: periodStart, period_end: periodEnd } })).data;
  },
};
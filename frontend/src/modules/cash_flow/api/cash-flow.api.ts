import { apiClient } from "../../../shared/api/client";
import type { CashFlowForecast, CashFlowSettings } from "../types/cash-flow.types";

export const cashFlowApi = {
  async getForecast(projectId: string | undefined, horizonDays: number, startingCashBalance: number | null): Promise<CashFlowForecast> {
    return (await apiClient.get<CashFlowForecast>("/cash-flow/forecast", {
      params: { project_id: projectId, horizon_days: horizonDays, starting_cash_balance: startingCashBalance ?? undefined },
    })).data;
  },
  async getSettings(): Promise<CashFlowSettings> { return (await apiClient.get<CashFlowSettings>("/cash-flow/settings")).data; },
  async updateSettings(payload: Partial<CashFlowSettings>): Promise<CashFlowSettings> {
    return (await apiClient.patch<CashFlowSettings>("/cash-flow/settings", payload)).data;
  },
};
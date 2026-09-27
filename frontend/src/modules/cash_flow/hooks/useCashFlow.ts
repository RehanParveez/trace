import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cashFlowApi } from "../api/cash-flow.api";

export const cashFlowKeys = {
  all: ["cash-flow"] as const,
  forecast: (projectId: string | undefined, horizon: number, startingBalance: number | null) =>
    [...cashFlowKeys.all, "forecast", projectId, horizon, startingBalance] as const,
  settings: () => [...cashFlowKeys.all, "settings"] as const,
};

export function useCashFlowForecast(projectId: string | undefined, horizonDays: number, startingCashBalance: number | null) {
  return useQuery({
    queryKey: cashFlowKeys.forecast(projectId, horizonDays, startingCashBalance),
    queryFn: () => cashFlowApi.getForecast(projectId, horizonDays, startingCashBalance),
  });
}

export function useCashFlowSettings() {
  return useQuery({ queryKey: cashFlowKeys.settings(), queryFn: cashFlowApi.getSettings });
}

export function useUpdateCashFlowSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof cashFlowApi.updateSettings>[0]) => cashFlowApi.updateSettings(payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: cashFlowKeys.settings() }); void qc.invalidateQueries({ queryKey: cashFlowKeys.all }); },
  });
}
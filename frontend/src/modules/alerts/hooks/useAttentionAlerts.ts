import { useQuery } from "@tanstack/react-query";
import { alertsApi } from "../api/alerts.api";

export const alertKeys = { all: ["alerts"] as const, attention: () => [...alertKeys.all, "attention"] as const };

export function useAttentionAlerts() {
  return useQuery({
    queryKey: alertKeys.attention(),
    queryFn: alertsApi.getAttention,
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}
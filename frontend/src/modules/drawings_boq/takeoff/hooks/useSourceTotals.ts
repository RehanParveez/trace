import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../../../shared/api/client";
import type { SourceTotals } from "../utils/sourceTotals";

export const sourceTotalsKey = (projectId: string) => ["takeoff", "source-totals", projectId] as const;

export function useSourceTotals(projectId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: sourceTotalsKey(projectId ?? ""),
    queryFn: async () => (await apiClient.get<SourceTotals>(`/drawings-boq/projects/${projectId}/takeoff/source-totals`)).data,
    enabled: Boolean(projectId) && enabled,
  });
}

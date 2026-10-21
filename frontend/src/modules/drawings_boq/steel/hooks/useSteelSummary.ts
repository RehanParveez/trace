import { useMutation, useQuery } from "@tanstack/react-query";
import { steelSummaryApi } from "../api/steelSummary.api";
import type { SteelSummary } from "../types/steelSummary.types";

export function useSteelSummary(runId: string | undefined, wastagePct: number | null) {
  return useQuery({
    queryKey: ["steel-summary", runId ?? "", wastagePct],
    queryFn: () => steelSummaryApi.get(runId as string, wastagePct),
    enabled: Boolean(runId),
    staleTime: 60 * 1000,
  });
}

export function useDownloadSteelSummary() {
  return useMutation({ mutationFn: (summary: SteelSummary) => steelSummaryApi.download(summary) });
}

import { useQuery } from "@tanstack/react-query";
import { runHistoryApi } from "../api/runHistory.api";

export function useRunHistory(runId: string | undefined) {
  return useQuery({
    queryKey: ["drawings-boq", "run-history", runId ?? ""] as const,
    queryFn: () => runHistoryApi.get(runId as string),
    enabled: Boolean(runId),
  });
}

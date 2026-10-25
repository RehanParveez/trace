import { useQuery } from "@tanstack/react-query";
import { billCompletenessApi } from "../api/billCompleteness.api";

export const billCompletenessKeys = {
  run: (runId: string) => ["drawings-boq", "bill-completeness", runId] as const,
};

export function useBillCompleteness(runId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: billCompletenessKeys.run(runId ?? ""),
    queryFn: () => billCompletenessApi.forRun(runId as string),
    enabled: Boolean(runId) && enabled,
    staleTime: 15_000,
  });
}

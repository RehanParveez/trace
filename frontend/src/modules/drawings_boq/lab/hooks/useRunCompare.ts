import { useMutation, useQuery } from "@tanstack/react-query";
import { runCompareApi } from "../api/runCompare.api";
import type { BillClasses } from "../types/billCompare.types";

export function useCompareBill(runId: string) {
  return useMutation({
    mutationFn: (v: { file: File; tolerancePct: number; classes: BillClasses }) => runCompareApi.compareBill(runId, v.file, v.tolerancePct, v.classes),
  });
}

export function useReasonableness(runId: string | undefined) {
  return useQuery({
    queryKey: ["drawings-boq", "reasonableness", runId ?? ""] as const,
    queryFn: () => runCompareApi.reasonableness(runId as string),
    enabled: Boolean(runId),
  });
}

import { useMutation } from "@tanstack/react-query";
import { steelCompareApi } from "../api/steelCompare.api";
import type { BillClasses } from "../types/billCompare.types";

export function useCompareSteel(runId: string) {
  return useMutation({
    mutationFn: (v: { file: File; tolerancePct: number; classes: BillClasses }) => steelCompareApi.compare(runId, v.file, v.tolerancePct, v.classes),
  });
}

export function useExportComparison() {
  return useMutation({ mutationFn: steelCompareApi.exportXlsx });
}

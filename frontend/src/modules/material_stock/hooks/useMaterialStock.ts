import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { materialStockApi } from "../api/material_stock.api";

export const materialStockKeys = {
  all: ["material-stock"] as const,
  issues: (projectId: string) => [...materialStockKeys.all, "issues", projectId] as const,
  reconciliation: (projectId: string) => [...materialStockKeys.all, "reconciliation", projectId] as const,
};

export function useMaterialIssues(projectId: string) {
  return useQuery({ queryKey: materialStockKeys.issues(projectId), queryFn: () => materialStockApi.listIssues(projectId), enabled: Boolean(projectId) });
}
export function useRecordMaterialIssue(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof materialStockApi.recordIssue>[1]) => materialStockApi.recordIssue(projectId, payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: materialStockKeys.issues(projectId) }); void qc.invalidateQueries({ queryKey: materialStockKeys.reconciliation(projectId) }); },
  });
}
export function useMaterialReconciliation(projectId: string) {
  return useQuery({ queryKey: materialStockKeys.reconciliation(projectId), queryFn: () => materialStockApi.getReconciliation(projectId), enabled: Boolean(projectId) });
}
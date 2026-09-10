import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { budgetsApi } from "../api/budgets.api";
import type { BudgetSaveRequest } from "../types/budget.types";

export const budgetKeys = {
  all: ["budgets"] as const,
  forProject: (projectId: string) => [...budgetKeys.all, "project", projectId] as const,
};

export function useProjectBudget(projectId: string | undefined) {
  return useQuery({
    queryKey: budgetKeys.forProject(projectId ?? ""),
    queryFn: async () => {
      const budgets = await budgetsApi.listBudgets(projectId);
      return budgets[0] ?? null;
    },
    enabled: Boolean(projectId),
  });
}

export function useSaveBudget() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: BudgetSaveRequest) => budgetsApi.saveBudget(payload),
    onSuccess: (budget) => {
      queryClient.setQueryData(budgetKeys.forProject(budget.project_id), budget);
    },
  });
}
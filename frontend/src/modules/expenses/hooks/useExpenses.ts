import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { expensesApi } from "../api/expenses.api";
import type { ExpenseCreateRequest, ExpenseListParams, ExpenseReviewRequest } from "../types/expense.types";

export const expenseKeys = {
  all: ["expenses"] as const,
  list: (params: ExpenseListParams) => [...expenseKeys.all, "list", params] as const,
};

export function useExpenses(params: ExpenseListParams = {}) {
  return useQuery({
    queryKey: expenseKeys.list(params),
    queryFn: () => expensesApi.listExpenses(params),
  });
}

function invalidateExpenseLists(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({
    queryKey: expenseKeys.all,
    predicate: (query) => query.queryKey[1] === "list",
  });
}

export function useCreateExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ExpenseCreateRequest) => expensesApi.createExpense(payload),
    onSuccess: () => invalidateExpenseLists(queryClient),
  });
}

export function useApproveExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ expenseId, payload }: { expenseId: string; payload: ExpenseReviewRequest }) =>
      expensesApi.approveExpense(expenseId, payload),
    onSuccess: () => invalidateExpenseLists(queryClient),
  });
}

export function useRejectExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ expenseId, payload }: { expenseId: string; payload: ExpenseReviewRequest }) =>
      expensesApi.rejectExpense(expenseId, payload),
    onSuccess: () => invalidateExpenseLists(queryClient),
  });
}
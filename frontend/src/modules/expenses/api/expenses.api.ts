import { apiClient } from "../../../shared/api/client";
import type {Expense, ExpenseCreateRequest, ExpenseListParams, ExpenseOrganizationSummary, ExpenseReviewRequest,
} from "../types/expense.types";

export const expensesApi = {
  async listExpenses(params: ExpenseListParams = {}): Promise<Expense[]> {
    const response = await apiClient.get<Expense[]>("/expenses", {
      params: {
        project_id: params.projectId,
        status: params.status,
        skip: params.skip ?? 0,
        limit: params.limit ?? 100,
      },
    });

    return response.data;
  },

  async createExpense(payload: ExpenseCreateRequest): Promise<Expense> {
    const response = await apiClient.post<Expense>("/expenses", payload);
    return response.data;
  },

  async approveExpense(expenseId: string, payload: ExpenseReviewRequest): Promise<Expense> {
    const response = await apiClient.post<Expense>(`/expenses/${expenseId}/approve`, payload);
    return response.data;
  },

  async rejectExpense(expenseId: string, payload: ExpenseReviewRequest): Promise<Expense> {
    const response = await apiClient.post<Expense>(`/expenses/${expenseId}/reject`, payload);
    return response.data;
  },

  async getOrganizationSummary(): Promise<ExpenseOrganizationSummary> {
    const response = await apiClient.get<ExpenseOrganizationSummary>(
      "/expenses/organization-summary",
    );

    return response.data;
  },
};
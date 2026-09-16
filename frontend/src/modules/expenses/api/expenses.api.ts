import { apiClient } from "../../../shared/api/client";
import type {Expense, ExpenseCreateRequest, ExpenseListParams, ExpenseOrganizationSummary, ExpenseReviewRequest, ExpenseStatusSummary, ExpenseListResponse,
} from "../types/expense.types";

export const expensesApi = {
  async listExpenses(params: ExpenseListParams = {}): Promise<ExpenseListResponse> {
    const response = await apiClient.get<ExpenseListResponse>("/expenses", {
      params: {
        project_id: params.projectId,
        status: params.status,
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
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

  async getStatusSummary(params: { projectId?: string } = {}): Promise<ExpenseStatusSummary> {
    const response = await apiClient.get<ExpenseStatusSummary>("/expenses/status-summary", {
      params: { project_id: params.projectId },
    });

    return response.data;
  },
};
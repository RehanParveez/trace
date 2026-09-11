import { apiClient } from "../../../shared/api/client";
import type { Budget, BudgetOrganizationSummary, BudgetSaveRequest } from "../types/budget.types";

export const budgetsApi = {
  async listBudgets(projectId?: string): Promise<Budget[]> {
    const response = await apiClient.get<Budget[]>("/budgets", {
      params: { project_id: projectId },
    });

    return response.data;
  },

  async saveBudget(payload: BudgetSaveRequest): Promise<Budget> {
    const response = await apiClient.put<Budget>(
      `/budgets/project/${payload.project_id}`,
      payload,
    );

    return response.data;
  },

  async getOrganizationSummary(): Promise<BudgetOrganizationSummary> {
    const response = await apiClient.get<BudgetOrganizationSummary>(
      "/budgets/organization-summary",
    );

    return response.data;
  },
};
import { authenticatedRequest } from "./client";
import type {Budget, BudgetOrganizationSummary, BudgetProjectSummary, BudgetSavePayload,
} from "./types";

export function listProjectBudgets(projectId: string): Promise<Budget[]> {
  return authenticatedRequest<Budget[]>(
    `/budgets?project_id=${encodeURIComponent(projectId)}`,
  );
}

export function listBudgetsByProject(): Promise<BudgetProjectSummary[]> {
  return authenticatedRequest<BudgetProjectSummary[]>(
    "/budgets/list-by-project",
  );
}

export function getBudgetOrganizationSummary():
  Promise<BudgetOrganizationSummary> {
  return authenticatedRequest<BudgetOrganizationSummary>(
    "/budgets/organization-summary",
  );
}

export function saveProjectBudget(
  projectId: string,
  payload: BudgetSavePayload,
): Promise<Budget> {
  return authenticatedRequest<Budget>(
    `/budgets/project/${encodeURIComponent(projectId)}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}
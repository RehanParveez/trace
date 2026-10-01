import { authenticatedRequest } from "./client";
import type {Expense, ExpenseCreatePayload, ExpenseListParams, ExpenseOrganizationSummary, ExpenseReviewPayload, ExpenseStatusSummary,
} from "./types";

function queryString(params: ExpenseListParams = {}): string {
  const query = new URLSearchParams();

  if (params.project_id) query.set("project_id", params.project_id);
  if (params.status) query.set("status", params.status);
  if (params.skip !== undefined) query.set("skip", String(params.skip));
  if (params.limit !== undefined) query.set("limit", String(params.limit));

  const value = query.toString();
  return value ? `?${value}` : "";
}

const jsonBody = (value: unknown) => JSON.stringify(value);

export function listExpenses(
  params: ExpenseListParams = {},
): Promise<Expense[]> {
  return authenticatedRequest<Expense[]>(`/expenses${queryString(params)}`);
}

export function getExpenseOrganizationSummary():
  Promise<ExpenseOrganizationSummary> {
  return authenticatedRequest<ExpenseOrganizationSummary>(
    "/expenses/organization-summary",
  );
}

export function getExpenseStatusSummary(
  projectId?: string,
): Promise<ExpenseStatusSummary> {
  const query = projectId
    ? `?project_id=${encodeURIComponent(projectId)}`
    : "";

  return authenticatedRequest<ExpenseStatusSummary>(
    `/expenses/status-summary${query}`,
  );
}

export function createExpense(
  payload: ExpenseCreatePayload,
): Promise<Expense> {
  return authenticatedRequest<Expense>("/expenses", {
    method: "POST",
    body: jsonBody(payload),
  });
}

export function approveExpense(
  expenseId: string,
  payload: ExpenseReviewPayload = {},
): Promise<Expense> {
  return authenticatedRequest<Expense>(
    `/expenses/${expenseId}/approve`,
    { method: "POST", body: jsonBody(payload) },
  );
}

export function rejectExpense(
  expenseId: string,
  payload: ExpenseReviewPayload = {},
): Promise<Expense> {
  return authenticatedRequest<Expense>(
    `/expenses/${expenseId}/reject`,
    { method: "POST", body: jsonBody(payload) },
  );
}
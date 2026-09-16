export type ExpenseStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface Expense {
  id: string;
  project_id: string;
  category: string;
  description: string | null;
  amount: number | string;
  expense_date: string;
  status: ExpenseStatus;
  submitted_by: string | null;
  reviewed_by: string | null;
  review_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseCreateRequest {
  project_id: string;
  category: string;
  description?: string | null;
  amount: number;
  expense_date: string;
}

export interface ExpenseReviewRequest {
  note?: string | null;
}

export interface ExpenseListParams {
  projectId?: string;
  status?: ExpenseStatus;
  page?: number;
  pageSize?: number;
}

export interface ExpenseOrganizationSummary {
  total_approved_amount: number | string;
  expense_count: number;
}

export interface ExpenseStatusSummary {
  totals: Partial<Record<ExpenseStatus, number | string>>;
}

export interface ExpenseListResponse {
  items: Expense[];
  total: number;
  page: number;
  page_size: number;
}
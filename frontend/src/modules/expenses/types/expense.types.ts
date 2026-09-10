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
  skip?: number;
  limit?: number;
}
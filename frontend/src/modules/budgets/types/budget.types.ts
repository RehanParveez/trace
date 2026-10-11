export interface BudgetCategory {
  id: string;
  name: string;
  allocated_amount: number | string;
}

export interface Budget {
  id: string;
  project_id: string;
  approved_amount: number | string;
  currency: string;
  notes: string | null;
  version: number;
  categories: BudgetCategory[];
  created_at: string;
  updated_at: string;
}

export interface BudgetCategoryInput {
  id?: string;
  name: string;
  allocated_amount: number;
}

export interface BudgetSaveRequest {
  project_id: string;
  approved_amount: number;
  currency?: string;
  notes?: string | null;
  categories?: BudgetCategoryInput[];
  version?: number | null;
}

export interface BudgetOrganizationSummary {
  total_approved_amount: number | string;
  budget_count: number;
  currency: string;
}

export interface BudgetProjectSummary {
  project_id: string;
  approved_amount: number | string;
  currency: string;
}

export interface BudgetCategoryStatus {
  category_id: string | null;
  name: string;
  allocated_amount: number | string;
  spent_amount: number | string;
  pending_amount: number | string;
  remaining_amount: number | string;
  used_percentage: number | null;
}

export interface BudgetStatus {
  project_id: string;
  has_budget: boolean;
  currency: string;
  approved_amount: number | string;
  allocated_total: number | string;
  expenses_approved: number | string | null;
  expenses_pending: number | string | null;
  labour_accrued: number | string | null;
  subcontracted: number | string | null;
  materials_received: number | string | null;
  materials_committed: number | string | null;
  total_used: number | string;
  forecast_total: number | string;
  remaining: number | string;
  used_percentage: number | null;
  categories: BudgetCategoryStatus[];
}
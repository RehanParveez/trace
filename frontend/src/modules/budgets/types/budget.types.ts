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
  categories: BudgetCategory[];
  created_at: string;
  updated_at: string;
}

export interface BudgetCategoryInput {
  name: string;
  allocated_amount: number;
}

export interface BudgetSaveRequest {
  project_id: string;
  approved_amount: number;
  currency?: string;
  notes?: string | null;
  categories?: BudgetCategoryInput[];
}

export interface BudgetOrganizationSummary {
  total_approved_amount: number | string;
  budget_count: number;
  currency: string;
}
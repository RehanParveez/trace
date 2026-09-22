export type MaterialIssueType = "ISSUED" | "WASTAGE";

export interface MaterialIssue {
  id: string; material_name: string; unit: string; quantity: number | string;
  issue_type: MaterialIssueType; issued_to: string | null; issue_date: string; notes: string | null;
}

export interface MaterialStockLine {
  material_name: string; unit: string; total_received: number | string; total_issued: number | string;
  total_wastage: number | string; balance: number | string; wastage_percentage: number | null;
  estimated_wastage_cost: number | string | null;
}

export interface MaterialStockReconciliation {
  project_id: string; lines: MaterialStockLine[]; currency: string;
}
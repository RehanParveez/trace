import { apiClient } from "../../../shared/api/client";
import type { MaterialIssue, MaterialStockReconciliation } from "../types/material-stock.types";

export const materialStockApi = {
  async listIssues(projectId: string): Promise<MaterialIssue[]> {
    return (await apiClient.get<MaterialIssue[]>(`/material-stock/projects/${projectId}/issues`)).data;
  },
  async recordIssue(projectId: string, payload: { material_name: string; unit: string; quantity: number; issue_type: string; issued_to?: string | null; issue_date: string; notes?: string | null }): Promise<MaterialIssue> {
    return (await apiClient.post<MaterialIssue>(`/material-stock/projects/${projectId}/issues`, payload)).data;
  },
  async getReconciliation(projectId: string): Promise<MaterialStockReconciliation> {
    return (await apiClient.get<MaterialStockReconciliation>(`/material-stock/projects/${projectId}/reconciliation`)).data;
  },
};
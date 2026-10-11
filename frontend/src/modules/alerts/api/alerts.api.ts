import { apiClient } from "../../../shared/api/client";

export type AttentionKind =
  | "CLIENT_BILLS_OVERDUE" | "SUBCONTRACTOR_BILLS_OVERDUE" | "GUARANTEES_EXPIRING"
  | "TAX_DUE" | "PROCUREMENT_OVERDUE" | "BUDGETS_NEAR_LIMIT";

export interface AttentionAlert { kind: AttentionKind; count: number; amount: number | string | null; }
export interface AttentionAlerts { currency: string; items: AttentionAlert[]; }

export const alertsApi = {
  async getAttention(): Promise<AttentionAlerts> {
    return (await apiClient.get<AttentionAlerts>("/alerts/attention")).data;
  },
};
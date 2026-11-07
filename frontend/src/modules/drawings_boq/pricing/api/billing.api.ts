import { apiClient } from "../../../../shared/api/client";
import type { BillingView } from "../types/billing.types";

const BASE = "/drawings-boq";

export const billingApi = {
  async get(projectId: string, profile?: string): Promise<BillingView> {
    return (await apiClient.get<BillingView>(`${BASE}/projects/${projectId}/billing`, { params: { profile: profile || undefined } })).data;
  },
};

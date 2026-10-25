import { apiClient } from "../../../../shared/api/client";
import type { BillCompleteness } from "../types/billCompleteness.types";

const BASE = "/drawings-boq";

export const billCompletenessApi = {
  async forRun(runId: string): Promise<BillCompleteness> {
    return (await apiClient.get<BillCompleteness>(`${BASE}/calculation-runs/${runId}/completeness`)).data;
  },
};

import { apiClient } from "../../../../shared/api/client";
import type { RunHistory } from "../types/history.types";

export const runHistoryApi = {
  async get(runId: string): Promise<RunHistory> {
    return (await apiClient.get<RunHistory>(`/drawings-boq/calculation-runs/${runId}/history`)).data;
  },
};

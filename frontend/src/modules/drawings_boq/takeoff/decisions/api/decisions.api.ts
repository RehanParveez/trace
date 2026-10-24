import { apiClient } from "../../../../../shared/api/client";
import type { ChooseDecisionBody, DecisionsReport } from "../types/decisions.types";

const BASE = "/drawings-boq";

export const decisionsApi = {
  async report(drawingId: string): Promise<DecisionsReport> {
    return (await apiClient.get<DecisionsReport>(`${BASE}/drawings/${drawingId}/takeoff/decisions`)).data;
  },
  async choose(drawingId: string, body: ChooseDecisionBody): Promise<DecisionsReport> {
    return (await apiClient.put<DecisionsReport>(`${BASE}/drawings/${drawingId}/takeoff/decisions`, body)).data;
  },
};

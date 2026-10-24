import { apiClient } from "../../../../../shared/api/client";
import type { IntegrityReport } from "../types/integrity.types";

const BASE = "/drawings-boq";

export const integrityApi = {
  async report(drawingId: string): Promise<IntegrityReport> {
    return (await apiClient.get<IntegrityReport>(`${BASE}/drawings/${drawingId}/takeoff/integrity`)).data;
  },
};

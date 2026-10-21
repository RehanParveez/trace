import { apiClient } from "../../../../shared/api/client";
import type { SteelSummary } from "../types/steelSummary.types";

export const steelSummaryApi = {
  async get(runId: string, wastagePct: number | null): Promise<SteelSummary> {
    if (!runId) throw new Error("Run ID is required");
    const params: Record<string, string> = {};
    if (wastagePct !== null) params.wastage_pct = String(wastagePct);
    return (await apiClient.get<SteelSummary>(`/drawings-boq/calculation-runs/${runId}/steel-summary`, { params })).data;
  },
  async download(summary: SteelSummary): Promise<Blob> {
    return (await apiClient.post<Blob>("/drawings-boq/steel-summary/export", summary, { responseType: "blob" })).data;
  },
};

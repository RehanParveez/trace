import { apiClient } from "../../../../../shared/api/client";
import type { ShadowMode, ShadowRunResult, ShadowSummary } from "../types/aiShadow.types";

const BASE = "/drawings-boq";

export const aiShadowApi = {
  async summary(drawingId: string): Promise<ShadowSummary> {
    return (await apiClient.get<ShadowSummary>(`${BASE}/drawings/${drawingId}/takeoff/ai-shadow`)).data;
  },
  async run(drawingId: string, body: { mode: ShadowMode; limit?: number; force?: boolean }): Promise<ShadowRunResult> {
    return (await apiClient.post<ShadowRunResult>(`${BASE}/drawings/${drawingId}/takeoff/ai-shadow`, body)).data;
  },
  async crop(readId: string): Promise<Blob> {
    return (await apiClient.get<Blob>(`${BASE}/takeoff/ai-shadow/${readId}/crop`, { responseType: "blob" })).data;
  },
};

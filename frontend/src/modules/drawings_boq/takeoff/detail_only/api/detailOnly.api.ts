import { apiClient } from "../../../../../shared/api/client";
import type { ChooseDepthBody, ChooseMarkBody, DetailOnlyReport } from "../types/detailOnly.types";

const BASE = "/drawings-boq";

export const detailOnlyApi = {
  async report(drawingId: string): Promise<DetailOnlyReport> {
    return (await apiClient.get<DetailOnlyReport>(`${BASE}/drawings/${drawingId}/takeoff/detail-only`)).data;
  },
  async chooseMark(drawingId: string, body: ChooseMarkBody): Promise<DetailOnlyReport> {
    return (await apiClient.post<DetailOnlyReport>(`${BASE}/drawings/${drawingId}/takeoff/detail-only/column-mark`, body)).data;
  },
  async chooseDepth(drawingId: string, body: ChooseDepthBody): Promise<DetailOnlyReport> {
    return (await apiClient.post<DetailOnlyReport>(`${BASE}/drawings/${drawingId}/takeoff/detail-only/beam-depth`, body)).data;
  },
  async undo(drawingId: string, decisionId: string): Promise<DetailOnlyReport> {
    return (await apiClient.delete<DetailOnlyReport>(`${BASE}/drawings/${drawingId}/takeoff/detail-only/decisions/${decisionId}`)).data;
  },
};

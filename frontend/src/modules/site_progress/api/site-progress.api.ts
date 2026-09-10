import { apiClient } from "../../../shared/api/client";
import type {SiteLogCreateRequest, SiteLogEntry, SiteLogListParams, SiteLogUpdateRequest,
} from "../types/site-progress.types";

export const siteProgressApi = {
  async listLogs(params: SiteLogListParams = {}): Promise<SiteLogEntry[]> {
    const response = await apiClient.get<SiteLogEntry[]>("/site-logs", {
      params: { project_id: params.projectId, skip: params.skip ?? 0, limit: params.limit ?? 100 },
    });

    return response.data;
  },

  async createLog(payload: SiteLogCreateRequest): Promise<SiteLogEntry> {
    const response = await apiClient.post<SiteLogEntry>("/site-logs", payload);
    return response.data;
  },

  async updateLog(logId: string, payload: SiteLogUpdateRequest): Promise<SiteLogEntry> {
    const response = await apiClient.patch<SiteLogEntry>(`/site-logs/${logId}`, payload);
    return response.data;
  },

  async deleteLog(logId: string): Promise<void> {
    await apiClient.delete(`/site-logs/${logId}`);
  },
};
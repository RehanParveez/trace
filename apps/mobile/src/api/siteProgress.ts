import { authenticatedRequest } from './client'; 
import type {SiteLog, SiteLogCreatePayload, SiteLogUpdatePayload,
} from './types';

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const siteProgressApi = {
  listLogs: (projectId: string, skip = 0, limit = 100) =>
    authenticatedRequest<SiteLog[]>(
      `/site-logs${buildQuery({ project_id: projectId, skip, limit })}`,
      { method: "GET" },
    ),

  createLog: (payload: SiteLogCreatePayload) =>
    authenticatedRequest<SiteLog>("/site-logs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  
  updateLog: (logId: string, payload: SiteLogUpdatePayload) =>
    authenticatedRequest<SiteLog>(`/site-logs/${logId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteLog: (logId: string) =>
    authenticatedRequest<void>(`/site-logs/${logId}`, {
      method: "DELETE",
    }),
};
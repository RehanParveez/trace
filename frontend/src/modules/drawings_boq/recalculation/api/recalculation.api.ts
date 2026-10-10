import { apiClient } from "../../../../shared/api/client";
import type {CalcUsage, ElementImpact, ExportJob, ExportRequest, OrgCalcMetrics, RunMetrics,
} from "../types/recalculation.types";

const BASE = "/drawings-boq";

function filenameFrom(disposition: unknown, fallback: string): string {
  if (typeof disposition !== "string") return fallback;
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  if (!match) return fallback;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}

export type ExportResponse =
  | { kind: "file"; blob: Blob; filename: string }
  | { kind: "job"; job: ExportJob };

export const recalculationApi = {
  async getRunMetrics(runId: string): Promise<RunMetrics> {
    return (await apiClient.get<RunMetrics>(`${BASE}/calculation-runs/${runId}/metrics`)).data;
  },

  async getElementImpact(runId: string, elementId: string): Promise<ElementImpact> {
    return (await apiClient.get<ElementImpact>(`${BASE}/calculation-runs/${runId}/elements/${elementId}/impact`)).data;
  },

  async getOrgMetrics(days: number): Promise<OrgCalcMetrics> {
    return (await apiClient.get<OrgCalcMetrics>(`${BASE}/calculation-metrics`, { params: { days } })).data;
  },

  async getUsage(): Promise<CalcUsage> {
    return (await apiClient.get<CalcUsage>(`${BASE}/calculation-usage`)).data;
  },

  async requestExport(versionId: string, request: ExportRequest, fallbackName: string): Promise<ExportResponse> {
    if (!versionId) throw new Error("Version ID is required");
    const response = await apiClient.get<Blob>(`${BASE}/boq-versions/${versionId}/exports/${request.kind}`, {
      params: {
        fmt: request.format,
        snapshot_id: request.snapshotId ?? undefined,
        compare_snapshot_id: request.compareSnapshotId ?? undefined,
        mode: request.delivery ?? "auto",
      },
      responseType: "blob",
    });
    const contentType = String(response.headers["content-type"] ?? "");
    if (response.status === 202 || contentType.includes("application/json")) {
      const job = JSON.parse(await response.data.text()) as ExportJob;
      return { kind: "job", job };
    }
    return {
      kind: "file",
      blob: response.data,
      filename: filenameFrom(response.headers["content-disposition"], fallbackName),
    };
  },

  async getExportJob(jobId: string): Promise<ExportJob> {
    return (await apiClient.get<ExportJob>(`${BASE}/export-jobs/${jobId}`)).data;
  },

  async downloadExportJob(jobId: string, fallbackName: string): Promise<{ blob: Blob; filename: string }> {
    const response = await apiClient.get<Blob>(`${BASE}/export-jobs/${jobId}/download`, { responseType: "blob" });
    return { blob: response.data, filename: filenameFrom(response.headers["content-disposition"], fallbackName) };
  },
};

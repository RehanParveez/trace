import { apiClient } from "../../../../shared/api/client";
import type { ComparableRun, FixList, RunDifference } from "../types/difference.types";

const need = (id: string, what: string) => {
  if (!id) throw new Error(`${what} is required`);
};

export const differenceApi = {
  async runs(projectId: string): Promise<ComparableRun[]> {
    need(projectId, "Project ID");
    return (await apiClient.get<{ runs: ComparableRun[] }>(`/drawings-boq/projects/${projectId}/difference/runs`)).data.runs;
  },
  async difference(fromRunId: string, toRunId: string, minChangePct?: number): Promise<RunDifference> {
    need(fromRunId, "Earlier run");
    need(toRunId, "Later run");
    const params: Record<string, string> = { from_run_id: fromRunId, to_run_id: toRunId };
    if (minChangePct !== undefined) params.min_change_pct = String(minChangePct);
    return (await apiClient.get<RunDifference>("/drawings-boq/run-difference", { params })).data;
  },
  async exportDifference(result: RunDifference, kind: "difference" | "variation"): Promise<Blob> {
    return (await apiClient.post<Blob>(`/drawings-boq/run-difference/export?kind=${kind}`, result, { responseType: "blob" })).data;
  },
  async fixList(runId: string): Promise<FixList> {
    need(runId, "Run ID");
    return (await apiClient.get<FixList>(`/drawings-boq/calculation-runs/${runId}/fix-list`)).data;
  },
  async exportFixList(fix: FixList): Promise<Blob> {
    return (await apiClient.post<Blob>("/drawings-boq/fix-list/export", fix, { responseType: "blob" })).data;
  },
};

import { apiClient } from "../../../../shared/api/client";
import type { ExpectedBoqDetail, ExpectedBoqSummary, ExpectedCheckResult, ExpectedTolerancesBody } from "../types/expectedBoq.types";

const base = (projectId: string) => `/drawings-boq/projects/${projectId}/expected-boq`;
const need = (id: string, what: string) => {
  if (!id) throw new Error(`${what} is required`);
};

export const expectedBoqApi = {
  async list(projectId: string): Promise<ExpectedBoqSummary[]> {
    need(projectId, "Project ID");
    return (await apiClient.get<{ items: ExpectedBoqSummary[] }>(base(projectId))).data.items;
  },
  async get(projectId: string, expectedId: string): Promise<ExpectedBoqDetail> {
    need(projectId, "Project ID");
    need(expectedId, "Expected BOQ ID");
    return (await apiClient.get<ExpectedBoqDetail>(`${base(projectId)}/${expectedId}`)).data;
  },
  async save(projectId: string, file: File, name: string): Promise<ExpectedBoqDetail> {
    need(projectId, "Project ID");
    const form = new FormData();
    form.append("file", file);
    if (name.trim()) form.append("name", name.trim());
    return (await apiClient.post<ExpectedBoqDetail>(base(projectId), form, { headers: { "Content-Type": "multipart/form-data" } })).data;
  },
  async setTolerances(projectId: string, expectedId: string, body: ExpectedTolerancesBody): Promise<ExpectedBoqDetail> {
    need(projectId, "Project ID");
    need(expectedId, "Expected BOQ ID");
    return (await apiClient.put<ExpectedBoqDetail>(`${base(projectId)}/${expectedId}/tolerances`, body)).data;
  },
  async remove(projectId: string, expectedId: string): Promise<ExpectedBoqSummary[]> {
    need(projectId, "Project ID");
    need(expectedId, "Expected BOQ ID");
    return (await apiClient.delete<{ items: ExpectedBoqSummary[] }>(`${base(projectId)}/${expectedId}`)).data.items;
  },
  async download(projectId: string, expectedId: string): Promise<Blob> {
    need(projectId, "Project ID");
    need(expectedId, "Expected BOQ ID");
    return (await apiClient.get<Blob>(`${base(projectId)}/${expectedId}/export`, { responseType: "blob" })).data;
  },
  async check(runId: string, expectedId: string): Promise<ExpectedCheckResult> {
    need(runId, "Run ID");
    need(expectedId, "Expected BOQ ID");
    return (await apiClient.post<ExpectedCheckResult>(`/drawings-boq/calculation-runs/${runId}/check-expected-boq/${expectedId}`, {})).data;
  },
};

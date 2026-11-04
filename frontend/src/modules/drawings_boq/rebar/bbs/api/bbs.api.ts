import { apiClient } from "../../../../../shared/api/client";
import type { AuditRun, BbsDocumentSummary, BbsUploadResponse, Finding, FindingDecision, FindingFilters, FindingList } from "../types/bbsAudit.types";

const B = "/drawings-boq";
export const FINDINGS_PAGE_SIZE = 100;

export const bbsApi = {
  async list(projectId: string) {
    return (await apiClient.get<BbsDocumentSummary[]>(`${B}/projects/${projectId}/bbs`)).data;
  },

  async upload(projectId: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    return (await apiClient.post<BbsUploadResponse>(`${B}/projects/${projectId}/bbs`, form,
      { headers: { "Content-Type": "multipart/form-data" } })).data;
  },

  async runAudit(documentId: string) {
    return (await apiClient.post<AuditRun>(`${B}/bbs/${documentId}/audit`)).data;
  },

  async runCrossCheck(documentId: string) {
    return (await apiClient.post<AuditRun>(`${B}/bbs/${documentId}/crosscheck`)).data;
  },

  async latestAudit(documentId: string) {
    return (await apiClient.get<AuditRun | null>(`${B}/bbs/${documentId}/audit`)).data;
  },

  async findings(documentId: string, filters: FindingFilters) {
    return (await apiClient.get<FindingList>(`${B}/bbs/${documentId}/findings`, {
      params: {
        finding_class: filters.finding_class || undefined, status: filters.status || undefined, code: filters.code || undefined,
        page: filters.page, page_size: FINDINGS_PAGE_SIZE,
      },
    })).data;
  },

  async decide(findingId: string, status: FindingDecision, reason: string) {
    return (await apiClient.patch<Finding>(`${B}/findings/${findingId}`, { status, reason })).data;
  },
};

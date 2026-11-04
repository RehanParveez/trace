import { apiClient } from "../../../../../shared/api/client";
import type { Finding } from "../types/bbsAudit.types";
import type { FindingCrops, QuestionList, ReportFilters, ReportFindingList, ReportSummary } from "../types/bbsReport.types";

const B = "/drawings-boq";
export const REPORT_PAGE_SIZE = 10;

export const bbsReportApi = {
  async summary(documentId: string) {
    return (await apiClient.get<ReportSummary>(`${B}/bbs/${documentId}/report/summary`)).data;
  },

  async findings(documentId: string, f: ReportFilters) {
    return (await apiClient.get<ReportFindingList>(`${B}/bbs/${documentId}/report/findings`, {
      params: { finding_class: f.finding_class || undefined, status: f.status || undefined, sheet: f.sheet ?? undefined, page: f.page, page_size: REPORT_PAGE_SIZE },
    })).data;
  },

  async questions(documentId: string) {
    return (await apiClient.get<QuestionList>(`${B}/bbs/${documentId}/report/questions`)).data;
  },

  async markdown(documentId: string) {
    return (await apiClient.get<string>(`${B}/bbs/${documentId}/report/summary.md`, { responseType: "text" })).data;
  },

  async xlsx(documentId: string) {
    return (await apiClient.get<Blob>(`${B}/bbs/${documentId}/report/export.xlsx`, { responseType: "blob" })).data;
  },

  async crops(findingId: string) {
    return (await apiClient.get<FindingCrops>(`${B}/findings/${findingId}/crops`)).data;
  },

  async sign(findingId: string, reason: string) {
    return (await apiClient.post<Finding>(`${B}/findings/${findingId}/sign`, { reason })).data;
  },
};

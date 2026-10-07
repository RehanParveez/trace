import { apiClient } from "../../../../shared/api/client";
import type {
  BarSize, BulkReviewResponse, RebarConfirmResponse, RebarImportDetail, RebarRowUpdateRequest, RebarScheduleRow,
  RebarShape, RebarSummary, RowDecision, ScheduleImportResponse,
} from "../../types/drawings-boq.types";

const B = "/drawings-boq";

export const rebarApi = {
  async listImports(projectId: string, status?: string) {
    return (await apiClient.get<ScheduleImportResponse[]>(`${B}/projects/${projectId}/rebar-imports`,
      { params: { status: status || undefined } })).data;
  },

  async importFile(projectId: string, file: File, notes?: string | null) {
    const form = new FormData();
    form.append("file", file);
    if (notes) form.append("notes", notes);
    return (await apiClient.post<RebarImportDetail>(`${B}/projects/${projectId}/rebar-imports/file`, form,
      { headers: { "Content-Type": "multipart/form-data" } })).data;
  },

  async importFromPdf(projectId: string, drawingId: string, notes?: string | null) {
    return (await apiClient.post<RebarImportDetail>(`${B}/projects/${projectId}/rebar-imports/from-pdf`,
      { drawing_id: drawingId, notes: notes ?? null })).data;
  },

  async getImport(importId: string) {
    return (await apiClient.get<RebarImportDetail>(`${B}/rebar-imports/${importId}`)).data;
  },

  async updateRow(rowId: string, body: RebarRowUpdateRequest) {
    return (await apiClient.patch<RebarScheduleRow>(`${B}/rebar-rows/${rowId}`, body)).data;
  },

  async bulkReview(importId: string, rowIds: string[], decision: RowDecision) {
    return (await apiClient.post<BulkReviewResponse>(`${B}/rebar-imports/${importId}/rows/bulk-review`,
      { row_ids: rowIds, review_status: decision })).data;
  },

  async confirmImport(importId: string, rejectPending: boolean) {
    return (await apiClient.post<RebarConfirmResponse>(`${B}/rebar-imports/${importId}/confirm`,
      { reject_pending: rejectPending })).data;
  },

  async rejectImport(importId: string) {
    return (await apiClient.post<RebarConfirmResponse>(`${B}/rebar-imports/${importId}/reject`)).data;
  },

  async archiveImport(importId: string) {
    return (await apiClient.post<RebarConfirmResponse>(`${B}/rebar-imports/${importId}/archive`)).data;
  },

  async listShapes() {
    return (await apiClient.get<RebarShape[]>(`${B}/rebar/shapes`)).data;
  },

  async listSizes() {
    return (await apiClient.get<BarSize[]>(`${B}/rebar/bar-sizes`)).data;
  },

  async summary(versionId: string) {
    return (await apiClient.get<RebarSummary>(`${B}/boq-versions/${versionId}/rebar-summary`)).data;
  },
};

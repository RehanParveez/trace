import { apiClient } from "../../../../../shared/api/client";
import type { Completeness, ManualMark, ManualMarkBody, MisreadBody, MisreadReport, ReadingReport, SheetItems } from "../types/readingReport.types";

const BASE = "/drawings-boq";

export const readingReportApi = {
  async report(drawingId: string, includeItems = false): Promise<ReadingReport> {
    return (await apiClient.get<ReadingReport>(`${BASE}/drawings/${drawingId}/reading-report`, { params: { include_items: includeItems } })).data;
  },
  async items(drawingId: string, sheetId: string): Promise<SheetItems> {
    return (await apiClient.get<SheetItems>(`${BASE}/drawings/${drawingId}/reading-report/sheets/${sheetId}/items`)).data;
  },
  async completeness(projectId: string): Promise<Completeness> {
    return (await apiClient.get<Completeness>(`${BASE}/projects/${projectId}/input-completeness`)).data;
  },
  async marks(drawingId: string, sheetId?: string): Promise<ManualMark[]> {
    return (await apiClient.get<{ overrides: ManualMark[] }>(`${BASE}/drawings/${drawingId}/reading-overrides`, { params: sheetId ? { sheet_id: sheetId } : undefined })).data.overrides;
  },
  async addMark(drawingId: string, body: ManualMarkBody): Promise<ManualMark> {
    return (await apiClient.post<ManualMark>(`${BASE}/drawings/${drawingId}/reading-overrides`, body)).data;
  },
  async withdrawMark(drawingId: string, id: string): Promise<ManualMark> {
    return (await apiClient.delete<ManualMark>(`${BASE}/drawings/${drawingId}/reading-overrides/${id}`)).data;
  },
  async reportMisread(drawingId: string, body: MisreadBody): Promise<MisreadReport> {
    return (await apiClient.post<MisreadReport>(`${BASE}/drawings/${drawingId}/misread-reports`, body)).data;
  },
};

import { apiClient } from "../../../../shared/api/client";
import type {AcceptBody, AcceptResult, CandidateList, DecideResult, DrawingExtractResult, ExtractResult, RegisterSyncResult,
  AutoCalibrateResult, BulkConfirmResult, CalibrationCreate, ModeOption, PickResult, PrepareResult, PreviewRequest, PreviewResult, ProjectTakeoffDrawing,
  DrawingFacts, Reconciliation, ShapeDetail, ShapeList, SheetAnalysis, SnapKind, SnapResult, TagDetail, TagSummary, TakeoffCalibration, TakeoffMeasurement,
  TakeoffOverview, TakeoffSheet, TextResult, VectorResult, MeasurementCreate, MeasurementUpdate, Pt,
} from "../types/takeoff.types";

const BASE = "/drawings-boq";

export const takeoffApi = {
  async modes(): Promise<ModeOption[]> {
    return (await apiClient.get<ModeOption[]>(`${BASE}/takeoff/modes`)).data;
  },
  async overview(drawingId: string): Promise<TakeoffOverview> {
    return (await apiClient.get<TakeoffOverview>(`${BASE}/drawings/${drawingId}/takeoff`)).data;
  },
  async sync(drawingId: string): Promise<TakeoffOverview> {
    return (await apiClient.post<TakeoffOverview>(`${BASE}/drawings/${drawingId}/takeoff/sync`)).data;
  },
  async prepareDrawing(drawingId: string, body: { sheet_ids?: string[]; force?: boolean; budget_seconds?: number }): Promise<PrepareResult> {
    return (await apiClient.post<PrepareResult>(`${BASE}/drawings/${drawingId}/takeoff/prepare`, body)).data;
  },
  async prepareSheet(sheetId: string): Promise<TakeoffSheet> {
    return (await apiClient.post<TakeoffSheet>(`${BASE}/takeoff/sheets/${sheetId}/prepare`)).data;
  },
  async updateSheet(sheetId: string, body: { label?: string | null; scale_text?: string | null; content_kind?: string | null; level_id?: string | null }): Promise<TakeoffSheet> {
    return (await apiClient.patch<TakeoffSheet>(`${BASE}/takeoff/sheets/${sheetId}`, body)).data;
  },
  async analysis(sheetId: string): Promise<SheetAnalysis> {
    return (await apiClient.get<SheetAnalysis>(`${BASE}/takeoff/sheets/${sheetId}/analysis`)).data;
  },
  async autoCalibrate(sheetId: string, body: { use?: "RECOMMENDED" | "DECLARED" | "DIMENSIONS"; make_default?: boolean; include_regions?: boolean }): Promise<AutoCalibrateResult> {
    return (await apiClient.post<AutoCalibrateResult>(`${BASE}/takeoff/sheets/${sheetId}/auto-calibrate`, body)).data;
  },
  async createCalibration(sheetId: string, body: CalibrationCreate): Promise<TakeoffCalibration> {
    return (await apiClient.post<TakeoffCalibration>(`${BASE}/takeoff/sheets/${sheetId}/calibrations`, body)).data;
  },
  async updateCalibration(id: string, body: Record<string, unknown>): Promise<TakeoffCalibration> {
    return (await apiClient.patch<TakeoffCalibration>(`${BASE}/takeoff/calibrations/${id}`, body)).data;
  },
  async makeDefaultCalibration(id: string): Promise<TakeoffCalibration> {
    return (await apiClient.post<TakeoffCalibration>(`${BASE}/takeoff/calibrations/${id}/default`)).data;
  },
  async deleteCalibration(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/takeoff/calibrations/${id}`);
  },
  async vector(sheetId: string, params: { x0?: number; y0?: number; x1?: number; y1?: number; max_segments?: number }): Promise<VectorResult> {
    return (await apiClient.get<VectorResult>(`${BASE}/takeoff/sheets/${sheetId}/vector`, { params })).data;
  },
  async text(sheetId: string, params: { q?: string; mode?: "TAG" | "WORD" | "CONTAINS"; x0?: number; y0?: number; x1?: number; y1?: number }): Promise<TextResult> {
    return (await apiClient.get<TextResult>(`${BASE}/takeoff/sheets/${sheetId}/text`, { params })).data;
  },
  async snap(sheetId: string, body: { points: Pt[]; radius_pt?: number; want?: SnapKind[] }): Promise<{ results: SnapResult[] }> {
    return (await apiClient.post<{ results: SnapResult[] }>(`${BASE}/takeoff/sheets/${sheetId}/snap`, body)).data;
  },
  async pick(sheetId: string, body: { point: Pt; radius_pt?: number; calibration_id?: string | null; wall?: boolean; region?: boolean; label_radius_pt?: number }): Promise<PickResult> {
    return (await apiClient.post<PickResult>(`${BASE}/takeoff/sheets/${sheetId}/pick`, body)).data;
  },
  async tags(sheetId: string): Promise<{ tags: TagSummary[] }> {
    return (await apiClient.get<{ tags: TagSummary[] }>(`${BASE}/takeoff/sheets/${sheetId}/tags`)).data;
  },
  async tag(sheetId: string, tag: string): Promise<TagDetail> {
    return (await apiClient.get<TagDetail>(`${BASE}/takeoff/sheets/${sheetId}/tags/${encodeURIComponent(tag)}`)).data;
  },
  async shapes(sheetId: string): Promise<ShapeList> {
    return (await apiClient.get<ShapeList>(`${BASE}/takeoff/sheets/${sheetId}/shapes`)).data;
  },
  async shape(sheetId: string, groupId: string): Promise<ShapeDetail> {
    return (await apiClient.get<ShapeDetail>(`${BASE}/takeoff/sheets/${sheetId}/shapes/${encodeURIComponent(groupId)}`)).data;
  },
  async preview(body: PreviewRequest, signal?: AbortSignal): Promise<PreviewResult> {
    return (await apiClient.post<PreviewResult>(`${BASE}/takeoff/preview`, body, { signal })).data;
  },
  async createMeasurement(sheetId: string, body: MeasurementCreate): Promise<TakeoffMeasurement> {
    return (await apiClient.post<TakeoffMeasurement>(`${BASE}/takeoff/sheets/${sheetId}/measurements`, body)).data;
  },
  async updateMeasurement(id: string, body: MeasurementUpdate): Promise<TakeoffMeasurement> {
    return (await apiClient.patch<TakeoffMeasurement>(`${BASE}/takeoff/measurements/${id}`, body)).data;
  },
  async deleteMeasurement(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/takeoff/measurements/${id}`);
  },
  async confirm(id: string): Promise<TakeoffMeasurement> {
    return (await apiClient.post<TakeoffMeasurement>(`${BASE}/takeoff/measurements/${id}/confirm`)).data;
  },
  async unconfirm(id: string): Promise<TakeoffMeasurement> {
    return (await apiClient.post<TakeoffMeasurement>(`${BASE}/takeoff/measurements/${id}/unconfirm`)).data;
  },
  async bulkConfirm(ids: string[]): Promise<BulkConfirmResult> {
    return (await apiClient.post<BulkConfirmResult>(`${BASE}/takeoff/measurements/bulk-confirm`, { ids })).data;
  },
  async projectDrawings(projectId: string): Promise<{ drawings: ProjectTakeoffDrawing[] }> {
    return (await apiClient.get<{ drawings: ProjectTakeoffDrawing[] }>(`${BASE}/projects/${projectId}/takeoff/drawings`)).data;
  },
  async reconciliation(projectId: string): Promise<Reconciliation> {
    return (await apiClient.get<Reconciliation>(`${BASE}/projects/${projectId}/takeoff/reconciliation`)).data;
  },
  async candidates(sheetId: string): Promise<CandidateList> {
    return (await apiClient.get<CandidateList>(`${BASE}/takeoff/sheets/${sheetId}/candidates`)).data;
  },
  async extract(sheetId: string, body: { auto_calibrate?: boolean } = {}): Promise<ExtractResult> {
    return (await apiClient.post<ExtractResult>(`${BASE}/takeoff/sheets/${sheetId}/extract`, body)).data;
  },
  async acceptCandidates(body: AcceptBody): Promise<AcceptResult> {
    return (await apiClient.post<AcceptResult>(`${BASE}/takeoff/candidates/accept`, body)).data;
  },
  async rejectCandidates(ids: string[]): Promise<DecideResult> {
    return (await apiClient.post<DecideResult>(`${BASE}/takeoff/candidates/reject`, { ids })).data;
  },
  async restoreCandidates(ids: string[]): Promise<DecideResult> {
    return (await apiClient.post<DecideResult>(`${BASE}/takeoff/candidates/restore`, { ids })).data;
  },

  async extractDrawing(drawingId: string, body: { auto_calibrate?: boolean; budget_seconds?: number; only_unread?: boolean } = {}): Promise<DrawingExtractResult> {
    return (await apiClient.post<DrawingExtractResult>(`${BASE}/drawings/${drawingId}/takeoff/extract`, body)).data;
  },
  
  async facts(drawingId: string): Promise<DrawingFacts> {
    return (await apiClient.get<DrawingFacts>(`${BASE}/drawings/${drawingId}/takeoff/facts`)).data;
  },
  
  async syncRegister(drawingId: string): Promise<RegisterSyncResult> {

    return (await apiClient.post<RegisterSyncResult>(`${BASE}/drawings/${drawingId}/takeoff/register`)).data;
  },
};
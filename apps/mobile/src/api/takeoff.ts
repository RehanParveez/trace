import { authenticatedRequest } from "./client";
import type {CandidateAcceptBody, CandidateAcceptResult, CandidateDecideResult, CandidateExtractResult, CandidateList, DrawingCandidates, DrawingExtractResult, ProjectTakeoffDrawing, TakeoffAutoCalibrate,
  TakeoffBulkConfirm, TakeoffCalibration, TakeoffMeasurement, TakeoffMeasurementCreate, TakeoffMeasurementUpdate, TakeoffMode, TakeoffOverview, TakeoffParams, TakeoffPick, TakeoffPoint,
  TakeoffPrepareResult, TakeoffPreview, TakeoffReconciliation, TakeoffShapeDetail, TakeoffShapeList, TakeoffSheet, TakeoffSheetAnalysis, TakeoffSnapResult, TakeoffTag, TakeoffTagDetail,
  TakeoffText, TakeoffVector, TakeoffKind, TakeoffSource,
} from "./types";

const BASE = "/drawings-boq";

function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  return authenticatedRequest<T>(`${BASE}${path}`, {
    method,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

function query(values: Record<string, string | number | boolean | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== null && value !== "") q.set(key, String(value));
  }
  const text = q.toString();
  return text ? `?${text}` : "";
}

export function listTakeoffModes(): Promise<TakeoffMode[]> {
  return send<TakeoffMode[]>("/takeoff/modes", "GET");
}

export function getTakeoffOverview(drawingId: string): Promise<TakeoffOverview> {
  return send<TakeoffOverview>(`/drawings/${drawingId}/takeoff`, "GET");
}

export function syncTakeoffSheets(drawingId: string): Promise<TakeoffOverview> {
  return send<TakeoffOverview>(`/drawings/${drawingId}/takeoff/sync`, "POST");
}

export function prepareDrawingSheets(
  drawingId: string,
  body: { sheet_ids?: string[]; force?: boolean; budget_seconds?: number } = {},
): Promise<TakeoffPrepareResult> {
  return send<TakeoffPrepareResult>(`/drawings/${drawingId}/takeoff/prepare`, "POST", body);
}

export function prepareSheet(sheetId: string, force = false): Promise<TakeoffSheet> {
  return send<TakeoffSheet>(`/takeoff/sheets/${sheetId}/prepare${query({ force: force ? "true" : undefined })}`, "POST");
}

export function updateSheet(
  sheetId: string,
  body: { label?: string | null; level_id?: string | null; scale_text?: string | null; content_kind?: string },
): Promise<TakeoffSheet> {
  return send<TakeoffSheet>(`/takeoff/sheets/${sheetId}`, "PATCH", body);
}

export function getSheetAnalysis(sheetId: string): Promise<TakeoffSheetAnalysis> {
  return send<TakeoffSheetAnalysis>(`/takeoff/sheets/${sheetId}/analysis`, "GET");
}

export function autoCalibrateSheet(
  sheetId: string,
  body: { use?: "RECOMMENDED" | "DECLARED" | "DIMENSIONS"; make_default?: boolean; include_regions?: boolean } = {},
): Promise<TakeoffAutoCalibrate> {
  return send<TakeoffAutoCalibrate>(`/takeoff/sheets/${sheetId}/auto-calibrate`, "POST", body);
}

export type KnownDistance = { p1: TakeoffPoint; p2: TakeoffPoint; value: number | string; unit: "mm" | "cm" | "m" | "ft" | "in" };

export function createCalibration(
  sheetId: string,
  body: {
    method: "TWO_POINT" | "SCALE_RATIO";
    reference?: KnownDistance | null;
    scale_text?: string | null;
    ratio?: number | string | null;
    check?: KnownDistance | null;
    label?: string | null;
    make_default?: boolean;
  },
): Promise<TakeoffCalibration> {
  return send<TakeoffCalibration>(`/takeoff/sheets/${sheetId}/calibrations`, "POST", body);
}

export function updateCalibration(
  calibrationId: string,
  body: {
    reference?: KnownDistance | null;
    scale_text?: string | null;
    ratio?: number | string | null;
    check?: KnownDistance | null;
    label?: string | null;
  },
): Promise<TakeoffCalibration> {
  return send<TakeoffCalibration>(`/takeoff/calibrations/${calibrationId}`, "PATCH", body);
}

export function makeDefaultCalibration(calibrationId: string): Promise<TakeoffCalibration> {
  return send<TakeoffCalibration>(`/takeoff/calibrations/${calibrationId}/default`, "POST");
}

export function deleteCalibration(calibrationId: string): Promise<void> {
  return send<void>(`/takeoff/calibrations/${calibrationId}`, "DELETE");
}

export function getSheetVector(
  sheetId: string,
  window: { x0?: number; y0?: number; x1?: number; y1?: number; max_segments?: number } = {},
): Promise<TakeoffVector> {
  return send<TakeoffVector>(`/takeoff/sheets/${sheetId}/vector${query(window)}`, "GET");
}

export function getSheetText(
  sheetId: string,
  options: { q?: string; mode?: "TAG" | "WORD" | "CONTAINS"; x0?: number; y0?: number; x1?: number; y1?: number } = {},
): Promise<TakeoffText> {
  return send<TakeoffText>(`/takeoff/sheets/${sheetId}/text${query(options)}`, "GET");
}

export function snapSheetPoints(
  sheetId: string,
  body: { points: TakeoffPoint[]; radius_pt?: number; want?: ("ENDPOINT" | "INTERSECTION" | "MIDPOINT" | "EDGE")[] },
): Promise<{ results: TakeoffSnapResult[] }> {
  return send<{ results: TakeoffSnapResult[] }>(`/takeoff/sheets/${sheetId}/snap`, "POST", body);
}

export function pickSheetPoint(
  sheetId: string,
  body: { point: TakeoffPoint; radius_pt?: number; calibration_id?: string | null; wall?: boolean; region?: boolean; label_radius_pt?: number },
): Promise<TakeoffPick> {
  return send<TakeoffPick>(`/takeoff/sheets/${sheetId}/pick`, "POST", body);
}

export function listSheetTags(sheetId: string): Promise<{ tags: TakeoffTag[] }> {
  return send<{ tags: TakeoffTag[] }>(`/takeoff/sheets/${sheetId}/tags`, "GET");
}

export function getSheetTag(sheetId: string, tag: string, includeDense = false): Promise<TakeoffTagDetail> {
  return send<TakeoffTagDetail>(
    `/takeoff/sheets/${sheetId}/tags/${encodeURIComponent(tag)}${query({ include_dense: includeDense ? "true" : undefined })}`,
    "GET",
  );
}

export function listSheetShapes(sheetId: string): Promise<TakeoffShapeList> {
  return send<TakeoffShapeList>(`/takeoff/sheets/${sheetId}/shapes`, "GET");
}

export function getSheetShape(sheetId: string, groupId: string): Promise<TakeoffShapeDetail> {
  return send<TakeoffShapeDetail>(`/takeoff/sheets/${sheetId}/shapes/${encodeURIComponent(groupId)}`, "GET");
}

export function previewMeasurement(body: {
  sheet_id: string;
  kind: TakeoffKind;
  quantity_mode?: string;
  geometry: Record<string, unknown>;
  params?: TakeoffParams;
  calibration_id?: string | null;
  source?: TakeoffSource;
  rule_set_code?: string | null;
}): Promise<TakeoffPreview> {
  return send<TakeoffPreview>("/takeoff/preview", "POST", body);
}

export function createMeasurement(sheetId: string, body: TakeoffMeasurementCreate): Promise<TakeoffMeasurement> {
  return send<TakeoffMeasurement>(`/takeoff/sheets/${sheetId}/measurements`, "POST", body);
}

export function updateMeasurement(measurementId: string, body: TakeoffMeasurementUpdate): Promise<TakeoffMeasurement> {
  return send<TakeoffMeasurement>(`/takeoff/measurements/${measurementId}`, "PATCH", body);
}

export function deleteMeasurement(measurementId: string): Promise<void> {
  return send<void>(`/takeoff/measurements/${measurementId}`, "DELETE");
}

export function confirmMeasurement(measurementId: string): Promise<TakeoffMeasurement> {
  return send<TakeoffMeasurement>(`/takeoff/measurements/${measurementId}/confirm`, "POST");
}

export function unconfirmMeasurement(measurementId: string): Promise<TakeoffMeasurement> {
  return send<TakeoffMeasurement>(`/takeoff/measurements/${measurementId}/unconfirm`, "POST");
}

export async function bulkConfirmMeasurements(ids: string[]): Promise<TakeoffBulkConfirm> {
  const out: TakeoffBulkConfirm = { confirmed: [], failed: [] };
  for (let start = 0; start < ids.length; start += 500) {
    const part = await send<TakeoffBulkConfirm>("/takeoff/measurements/bulk-confirm", "POST", {
      ids: ids.slice(start, start + 500),
    });
    out.confirmed.push(...part.confirmed);
    out.failed.push(...part.failed);
  }
  return out;
}

export function getTakeoffReconciliation(projectId: string): Promise<TakeoffReconciliation> {
  return send<TakeoffReconciliation>(`/projects/${projectId}/takeoff/reconciliation`, "GET");
}

export function getProjectTakeoffDrawings(projectId: string): Promise<{ drawings: ProjectTakeoffDrawing[] }> {
  return send<{ drawings: ProjectTakeoffDrawing[] }>(`/projects/${projectId}/takeoff/drawings`, "GET");
}

export function extractSheetItems(
  sheetId: string,
  body: { auto_calibrate?: boolean; budget_seconds?: number } = {},
): Promise<CandidateExtractResult> {
  return send<CandidateExtractResult>(`/takeoff/sheets/${sheetId}/extract`, "POST", body);
}

export function listSheetCandidates(sheetId: string): Promise<CandidateList> {
  return send<CandidateList>(`/takeoff/sheets/${sheetId}/candidates`, "GET");
}

export function extractDrawingItems(
  drawingId: string,
  body: { auto_calibrate?: boolean; budget_seconds?: number } = {},
): Promise<DrawingExtractResult> {
  return send<DrawingExtractResult>(`/drawings/${drawingId}/takeoff/extract`, "POST", body);
}

export function listDrawingCandidates(drawingId: string): Promise<DrawingCandidates> {
  return send<DrawingCandidates>(`/drawings/${drawingId}/takeoff/candidates`, "GET");
}

export function acceptCandidates(body: CandidateAcceptBody): Promise<CandidateAcceptResult> {
  return send<CandidateAcceptResult>("/takeoff/candidates/accept", "POST", body);
}

export function rejectCandidates(ids: string[]): Promise<CandidateDecideResult> {
  return send<CandidateDecideResult>("/takeoff/candidates/reject", "POST", { ids });
}

export function restoreCandidates(ids: string[]): Promise<CandidateDecideResult> {
  return send<CandidateDecideResult>("/takeoff/candidates/restore", "POST", { ids });
}
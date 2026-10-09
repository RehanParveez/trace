import { authenticatedRequest } from "./client";
import type { DrawingUpload } from "./drawingsBoq";
import type {ConfirmImportResult, RebarConfirmResult, RebarImportDetail, RebarRow, RebarRowPayload, RebarSummary, ReviewDecision, ScheduleImport, ScheduleImportDetail,
  ScheduleKind, ScheduleRow, ScheduleRowPayload,
} from "./types";

const BASE = "/drawings-boq";

function filePart(file: DrawingUpload): Blob {
  return {
    uri: file.uri,
    name: file.name,
    type: file.mimeType ?? "application/octet-stream",
  } as unknown as Blob;
}

function json(body: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body) };
}

export function listScheduleImports(projectId: string): Promise<ScheduleImport[]> {
  return authenticatedRequest<ScheduleImport[]>(
    `${BASE}/projects/${projectId}/schedule-imports`,
  );
}

export function importScheduleFile(
  projectId: string,
  file: DrawingUpload,
  kind: ScheduleKind,
  notes?: string,
): Promise<ScheduleImport> {
  const form = new FormData();
  form.append("file", filePart(file));
  form.append("schedule_kind", kind);
  if (notes?.trim()) form.append("notes", notes.trim());
  return authenticatedRequest<ScheduleImport>(
    `${BASE}/projects/${projectId}/schedule-imports/file`,
    { method: "POST", body: form },
  );
}

export function importScheduleFromPdf(
  projectId: string,
  drawingId: string,
  kind: ScheduleKind,
): Promise<ScheduleImport> {
  return authenticatedRequest<ScheduleImport>(
    `${BASE}/projects/${projectId}/schedule-imports/from-pdf`,
    json({ drawing_id: drawingId, schedule_kind: kind, method: "AUTO" }),
  );
}

export function createManualScheduleImport(
  projectId: string,
  kind: ScheduleKind,
): Promise<ScheduleImport> {
  return authenticatedRequest<ScheduleImport>(
    `${BASE}/projects/${projectId}/schedule-imports`,
    json({ schedule_kind: kind }),
  );
}

export function getScheduleImport(importId: string): Promise<ScheduleImportDetail> {
  return authenticatedRequest<ScheduleImportDetail>(
    `${BASE}/schedule-imports/${importId}`,
  );
}

export function addScheduleRow(
  importId: string,
  payload: ScheduleRowPayload,
): Promise<ScheduleRow> {
  return authenticatedRequest<ScheduleRow>(
    `${BASE}/schedule-imports/${importId}/rows`,
    json(payload),
  );
}

export function updateScheduleRow(
  rowId: string,
  payload: ScheduleRowPayload & { review_status?: ReviewDecision; review_note?: string },
): Promise<ScheduleRow> {
  return authenticatedRequest<ScheduleRow>(`${BASE}/schedule-rows/${rowId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function bulkReviewScheduleRows(
  importId: string,
  rowIds: string[],
  status: ReviewDecision,
): Promise<{ updated: number; failed: Record<string, unknown>[] }> {
  return authenticatedRequest(
    `${BASE}/schedule-imports/${importId}/rows/bulk-review`,
    json({ row_ids: rowIds, review_status: status }),
  );
}

export function confirmScheduleImport(
  importId: string,
  rejectPending: boolean,
): Promise<ConfirmImportResult> {
  return authenticatedRequest<ConfirmImportResult>(
    `${BASE}/schedule-imports/${importId}/confirm`,
    json({ reject_pending: rejectPending }),
  );
}

export function rejectScheduleImport(importId: string, note?: string): Promise<ScheduleImport> {
  return authenticatedRequest<ScheduleImport>(
    `${BASE}/schedule-imports/${importId}/reject`,
    json({ note: note?.trim() || null }),
  );
}

export function archiveScheduleImport(importId: string): Promise<ScheduleImport> {
  return authenticatedRequest<ScheduleImport>(
    `${BASE}/schedule-imports/${importId}/archive`,
    { method: "POST" },
  );
}

export function rematchScheduleImport(
  importId: string,
): Promise<{ rows_changed: number; rerun_recommended: boolean }> {
  return authenticatedRequest(`${BASE}/schedule-imports/${importId}/rematch`, {
    method: "POST",
  });
}

export function listRebarImports(projectId: string): Promise<ScheduleImport[]> {
  return authenticatedRequest<ScheduleImport[]>(
    `${BASE}/projects/${projectId}/rebar-imports`,
  );
}

export function importRebarFile(
  projectId: string,
  file: DrawingUpload,
  notes?: string,
): Promise<RebarImportDetail> {
  const form = new FormData();
  form.append("file", filePart(file));
  if (notes?.trim()) form.append("notes", notes.trim());
  return authenticatedRequest<RebarImportDetail>(
    `${BASE}/projects/${projectId}/rebar-imports/file`,
    { method: "POST", body: form },
  );
}

export function importRebarFromPdf(
  projectId: string,
  drawingId: string,
): Promise<RebarImportDetail> {
  return authenticatedRequest<RebarImportDetail>(
    `${BASE}/projects/${projectId}/rebar-imports/from-pdf`,
    json({ drawing_id: drawingId }),
  );
}

export function getRebarImport(importId: string): Promise<RebarImportDetail> {
  return authenticatedRequest<RebarImportDetail>(`${BASE}/rebar-imports/${importId}`);
}

export function updateRebarRow(
  rowId: string,
  payload: RebarRowPayload & { review_status?: ReviewDecision; review_note?: string },
): Promise<RebarRow> {
  return authenticatedRequest<RebarRow>(`${BASE}/rebar-rows/${rowId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function bulkReviewRebarRows(
  importId: string,
  rowIds: string[],
  status: ReviewDecision,
): Promise<{ updated: number; failed: Record<string, unknown>[] }> {
  return authenticatedRequest(
    `${BASE}/rebar-imports/${importId}/rows/bulk-review`,
    json({ row_ids: rowIds, review_status: status }),
  );
}

export function confirmRebarImport(
  importId: string,
  rejectPending: boolean,
): Promise<RebarConfirmResult> {
  return authenticatedRequest<RebarConfirmResult>(
    `${BASE}/rebar-imports/${importId}/confirm`,
    json({ reject_pending: rejectPending }),
  );
}

export function rejectRebarImport(importId: string): Promise<RebarConfirmResult> {
  return authenticatedRequest<RebarConfirmResult>(
    `${BASE}/rebar-imports/${importId}/reject`,
    { method: "POST" },
  );
}

export function archiveRebarImport(importId: string): Promise<RebarConfirmResult> {
  return authenticatedRequest<RebarConfirmResult>(
    `${BASE}/rebar-imports/${importId}/archive`,
    { method: "POST" },
  );
}

export function getRebarSummary(versionId: string): Promise<RebarSummary> {
  return authenticatedRequest<RebarSummary>(
    `${BASE}/boq-versions/${versionId}/rebar-summary`,
  );
}
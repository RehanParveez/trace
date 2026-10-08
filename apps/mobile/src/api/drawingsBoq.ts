import { authenticatedRequest } from "./client";
import type {BOQCustomItemCreatePayload, BOQItem, BOQItemUpdatePayload, BOQSummary, BOQVersion, BOQVersionCreatePayload, BOQVersionUpdatePayload, Drawing, DrawingAudit,
} from "./types";

export function listProjectDrawings(projectId: string): Promise<Drawing[]> {
  return authenticatedRequest<Drawing[]>(
    `/drawings-boq/projects/${projectId}/drawings`,
  );
}

export function listProjectBOQVersions(projectId: string): Promise<BOQVersion[]> {
  return authenticatedRequest<BOQVersion[]>(
    `/drawings-boq/projects/${projectId}/boq-versions`,
  );
}

export function listBOQItems(boqVersionId: string): Promise<BOQItem[]> {
  return authenticatedRequest<BOQItem[]>(
    `/drawings-boq/boq-versions/${boqVersionId}/items`,
  );
}

export function getBOQSummary(boqVersionId: string): Promise<BOQSummary> {
  return authenticatedRequest<BOQSummary>(
    `/drawings-boq/boq-versions/${boqVersionId}/summary`,
  );
}

export type DrawingUpload = {
  uri: string;
  name: string;
  mimeType?: string | null;
};

export function uploadProjectDrawing(
  projectId: string,
  file: DrawingUpload,
): Promise<Drawing> {
  const form = new FormData();
  form.append(
    "file",
    {
      uri: file.uri,
      name: file.name,
      type: file.mimeType ?? "application/octet-stream",
    } as unknown as Blob,
  );

  return authenticatedRequest<Drawing>(
    `/drawings-boq/projects/${projectId}/drawings`,
    { method: "POST", body: form },
  );
}

export function createBOQVersion(
  projectId: string,
  payload: BOQVersionCreatePayload,
): Promise<BOQVersion> {
  return authenticatedRequest<BOQVersion>(
    `/drawings-boq/projects/${projectId}/boq-versions`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function addCustomBOQItem(
  versionId: string,
  payload: BOQCustomItemCreatePayload,
): Promise<BOQItem> {
  return authenticatedRequest<BOQItem>(
    `/drawings-boq/boq-versions/${versionId}/items`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function updateBOQItem(
  itemId: string,
  payload: BOQItemUpdatePayload,
): Promise<BOQItem> {
  return authenticatedRequest<BOQItem>(`/drawings-boq/boq-items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function approveBOQItem(itemId: string): Promise<BOQItem> {
  return authenticatedRequest<BOQItem>(
    `/drawings-boq/boq-items/${itemId}/approve`,
    { method: "POST" },
  );
}

export function suggestBOQItemsFromPDF(
  drawingId: string,
): Promise<{
  boq_version_id: string;
  created_item_count: number;
  items: BOQItem[];
}> {
  return authenticatedRequest(
    `/drawings-boq/drawings/${drawingId}/suggest-items`,
    { method: "POST" },
  );
}

export function getDrawing(drawingId: string): Promise<Drawing> {
  return authenticatedRequest<Drawing>(`/drawings-boq/drawings/${drawingId}`);
}

export function deleteDrawing(drawingId: string): Promise<void> {
  return authenticatedRequest<void>(`/drawings-boq/drawings/${drawingId}`, {
    method: "DELETE",
  });
}

export function reviseDrawing(
  drawingId: string,
  file: DrawingUpload,
  revisionLabel?: string,
): Promise<Drawing> {
  const form = new FormData();
  form.append(
    "file",
    {
      uri: file.uri,
      name: file.name,
      type: file.mimeType ?? "application/octet-stream",
    } as unknown as Blob,
  );
  if (revisionLabel && revisionLabel.trim()) {
    form.append("revision_label", revisionLabel.trim());
  }
  return authenticatedRequest<Drawing>(
    `/drawings-boq/drawings/${drawingId}/revise`,
    { method: "POST", body: form },
  );
}

export function listDrawingRevisions(drawingId: string): Promise<Drawing[]> {
  return authenticatedRequest<Drawing[]>(
    `/drawings-boq/drawings/${drawingId}/revisions`,
  );
}

export function getDrawingAudit(drawingId: string): Promise<DrawingAudit> {
  return authenticatedRequest<DrawingAudit>(
    `/drawings-boq/drawings/${drawingId}/audit`,
  );
}

export function updateBOQVersion(
  versionId: string,
  payload: BOQVersionUpdatePayload,
): Promise<BOQVersion> {
  return authenticatedRequest<BOQVersion>(
    `/drawings-boq/boq-versions/${versionId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export function deleteBOQItem(itemId: string): Promise<void> {
  return authenticatedRequest<void>(`/drawings-boq/boq-items/${itemId}`, {
    method: "DELETE",
  });
}

export function generateLabourItems(versionId: string): Promise<BOQItem[]> {
  return authenticatedRequest<BOQItem[]>(
    `/drawings-boq/boq-versions/${versionId}/labour/generate`,
    { method: "POST" },
  );
}
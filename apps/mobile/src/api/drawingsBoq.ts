import { authenticatedRequest } from "./client";
import type {BOQItem, BOQSummary, BOQVersion, Drawing, BOQCustomItemCreatePayload, BOQItemUpdatePayload, BOQVersionCreatePayload,
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
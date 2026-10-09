import { authenticatedRequest } from "./client";
import type {BuildingLevel, DrawingElement, FinishPreview, Space, SpaceDetail, SpaceFinish, SpaceFinishPayload, SpacePayload, WorkItem,
} from "./types";

const BASE = "/drawings-boq";

function send(method: string, payload?: unknown): RequestInit {
  return payload === undefined ? { method } : { method, body: JSON.stringify(payload) };
}

export function listSpaces(
  projectId: string,
  options: { levelId?: string; includeInactive?: boolean } = {},
): Promise<Space[]> {
  const query = new URLSearchParams();
  if (options.levelId) query.set("level_id", options.levelId);
  if (options.includeInactive) query.set("include_inactive", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return authenticatedRequest<Space[]>(`${BASE}/projects/${projectId}/spaces${suffix}`);
}

export function createSpace(projectId: string, payload: SpacePayload): Promise<Space> {
  return authenticatedRequest<Space>(
    `${BASE}/projects/${projectId}/spaces`,
    send("POST", payload),
  );
}

export function getSpace(spaceId: string): Promise<SpaceDetail> {
  return authenticatedRequest<SpaceDetail>(`${BASE}/spaces/${spaceId}`);
}

export function updateSpace(spaceId: string, payload: SpacePayload): Promise<Space> {
  return authenticatedRequest<Space>(`${BASE}/spaces/${spaceId}`, send("PATCH", payload));
}

export function deleteSpace(spaceId: string): Promise<void> {
  return authenticatedRequest<void>(`${BASE}/spaces/${spaceId}`, send("DELETE"));
}

export function setSpaceBoundaries(
  spaceId: string,
  elementIds: string[],
): Promise<{ boundary_count: number }> {
  return authenticatedRequest(
    `${BASE}/spaces/${spaceId}/boundaries`,
    send("PUT", { element_ids: elementIds }),
  );
}

export function listSpaceFinishes(spaceId: string): Promise<SpaceFinish[]> {
  return authenticatedRequest<SpaceFinish[]>(`${BASE}/spaces/${spaceId}/finishes`);
}

export function setSpaceFinish(
  spaceId: string,
  payload: SpaceFinishPayload,
): Promise<SpaceFinish> {
  return authenticatedRequest<SpaceFinish>(
    `${BASE}/spaces/${spaceId}/finishes`,
    send("POST", payload),
  );
}

export function deleteSpaceFinish(finishId: string): Promise<void> {
  return authenticatedRequest<void>(`${BASE}/space-finishes/${finishId}`, send("DELETE"));
}

export function getFinishPreview(spaceId: string, ruleSetCode?: string): Promise<FinishPreview> {
  const suffix = ruleSetCode?.trim()
    ? `?rule_set_code=${encodeURIComponent(ruleSetCode.trim())}`
    : "";
  return authenticatedRequest<FinishPreview>(
    `${BASE}/spaces/${spaceId}/finish-preview${suffix}`,
  );
}

export function listDrawingLevels(drawingId: string): Promise<BuildingLevel[]> {
  return authenticatedRequest<BuildingLevel[]>(`${BASE}/drawings/${drawingId}/levels`);
}

export function listDrawingElements(
  drawingId: string,
  limit = 500,
): Promise<DrawingElement[]> {
  return authenticatedRequest<DrawingElement[]>(
    `${BASE}/drawings/${drawingId}/elements?limit=${limit}`,
  );
}

export function listWorkItems(): Promise<WorkItem[]> {
  return authenticatedRequest<WorkItem[]>(`${BASE}/work-items`);
}
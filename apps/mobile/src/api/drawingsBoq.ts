import { authenticatedRequest } from "./client";
import type { BOQItem, BOQSummary, BOQVersion, Drawing } from "./types";

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
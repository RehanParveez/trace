import { authenticatedRequest, authenticatedResponse } from "./client";
import type {Adjustment, AdjustmentCreatePayload, BOQBuildResult, BOQItem, BOQVersion, CalculationRun, ExportKind, ItemTrace, PriceVersionResult, ReviewIssue, ReviewIssueStatus, RunStage, Snapshot,
} from "./types";

const BASE = "/drawings-boq";

export function startCalculationRun(
  projectId: string,
  options?: {
    drawing_ids?: string[];
    rule_set_code?: string;
    convention_code?: string;
    force_full?: boolean;
    verify?: boolean;
  },
): Promise<CalculationRun> {
  return authenticatedRequest<CalculationRun>(
    `${BASE}/projects/${projectId}/calculation-runs`,
    { method: "POST", body: JSON.stringify(options ?? {}) },
  );
}

export function getCalculationRun(runId: string): Promise<CalculationRun> {
  return authenticatedRequest<CalculationRun>(`${BASE}/calculation-runs/${runId}`);
}

export function listRunStages(runId: string): Promise<RunStage[]> {
  return authenticatedRequest<RunStage[]>(
    `${BASE}/calculation-runs/${runId}/stages`,
  );
}

export function listProjectCalculationRuns(
  projectId: string,
  limit = 5,
): Promise<CalculationRun[]> {
  return authenticatedRequest<CalculationRun[]>(
    `${BASE}/projects/${projectId}/calculation-runs?limit=${limit}`,
  );
}

export function buildBoqFromRun(runId: string): Promise<BOQBuildResult> {
  return authenticatedRequest<BOQBuildResult>(
    `${BASE}/calculation-runs/${runId}/boq`,
    { method: "POST" },
  );
}

function transition(
  versionId: string,
  action: "submit-review" | "reopen" | "approve" | "issue" | "archive",
  note?: string,
): Promise<BOQVersion> {
  const trimmed = note?.trim();
  const withNote = (action === "approve" || action === "issue") && trimmed;
  return authenticatedRequest<BOQVersion>(
    `${BASE}/boq-versions/${versionId}/${action}`,
    {
      method: "POST",
      ...(withNote ? { body: JSON.stringify({ note: trimmed }) } : {}),
    },
  );
}

export const submitVersionForReview = (id: string) => transition(id, "submit-review");
export const reopenVersion = (id: string) => transition(id, "reopen");
export const approveVersion = (id: string, note?: string) => transition(id, "approve", note);
export const issueVersion = (id: string, note?: string) => transition(id, "issue", note);
export const archiveVersion = (id: string) => transition(id, "archive");

export function listSnapshots(versionId: string): Promise<Snapshot[]> {
  return authenticatedRequest<Snapshot[]>(
    `${BASE}/boq-versions/${versionId}/snapshots`,
  );
}

export function getItemTrace(itemId: string): Promise<ItemTrace> {
  return authenticatedRequest<ItemTrace>(`${BASE}/boq-items/${itemId}/trace`);
}

export function listAdjustments(itemId: string): Promise<Adjustment[]> {
  return authenticatedRequest<Adjustment[]>(
    `${BASE}/boq-items/${itemId}/adjustments`,
  );
}

export function addAdjustment(
  itemId: string,
  payload: AdjustmentCreatePayload,
): Promise<Adjustment> {
  return authenticatedRequest<Adjustment>(
    `${BASE}/boq-items/${itemId}/adjustments`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function revokeAdjustment(
  adjustmentId: string,
  reason: string,
): Promise<Adjustment> {
  return authenticatedRequest<Adjustment>(
    `${BASE}/boq-adjustments/${adjustmentId}/revoke`,
    { method: "POST", body: JSON.stringify({ reason }) },
  );
}

export function waiveItemReview(itemId: string, reason: string): Promise<BOQItem> {
  return authenticatedRequest<BOQItem>(
    `${BASE}/boq-items/${itemId}/waive-review`,
    { method: "POST", body: JSON.stringify({ reason }) },
  );
}

export function confirmItemRate(itemId: string): Promise<BOQItem> {
  return authenticatedRequest<BOQItem>(
    `${BASE}/boq-items/${itemId}/confirm-rate`,
    { method: "POST" },
  );
}

export function priceVersion(versionId: string): Promise<PriceVersionResult> {
  return authenticatedRequest<PriceVersionResult>(
    `${BASE}/boq-versions/${versionId}/price`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export function listReviewIssues(
  projectId: string,
  filters?: { boq_version_id?: string; status?: ReviewIssueStatus },
): Promise<ReviewIssue[]> {
  const q = new URLSearchParams({ project_id: projectId });
  if (filters?.boq_version_id) q.set("boq_version_id", filters.boq_version_id);
  if (filters?.status) q.set("status", filters.status);
  return authenticatedRequest<ReviewIssue[]>(`${BASE}/review-issues?${q.toString()}`);
}

export function resolveReviewIssue(
  issueId: string,
  status: "RESOLVED" | "WAIVED",
  note?: string,
): Promise<ReviewIssue> {
  return authenticatedRequest<ReviewIssue>(`${BASE}/review-issues/${issueId}`, {
    method: "PATCH",
    body: JSON.stringify({ status, note: note?.trim() || null }),
  });
}

export type ExportFile = {
  bytes: Uint8Array;
  filename: string;
  mime: string;
};

export async function downloadExport(
  versionId: string,
  kind: ExportKind,
  fmt: "pdf" | "xlsx",
  options?: { snapshot_id?: string; compare_snapshot_id?: string },
): Promise<ExportFile> {
  const q = new URLSearchParams({ fmt });
  if (options?.snapshot_id) q.set("snapshot_id", options.snapshot_id);
  if (options?.compare_snapshot_id) {
    q.set("compare_snapshot_id", options.compare_snapshot_id);
  }

  const response = await authenticatedResponse(
    `${BASE}/boq-versions/${versionId}/exports/${kind}?${q.toString()}`,
  );
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  const fallback = `${kind.toLowerCase()}.${fmt}`;
  const filename = (match?.[1] ?? fallback).replace(/[^\w.\- ]/g, "_");
  const mime =
    response.headers.get("Content-Type") ??
    (fmt === "pdf"
      ? "application/pdf"
      : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

  return {
    bytes: new Uint8Array(await response.arrayBuffer()),
    filename,
    mime,
  };
}
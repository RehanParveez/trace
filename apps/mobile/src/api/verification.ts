import { authenticatedRequest } from "./client";
import type {ProgressClaim, ProgressClaimCreatePayload, ProgressClaimUpdatePayload, ProgressClaimReviewPayload,
} from "./types";

function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}

export function listProgressClaims(
  projectId: string,
): Promise<ProgressClaim[]> {
  return authenticatedRequest<ProgressClaim[]>(
    `/progress-verification/projects/${projectId}/claims`,
  );
}

export function getProgressClaim(claimId: string): Promise<ProgressClaim> {
  return authenticatedRequest<ProgressClaim>(
    `/progress-verification/claims/${claimId}`,
  );
}

export function createProgressClaim(
  payload: ProgressClaimCreatePayload,
): Promise<ProgressClaim> {
  return authenticatedRequest<ProgressClaim>("/progress-verification/claims", {
    method: "POST",
    body: jsonBody(payload),
  });
}

export function updateProgressClaim(
  claimId: string,
  payload: ProgressClaimUpdatePayload,
): Promise<ProgressClaim> {
  return authenticatedRequest<ProgressClaim>(
    `/progress-verification/claims/${claimId}`,
    {
      method: "PATCH",
      body: jsonBody(payload),
    },
  );
}

export function submitProgressClaim(
  claimId: string,
  version: number,
): Promise<ProgressClaim> {
  return authenticatedRequest<ProgressClaim>(
    `/progress-verification/claims/${claimId}/submit`,
    {
      method: "POST",
      body: jsonBody({ version }),
    },
  );
}

export function approveProgressClaim(
  claimId: string,
  payload: ProgressClaimReviewPayload,
): Promise<ProgressClaim> {
  return authenticatedRequest<ProgressClaim>(
    `/progress-verification/claims/${claimId}/approve`,
    {
      method: "POST",
      body: jsonBody(payload),
    },
  );
}

export function rejectProgressClaim(
  claimId: string,
  payload: ProgressClaimReviewPayload,
): Promise<ProgressClaim> {
  return authenticatedRequest<ProgressClaim>(
    `/progress-verification/claims/${claimId}/reject`,
    {
      method: "POST",
      body: jsonBody(payload),
    },
  );
}
import { useState } from "react";
import { Badge, Button, Field, LoadingState, Modal, inputClass } from "../../organizations/components/OrganizationUi";
import { useApproveProgressClaim, useProgressClaim, useRejectProgressClaim, useSubmitProgressClaim } from "../hooks";
import { formatClaimDate, formatClaimPercentage, formatClaimStatus, getClaimStatusTone } from "../utils/verification.utils";
import { PhotoEvidencePicker } from "./PhotoEvidencePicker";

interface ProgressClaimDetailDialogProps {
  claimId: string;
  projectId: string;
  canSubmit: boolean;
  canReview: boolean;
  onClose: () => void;
}

export function ProgressClaimDetailDialog({ claimId, projectId, canSubmit, canReview, onClose }: ProgressClaimDetailDialogProps) {
  const claimQuery = useProgressClaim(claimId);
  const submitClaim = useSubmitProgressClaim();
  const approveClaim = useApproveProgressClaim();
  const rejectClaim = useRejectProgressClaim();
  const [reviewNote, setReviewNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const claim = claimQuery.data;

  if (!claim) {
    return (
      <Modal title="Progress claim" onClose={onClose}>
        <LoadingState label="Loading claim…" />
      </Modal>
    );
  }

  function handleReview(action: "approve" | "reject") {
    setError(null);
    const mutation = action === "approve" ? approveClaim : rejectClaim;
    mutation.mutate(
      { claimId, payload: { version: claim!.version, note: reviewNote.trim() || null } },
      { onError: () => setError("Someone else may have already reviewed this claim — reload and try again.") },
    );
  }

  return (
    <Modal title="Progress claim" description={formatClaimDate(claim.claim_date)} onClose={onClose} wide>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Badge tone={getClaimStatusTone(claim.status)}>{formatClaimStatus(claim.status)}</Badge>
          <span className="font-mono text-[14px] font-semibold text-[var(--color-text-primary)]">{formatClaimPercentage(claim.claimed_percentage)}</span>
        </div>

        {claim.notes ? <p className="text-[13px] leading-5 text-[var(--color-text-primary)]">{claim.notes}</p> : null}

        {claim.review_note ? (
          <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
            <span className="font-semibold text-[var(--color-text-primary)]">Review note: </span>{claim.review_note}
          </div>
        ) : null}

        <PhotoEvidencePicker claimId={claim.id} projectId={projectId} boqItemId={claim.boq_item_id} canManage={canReview || canSubmit} />

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        {claim.status === "DRAFT" && canSubmit ? (
          <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
            <Button variant="primary" disabled={submitClaim.isPending} onClick={() => submitClaim.mutate(claim.id)}>
              {submitClaim.isPending ? "Submitting…" : "Submit for review"}
            </Button>
          </div>
        ) : null}

        {claim.status === "SUBMITTED" && canReview ? (
          <div className="space-y-2 border-t border-[var(--color-border)] pt-4">
            <Field label="Review note">
              <textarea className={`${inputClass} resize-y`} rows={2} value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} placeholder="Optional" />
            </Field>
            <div className="flex justify-end gap-2">
              <Button variant="danger" disabled={rejectClaim.isPending} onClick={() => handleReview("reject")}>Reject</Button>
              <Button variant="primary" disabled={approveClaim.isPending} onClick={() => handleReview("approve")}>Approve</Button>
            </div>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
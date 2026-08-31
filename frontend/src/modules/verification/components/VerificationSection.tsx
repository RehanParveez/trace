import { useState } from "react";
import { ErrorState, LoadingState } from "../../organizations/components/OrganizationUi";
import { useProgressClaims } from "../hooks";
import type { ProgressClaim } from "../types/verification.types";
import { VERIFICATION_PERMISSIONS } from "../permissions";
import { ProgressClaimForm } from "./ProgressClaimForm";
import { ProgressClaimTable } from "./ProgressClaimTable";
import { ProgressClaimDetailDialog } from "./ProgressClaimDetailDialog";

interface VerificationSectionProps {
  projectId: string;
  permissions: string[];
}

export function VerificationSection({ projectId, permissions }: VerificationSectionProps) {
  const claimsQuery = useProgressClaims(projectId);
  const [formOpen, setFormOpen] = useState(false);
  const [viewingClaim, setViewingClaim] = useState<ProgressClaim | null>(null);

  const canRead = permissions.includes(VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_READ);
  const canCreate = permissions.includes(VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_CREATE);
  const canSubmit = permissions.includes(VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_SUBMIT);
  const canReview = permissions.includes(VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_REVIEW);

  if (!canRead) return null;
  if (claimsQuery.isLoading) return <LoadingState label="Loading progress claims…" />;
  if (claimsQuery.isError) return <ErrorState title="Couldn't load progress claims" onRetry={() => void claimsQuery.refetch()} />;

  return (
    <div>
      <ProgressClaimTable claims={claimsQuery.data ?? []} canCreate={canCreate} onCreate={() => setFormOpen(true)} onView={setViewingClaim} />
      {formOpen ? <ProgressClaimForm projectId={projectId} onClose={() => setFormOpen(false)} /> : null}
      {viewingClaim ? (
        <ProgressClaimDetailDialog
          claimId={viewingClaim.id}
          projectId={projectId}
          canSubmit={canSubmit}
          canReview={canReview}
          onClose={() => setViewingClaim(null)}
        />
      ) : null}
    </div>
  );
}
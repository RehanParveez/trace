import { useState } from "react";
import { ErrorState, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { useProgressClaims } from "../hooks";
import type { ProgressClaim } from "../types/verification.types";
import { VERIFICATION_PERMISSIONS } from "../permissions";
import { ProgressClaimTable } from "../components/ProgressClaimTable";
import { ProgressClaimDetailDialog } from "../components/ProgressClaimDetailDialog";

export function ProgressClaimsReviewPage() {
  const permissions = usePermissionKeys();
  const canReview = permissions.includes(VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_REVIEW);
  const claimsQuery = useProgressClaims(undefined, "SUBMITTED");
  const [viewingClaim, setViewingClaim] = useState<ProgressClaim | null>(null);

  if (!canReview) {
    return (
      <ErrorState
        title="Review access unavailable"
        description="You don't have permission to review progress claims across projects."
      />
    );
  }

  if (claimsQuery.isLoading) return <LoadingState label="Loading claims awaiting review…" />;
  if (claimsQuery.isError) return <ErrorState title="Couldn't load claims" onRetry={() => void claimsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title="Progress claim review" description="Submitted claims across every project, waiting on approval or rejection." />
      <ProgressClaimTable claims={claimsQuery.data ?? []} canCreate={false} onCreate={() => {}} onView={setViewingClaim} />
      {viewingClaim ? (
        <ProgressClaimDetailDialog
          claimId={viewingClaim.id}
          projectId={viewingClaim.project_id}
          canSubmit={false}
          canReview={canReview}
          onClose={() => setViewingClaim(null)}
        />
      ) : null}
    </div>
  );
}
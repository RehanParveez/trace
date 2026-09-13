import { useState } from "react";
import { ErrorState, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { useProgressClaims } from "../hooks";
import type { ProgressClaim } from "../types/verification.types";
import { VERIFICATION_PERMISSIONS } from "../permissions";
import { ProgressClaimTable } from "../components/ProgressClaimTable";
import { ProgressClaimDetailDialog } from "../components/ProgressClaimDetailDialog";
import { useTranslation } from "react-i18next";

export function ProgressClaimsReviewPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canReview = permissions.includes(VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_REVIEW);
  const claimsQuery = useProgressClaims(undefined, "SUBMITTED");
  const [viewingClaim, setViewingClaim] = useState<ProgressClaim | null>(null);

  if (!canReview) {
    return (
      <ErrorState
        title={t("verification.review.accessUnavailable")}
        description={t("verification.review.accessUnavailableDesc")}
      />
    );
  }

  if (claimsQuery.isLoading) return <LoadingState label={t("verification.review.loading")} />;
  if (claimsQuery.isError) return <ErrorState title={t("verification.review.loadError")} onRetry={() => void claimsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title={t("verification.review.pageTitle")} description={t("verification.review.pageDescription")} />
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
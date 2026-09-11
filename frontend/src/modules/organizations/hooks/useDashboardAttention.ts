import type { DashboardAttentionItem } from "../types/organization.types";
import { getInvitationStatus } from "../utils/organization.utils";
import { useInvitations } from "./useInvitations";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useProgressClaims, VERIFICATION_PERMISSIONS } from "../../verification";
import { useSitePhotos } from "../../whatsapp";
import { EXPENSE_PERMISSIONS, useExpenses } from "../../expenses";
import { PROCUREMENT_PERMISSIONS, useProcurementRequests } from "../../procurement";

export function useDashboardAttention(): {
  items: DashboardAttentionItem[];
  isLoading: boolean;
} {
  const permissions = usePermissionKeys();

  const canManageMembers = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MEMBERS_MANAGE,
  );
  const canReviewClaims = permissions.includes(
    VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_REVIEW,
  );
    
  const canManagePhotos = permissions.includes(
    IDENTITY_PERMISSIONS.SITE_PHOTO_MANAGE,
  );

  const canApproveExpenses = permissions.includes(
    EXPENSE_PERMISSIONS.EXPENSE_APPROVE,
  );
  const canManageProcurement = permissions.includes(
    PROCUREMENT_PERMISSIONS.PROCUREMENT_MANAGE,
  );

  const invitationsQuery = useInvitations(0, 100, { enabled: canManageMembers });
  const submittedClaimsQuery = useProgressClaims(undefined, "SUBMITTED");
  const unassignedPhotosQuery = useSitePhotos({ unassignedOnly: true });
  const pendingExpensesQuery = useExpenses(
    { status: "PENDING" },
    { enabled: canApproveExpenses },
  );
  const pendingProcurementQuery = useProcurementRequests(
    { status: "REQUESTED" },
    { enabled: canManageProcurement },
  );

  const items: DashboardAttentionItem[] = [];

  if (canManageMembers) {
    const pendingCount = (invitationsQuery.data?.items ?? []).filter(
      (invitation) => getInvitationStatus(invitation) === "pending",
    ).length;

    if (pendingCount > 0) {
      items.push({
        key: "invitations",
        icon: "mail",
        label: `${pendingCount} invitation${pendingCount === 1 ? "" : "s"} awaiting acceptance`,
        count: pendingCount,
        to: "/app/organization/invitations",
      });
    }
  }

  if (canReviewClaims) {
    const submittedCount = (submittedClaimsQuery.data ?? []).length;

    if (submittedCount > 0) {
      items.push({
        key: "claims",
        icon: "check",
        label: `${submittedCount} progress claim${submittedCount === 1 ? "" : "s"} awaiting review`,
        count: submittedCount,
        to: "/app/progress-review",
      });
    }
  }

  if (canManagePhotos) {
    const unassignedCount = (unassignedPhotosQuery.data ?? []).length;

    if (unassignedCount > 0) {
      items.push({
        key: "photos",
        icon: "spark",
        label: `${unassignedCount} site photo${unassignedCount === 1 ? "" : "s"} need a project`,
        count: unassignedCount,
        to: "/app/site-photos",
      });
    }
  }

  if (canApproveExpenses) {
    const pendingExpenseCount = (pendingExpensesQuery.data ?? []).length;

    if (pendingExpenseCount > 0) {
      items.push({
        key: "expenses",
        icon: "expenses",
        label: `${pendingExpenseCount} expense${pendingExpenseCount === 1 ? "" : "s"} awaiting approval`,
        count: pendingExpenseCount,
        to: "/app/expenses",
      });
    }
  }

  if (canManageProcurement) {
    const pendingProcurementCount = (pendingProcurementQuery.data ?? []).length;

    if (pendingProcurementCount > 0) {
      items.push({
        key: "procurement",
        icon: "procurement",
        label: `${pendingProcurementCount} procurement request${pendingProcurementCount === 1 ? "" : "s"} awaiting approval`,
        count: pendingProcurementCount,
        to: "/app/procurement",
      });
    }
  }

  const isLoading =
    (canManageMembers && invitationsQuery.isLoading) ||
    (canReviewClaims && submittedClaimsQuery.isLoading) ||
    (canManagePhotos && unassignedPhotosQuery.isLoading) ||
    (canApproveExpenses && pendingExpensesQuery.isLoading) ||
    (canManageProcurement && pendingProcurementQuery.isLoading);

  return { items, isLoading };
}
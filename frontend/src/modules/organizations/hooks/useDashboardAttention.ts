import type { DashboardAttentionItem } from "../types/organization.types";
import { getInvitationStatus } from "../utils/organization.utils";
import { useInvitations } from "./useInvitations";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useProgressClaims, VERIFICATION_PERMISSIONS } from "../../verification";
import { useSitePhotos } from "../../whatsapp";
import { useExpenses } from "../../expenses";
import { useProcurementRequests } from "../../procurement";
import { useTranslation } from "react-i18next";
import { useAttentionAlerts, type AttentionKind } from "../../alerts";
import { formatCashFlowMoney } from "../../cash_flow/utils/cash-flow.utils";

const ALERT_ROUTES: Record<AttentionKind, { to: string; icon: DashboardAttentionItem["icon"] }> = {
  CLIENT_BILLS_OVERDUE: { to: "/app/running-bills", icon: "expenses" },
  SUBCONTRACTOR_BILLS_OVERDUE: { to: "/app/subcontractors", icon: "expenses" },
  GUARANTEES_EXPIRING: { to: "/app/bank-guarantees", icon: "spark" },
  TAX_DUE: { to: "/app/sales-tax", icon: "expenses" },
  PROCUREMENT_OVERDUE: { to: "/app/procurement", icon: "procurement" },
  BUDGETS_NEAR_LIMIT: { to: "/app/budgets", icon: "spark" },
};

export function useDashboardAttention(): {
  items: DashboardAttentionItem[];
  isLoading: boolean;
} {
  const { t } = useTranslation();
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
    IDENTITY_PERMISSIONS.EXPENSE_APPROVE,
  );
  const canManageProcurement = permissions.includes(
    IDENTITY_PERMISSIONS.PROCUREMENT_MANAGE,
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

  const alertsQuery = useAttentionAlerts();

  const items: DashboardAttentionItem[] = [];

  if (canManageMembers) {
    const pendingCount = (invitationsQuery.data?.items ?? []).filter(
      (invitation) => getInvitationStatus(invitation) === "pending",
    ).length;

    if (pendingCount > 0) {
      items.push({
        key: "invitations",
        icon: "mail",
        label: t("dashboard.attention.invitations", { count: pendingCount }),
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
        label: t("dashboard.attention.claims", { count: submittedCount }),
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
        label: t("dashboard.attention.photos", { count: unassignedCount }),
        count: unassignedCount,
        to: "/app/site-photos",
      });
    }
  }

  if (canApproveExpenses) {
    const pendingExpenseCount = (pendingExpensesQuery.data?.items ?? []).length;

    if (pendingExpenseCount > 0) {
      items.push({
        key: "expenses",
        icon: "expenses",
        label: t("dashboard.attention.expenses", { count: pendingExpenseCount }),
        count: pendingExpenseCount,
        to: "/app/expenses",
      });
    }
  }

  if (canManageProcurement) {
    const pendingProcurementCount = (pendingProcurementQuery.data?.items ?? []).length;

    if (pendingProcurementCount > 0) {
      items.push({
        key: "procurement",
        icon: "procurement",
        label: t("dashboard.attention.procurement", { count: pendingProcurementCount }),
        count: pendingProcurementCount,
        to: "/app/procurement",
      });
    }
  }

  const alertCurrency = alertsQuery.data?.currency ?? "PKR";
  for (const alert of alertsQuery.data?.items ?? []) {
    const route = ALERT_ROUTES[alert.kind];
    if (!route) continue;
    items.push({
      key: `alert-${alert.kind}`,
      icon: route.icon,
      label: t(`dashboard.attention.alert.${alert.kind}`, {
        count: alert.count,
        amount: alert.amount === null ? "" : formatCashFlowMoney(alert.amount, alertCurrency),
      }),
      count: alert.count,
      to: route.to,
    });
  }

  const isLoading =
    alertsQuery.isLoading ||
    (canManageMembers && invitationsQuery.isLoading) ||
    (canReviewClaims && submittedClaimsQuery.isLoading) ||
    (canManagePhotos && unassignedPhotosQuery.isLoading) ||
    (canApproveExpenses && pendingExpensesQuery.isLoading) ||
    (canManageProcurement && pendingProcurementQuery.isLoading);

  return { items, isLoading };
}
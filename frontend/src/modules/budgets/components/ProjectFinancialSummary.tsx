import { StatCard } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useExpenses } from "../../expenses";
import { useProcurementRequests } from "../../procurement";
import { LABOUR_PERMISSIONS, useLabourSummary } from "../../labour";
import { useProjectBudget } from "../hooks";
import { formatBudgetAmount } from "../utils/budget.utils";
import { useTranslation } from "react-i18next";
import { SUBCONTRACTOR_PERMISSIONS, useProjectSubcontractCost } from "../../subcontractors";

interface ProjectFinancialSummaryProps {
  projectId: string;
}

export function ProjectFinancialSummary({ projectId }: ProjectFinancialSummaryProps) {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();

  const canViewBudget = permissions.includes(IDENTITY_PERMISSIONS.BUDGET_READ);
  const canViewExpenses = permissions.includes(IDENTITY_PERMISSIONS.EXPENSE_READ);
  const canViewProcurement = permissions.includes(IDENTITY_PERMISSIONS.PROCUREMENT_READ);
  const canViewLabour = permissions.includes(LABOUR_PERMISSIONS.LABOUR_READ);
  const canViewSubcontractors = permissions.includes(SUBCONTRACTOR_PERMISSIONS.SUBCONTRACTOR_READ);
  const subcontractCostQuery = useProjectSubcontractCost(projectId, { enabled: canViewSubcontractors });

  const budgetQuery = useProjectBudget(canViewBudget ? projectId : undefined);
  const expensesQuery = useExpenses(
    { projectId, status: "APPROVED" },
    { enabled: canViewExpenses },
  );
  const procurementQuery = useProcurementRequests(
    { projectId },
    { enabled: canViewProcurement },
  );

  const budget = budgetQuery.data ?? null; 

  const labourPeriodStart = budget?.created_at
    ? budget.created_at.slice(0, 10)
    : "2000-01-01";
  const labourPeriodEnd = new Date().toISOString().slice(0, 10);

  const labourSummaryQuery = useLabourSummary(
    projectId,
    labourPeriodStart,
    labourPeriodEnd,
    { enabled: canViewLabour },
  );

  if (!canViewBudget && !canViewExpenses && !canViewProcurement && !canViewLabour) {
    return null;
  }

  const isLoadingFinancials =
    (canViewBudget && budgetQuery.isLoading) ||
    (canViewExpenses && expensesQuery.isLoading) ||
    (canViewProcurement && procurementQuery.isLoading) ||
    (canViewLabour && labourSummaryQuery.isLoading) ||
    (canViewSubcontractors && subcontractCostQuery.isLoading);

  const subcontractedAmount = canViewSubcontractors && subcontractCostQuery.data
    ? Number(subcontractCostQuery.data.total_billed)
    : null;

  const approvedExpenses = expensesQuery.data?.items ?? [];
  const procurementRequests = procurementQuery.data?.items ?? [];

  const approvedAmount = budget ? Number(budget.approved_amount) : null;

  const spentAmount = canViewExpenses
    ? approvedExpenses.reduce((sum, expense) => sum + Number(expense.amount), 0)
    : null;

  const committedAmount = canViewProcurement
    ? procurementRequests
        .filter((request) => request.status === "APPROVED" || request.status === "ORDERED")
        .reduce((sum, request) => sum + Number(request.estimated_amount ?? 0), 0)
    : null;

  const labourAmount =
    canViewLabour && labourSummaryQuery.data
      ? Number(labourSummaryQuery.data.total_accrued_cost)
      : null;

  const remainingAmount =
    approvedAmount !== null
      ? approvedAmount - (spentAmount ?? 0) - (committedAmount ?? 0) - (labourAmount ?? 0)
      : null;

  const currency = budget?.currency ?? "PKR";

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">

      <StatCard
        label={t("dashboard.financial.labour")}         
        value={
          !canViewLabour
            ? t("dashboard.financial.noAccess")
            : isLoadingFinancials
              ? "…"
              : formatBudgetAmount(labourAmount ?? 0, currency)
        }
        note={
        canViewLabour
          ? t("dashboard.financial.labourNote")    
          : t("dashboard.financial.requiresLabour")
        }
        icon="users"
        tone="gold"
      />

    <StatCard
      label="Subcontracted"
      value={!canViewSubcontractors ? "No access" : isLoadingFinancials ? "…" : formatBudgetAmount(subcontractedAmount ?? 0, currency)}
      note={canViewSubcontractors ? "Issued subcontractor bills" : "Requires subcontractor permission"}
      icon="procurement"
      tone="gold"
     />

      <StatCard
        label={t("dashboard.financial.approvedBudget")}
        value={
          !canViewBudget
            ? t("dashboard.financial.noAccess")
            : isLoadingFinancials
              ? "…"
              : approvedAmount === null
                ? t("dashboard.financial.notSet")
                : formatBudgetAmount(approvedAmount, currency)
        }
        note={canViewBudget ? t("budgets.financial.setForProject") : t("dashboard.financial.requiresBudget")}
        icon="budget"
        tone="blue"
      />

      <StatCard
        label={t("dashboard.financial.committed")}
        value={
          !canViewProcurement
            ? t("dashboard.financial.noAccess")
            : isLoadingFinancials
              ? "…"
              : formatBudgetAmount(committedAmount ?? 0, currency)
        }
        note={canViewProcurement ? t("dashboard.financial.committedNote") : t("dashboard.financial.requiresProcurement")}
        icon="procurement"
        tone="gold"
      />

      <StatCard
        label={t("dashboard.financial.spent")}
        value={
          !canViewExpenses
            ? "No access"
            : isLoadingFinancials
              ? "…"
              : formatBudgetAmount(spentAmount ?? 0, currency)
        }
        note={canViewExpenses ? t("dashboard.financial.spentNote") : t("dashboard.financial.requiresExpense")}
        icon="expenses"
        tone="gold"
      />

      <StatCard
        label={t("dashboard.financial.remaining")}
        value={
          isLoadingFinancials
            ? "…"
            : remainingAmount === null
              ? "—"
              : formatBudgetAmount(remainingAmount, currency)
        }
        note={
          remainingAmount === null
            ? t("dashboard.financial.remainingNotSet")
            : remainingAmount < 0
              ? t("budgets.financial.overBudget")
              : t("budgets.financial.available")
        }
        icon="check"
        tone={remainingAmount === null ? "blue" : remainingAmount < 0 ? "red" : "green"}
      />
    </div>
  );
}
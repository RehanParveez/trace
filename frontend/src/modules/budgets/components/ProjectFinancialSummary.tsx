import { StatCard } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { EXPENSE_PERMISSIONS, useExpenses } from "../../expenses";
import { PROCUREMENT_PERMISSIONS, useProcurementRequests } from "../../procurement";
import { BUDGET_PERMISSIONS } from "../permissions";
import { useProjectBudget } from "../hooks";
import { formatBudgetAmount } from "../utils/budget.utils";
import { useTranslation } from "react-i18next";

interface ProjectFinancialSummaryProps {
  projectId: string;
}

export function ProjectFinancialSummary({ projectId }: ProjectFinancialSummaryProps) {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();

  const canViewBudget = permissions.includes(BUDGET_PERMISSIONS.BUDGET_READ);
  const canViewExpenses = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_READ);
  const canViewProcurement = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_READ);

  const budgetQuery = useProjectBudget(canViewBudget ? projectId : undefined);
  const expensesQuery = useExpenses(
    { projectId, status: "APPROVED" },
    { enabled: canViewExpenses },
  );
  const procurementQuery = useProcurementRequests(
    { projectId },
    { enabled: canViewProcurement },
  );

  if (!canViewBudget && !canViewExpenses && !canViewProcurement) {
    return null;
  }

  const isLoadingFinancials =
    (canViewBudget && budgetQuery.isLoading) ||
    (canViewExpenses && expensesQuery.isLoading) ||
    (canViewProcurement && procurementQuery.isLoading);

  const budget = budgetQuery.data ?? null;
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

  const remainingAmount =
    approvedAmount !== null
      ? approvedAmount - (spentAmount ?? 0) - (committedAmount ?? 0)
      : null;

  const currency = budget?.currency ?? "PKR";

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
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
            ? "No access"
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
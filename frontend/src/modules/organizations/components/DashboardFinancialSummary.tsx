import { StatCard } from "./OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { BUDGET_PERMISSIONS, formatBudgetAmount, useBudgetOrganizationSummary } from "../../budgets";
import { EXPENSE_PERMISSIONS, useExpenseOrganizationSummary } from "../../expenses";
import { PROCUREMENT_PERMISSIONS, useProcurementOrganizationSummary } from "../../procurement";
import { useTranslation } from "react-i18next";

export function DashboardFinancialSummary() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();

  const canViewBudget = permissions.includes(BUDGET_PERMISSIONS.BUDGET_READ);
  const canViewExpenses = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_READ);
  const canViewProcurement = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_READ);

  const budgetSummaryQuery = useBudgetOrganizationSummary({ enabled: canViewBudget });
  const expenseSummaryQuery = useExpenseOrganizationSummary({ enabled: canViewExpenses });
  const procurementSummaryQuery = useProcurementOrganizationSummary({ enabled: canViewProcurement });

  if (!canViewBudget && !canViewExpenses && !canViewProcurement) {
    return null;
  }

  const isLoading =
    (canViewBudget && budgetSummaryQuery.isLoading) ||
    (canViewExpenses && expenseSummaryQuery.isLoading) ||
    (canViewProcurement && procurementSummaryQuery.isLoading);

  const currency = budgetSummaryQuery.data?.currency ?? "PKR";

  const approvedTotal = budgetSummaryQuery.data
    ? Number(budgetSummaryQuery.data.total_approved_amount)
    : null;
  const committedTotal = procurementSummaryQuery.data
    ? Number(procurementSummaryQuery.data.total_committed_amount)
    : null;
  const spentTotal = expenseSummaryQuery.data
    ? Number(expenseSummaryQuery.data.total_approved_amount)
    : null;

  const remainingTotal =
    approvedTotal !== null
      ? approvedTotal - (committedTotal ?? 0) - (spentTotal ?? 0)
      : null;

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label={t("dashboard.financial.approvedBudget")}
         value={
          !canViewBudget
            ? t("dashboard.financial.noAccess")
            : isLoading
             ? "…"
             : approvedTotal === null
        ? t("dashboard.financial.notSet")
        : formatBudgetAmount(approvedTotal, currency)
      }  
    note={
      canViewBudget
      ? t("dashboard.financial.acrossProjects", { count: budgetSummaryQuery.data?.budget_count ?? 0 })
      : t("dashboard.financial.requiresBudget")
    }
        icon="budget"
        tone="blue"
      />

      <StatCard
        label={t("dashboard.financial.committed")}
        value={
         !canViewProcurement
          ? t("dashboard.financial.noAccess")
          : isLoading
            ? "…"
            : formatBudgetAmount(committedTotal ?? 0, currency)
           }
        note={
          canViewProcurement
           ? t("dashboard.financial.committedNote")
           : t("dashboard.financial.requiresProcurement")
        }
        icon="procurement"
        tone="gold"
      />

      <StatCard
        label={t("dashboard.financial.spent")}
        value={
          !canViewExpenses
            ? t("dashboard.financial.noAccess")
            : isLoading
             ? "…"
             : formatBudgetAmount(spentTotal ?? 0, currency)
           }
      note={
        canViewExpenses
          ? t("dashboard.financial.spentNote")
          : t("dashboard.financial.requiresExpense")
      }
        icon="expenses"
        tone="gold"
      />

      <StatCard
        label={t("dashboard.financial.remaining")}
        value={
          isLoading
           ? "…"
           : remainingTotal === null
            ? "—"
            : formatBudgetAmount(remainingTotal, currency)
          }
        note={
         remainingTotal === null
          ? t("dashboard.financial.remainingNotSet")
          : remainingTotal < 0
           ? t("dashboard.financial.overBudget")
           : t("dashboard.financial.available")
        }
        icon="check"
        tone={remainingTotal === null ? "blue" : remainingTotal < 0 ? "red" : "green"}
      />
    </div>
  );
}
import { StatCard } from "./OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { BUDGET_PERMISSIONS, formatBudgetAmount, useBudgetOrganizationSummary } from "../../budgets";
import { EXPENSE_PERMISSIONS, useExpenseOrganizationSummary } from "../../expenses";
import { PROCUREMENT_PERMISSIONS, useProcurementOrganizationSummary } from "../../procurement";

export function DashboardFinancialSummary() {
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
        label="Approved budget"
        value={
          !canViewBudget
            ? "No access"
            : isLoading
              ? "…"
              : approvedTotal === null
                ? "Not set"
                : formatBudgetAmount(approvedTotal, currency)
        }
        note={
          canViewBudget
            ? `Across ${budgetSummaryQuery.data?.budget_count ?? 0} project${(budgetSummaryQuery.data?.budget_count ?? 0) === 1 ? "" : "s"}`
            : "Requires budget permission"
        }
        icon="budget"
        tone="blue"
      />

      <StatCard
        label="Committed"
        value={
          !canViewProcurement
            ? "No access"
            : isLoading
              ? "…"
              : formatBudgetAmount(committedTotal ?? 0, currency)
        }
        note={canViewProcurement ? "Approved or ordered procurement" : "Requires procurement permission"}
        icon="procurement"
        tone="gold"
      />

      <StatCard
        label="Spent to date"
        value={
          !canViewExpenses
            ? "No access"
            : isLoading
              ? "…"
              : formatBudgetAmount(spentTotal ?? 0, currency)
        }
        note={canViewExpenses ? "Approved expenses" : "Requires expense permission"}
        icon="expenses"
        tone="gold"
      />

      <StatCard
        label="Remaining"
        value={isLoading ? "…" : remainingTotal === null ? "—" : formatBudgetAmount(remainingTotal, currency)}
        note={
          remainingTotal === null
            ? "Set project budgets to see remaining"
            : remainingTotal < 0
              ? "Over budget across portfolio"
              : "Available across your portfolio"
        }
        icon="check"
        tone={remainingTotal === null ? "blue" : remainingTotal < 0 ? "red" : "green"}
      />
    </div>
  );
}
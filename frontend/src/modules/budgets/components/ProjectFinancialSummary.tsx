import { StatCard } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { EXPENSE_PERMISSIONS, useExpenses } from "../../expenses";
import { PROCUREMENT_PERMISSIONS, useProcurementRequests } from "../../procurement";
import { BUDGET_PERMISSIONS } from "../permissions";
import { useProjectBudget } from "../hooks";
import { formatBudgetAmount } from "../utils/budget.utils";

interface ProjectFinancialSummaryProps {
  projectId: string;
}

export function ProjectFinancialSummary({ projectId }: ProjectFinancialSummaryProps) {
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
  const approvedExpenses = expensesQuery.data ?? [];
  const procurementRequests = procurementQuery.data ?? [];

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
        label="Approved budget"
        value={
          !canViewBudget
            ? "No access"
            : isLoadingFinancials
              ? "…"
              : approvedAmount === null
                ? "Not set"
                : formatBudgetAmount(approvedAmount, currency)
        }
        note={canViewBudget ? "Set for this project" : "Requires budget permission"}
        icon="budget"
        tone="blue"
      />

      <StatCard
        label="Committed"
        value={
          !canViewProcurement
            ? "No access"
            : isLoadingFinancials
              ? "…"
              : formatBudgetAmount(committedAmount ?? 0, currency)
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
            : isLoadingFinancials
              ? "…"
              : formatBudgetAmount(spentAmount ?? 0, currency)
        }
        note={canViewExpenses ? "Approved expenses" : "Requires expense permission"}
        icon="expenses"
        tone="gold"
      />

      <StatCard
        label="Remaining"
        value={
          isLoadingFinancials
            ? "…"
            : remainingAmount === null
              ? "—"
              : formatBudgetAmount(remainingAmount, currency)
        }
        note={
          remainingAmount === null
            ? "Set a budget to see remaining"
            : remainingAmount < 0
              ? "Over budget"
              : "Available after commitments and spend"
        }
        icon="check"
        tone={remainingAmount === null ? "blue" : remainingAmount < 0 ? "red" : "green"}
      />
    </div>
  );
}
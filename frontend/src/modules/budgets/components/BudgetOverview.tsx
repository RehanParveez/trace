import {
  Button, EmptyState, Icon, Panel, PanelHeader, ProgressBar,
} from "../../organizations/components/OrganizationUi";
import type { Budget } from "../types/budget.types";
import { formatBudgetAmount, sumCategoryAllocations } from "../utils/budget.utils";

interface BudgetOverviewProps {
  budget: Budget | null;
  canManage: boolean;
  onEdit: () => void;
}

export function BudgetOverview({ budget, canManage, onEdit }: BudgetOverviewProps) {
  if (!budget) {
    return (
      <Panel>
        <PanelHeader
          eyebrow="PROJECT BUDGET"
          title="No budget set"
          description="Set an approved budget to start tracking this project's financial envelope."
        />
        <EmptyState
          icon="budget"
          title="No budget for this project yet"
          description="Once you set an approved amount, it appears here alongside any category breakdown."
          action={canManage ? <Button variant="primary" onClick={onEdit}>Set budget</Button> : undefined}
        />
      </Panel>
    );
  }

  const categoryTotal = sumCategoryAllocations(budget.categories);
  const approvedAmount = Number(budget.approved_amount);
  const categoryShare = approvedAmount > 0 ? Math.min(100, Math.round((categoryTotal / approvedAmount) * 100)) : 0;

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="PROJECT BUDGET"
        title={formatBudgetAmount(budget.approved_amount, budget.currency)}
        description={budget.notes ?? "Approved budget for this project."}
        action={canManage ? (
          <Button variant="secondary" size="sm" onClick={onEdit}>
            <Icon name="edit" size={13} />
            Edit budget
          </Button>
        ) : undefined}
      />

      {budget.categories.length > 0 ? (
        <div className="p-5 sm:p-6">
          <div className="mb-3 flex items-center justify-between text-[12px] font-semibold text-[var(--color-text-secondary)]">
            <span>Category allocation</span>
            <span>{categoryShare}% of budget allocated</span>
          </div>
          <ProgressBar value={categoryShare} tone={categoryShare > 100 ? "red" : "gold"} />

          <div className="mt-4 space-y-2.5">
            {budget.categories.map((category) => (
              <div
                key={category.id}
                className="flex items-center justify-between gap-4 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-3"
              >
                <span className="text-[13px] font-semibold text-[var(--color-text-primary)]">{category.name}</span>
                <span className="font-mono text-[12.5px] font-semibold text-[var(--color-text-secondary)]">
                  {formatBudgetAmount(category.allocated_amount, budget.currency)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-5 text-[12.5px] text-[var(--color-text-secondary)] sm:p-6">
          No category breakdown has been added for this budget.
        </div>
      )}
    </Panel>
  );
}
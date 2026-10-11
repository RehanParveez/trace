import { StatCard } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useBudgetStatus } from "../hooks";
import { formatBudgetAmount } from "../utils/budget.utils";
import { useTranslation } from "react-i18next";

interface ProjectFinancialSummaryProps {
  projectId: string;
}

function num(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function ProjectFinancialSummary({ projectId }: ProjectFinancialSummaryProps) {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canViewBudget = permissions.includes(IDENTITY_PERMISSIONS.BUDGET_READ);

  const statusQuery = useBudgetStatus(projectId, { enabled: canViewBudget });

  if (!canViewBudget) {
    return null;
  }

  const status = statusQuery.data;
  const loading = statusQuery.isLoading;
  const currency = status?.currency ?? "PKR";
  const fmt = (value: number | string | null | undefined) => {
    const n = num(value);
    return loading ? "…" : n === null ? t("dashboard.financial.noAccess") : formatBudgetAmount(n, currency);
  };

  const hasBudget = Boolean(status?.has_budget);
  const remaining = num(status?.remaining);
  const forecast = num(status?.forecast_total);
  const approved = num(status?.approved_amount);
  const usedPct = status?.used_percentage ?? null;
  const overBudget = hasBudget && remaining !== null && remaining < 0;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label={t("dashboard.financial.approvedBudget")}
          value={loading ? "…" : hasBudget ? formatBudgetAmount(approved, currency) : t("dashboard.financial.notSet")}
          note={hasBudget ? t("budgets.financial.setForProject") : t("dashboard.financial.remainingNotSet")}
          icon="budget"
          tone="blue"
        />
        <StatCard
          label={t("budgets.status.used")}
          value={loading ? "…" : formatBudgetAmount(num(status?.total_used) ?? 0, currency)}
          note={usedPct === null ? t("budgets.status.usedNote") : t("budgets.status.usedPct", { pct: Math.round(usedPct) })}
          icon="expenses"
          tone="gold"
        />
        <StatCard
          label={t("budgets.status.committed")}
          value={fmt(status?.materials_committed)}
          note={t("budgets.status.committedNote")}
          icon="procurement"
          tone="gold"
        />
        <StatCard
          label={t("dashboard.financial.remaining")}
          value={loading ? "…" : !hasBudget ? "—" : formatBudgetAmount(remaining, currency)}
          note={!hasBudget ? t("dashboard.financial.remainingNotSet") : overBudget ? t("budgets.financial.overBudget") : t("budgets.financial.available")}
          icon="check"
          tone={!hasBudget ? "blue" : overBudget ? "red" : "green"}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard label={t("dashboard.financial.labour")} value={fmt(status?.labour_accrued)} note={t("dashboard.financial.labourNote")} icon="users" tone="gold" />
        <StatCard label={t("budgets.status.subcontracted")} value={fmt(status?.subcontracted)} note={t("budgets.status.subcontractedNote")} icon="procurement" tone="gold" />
        <StatCard label={t("budgets.status.materials")} value={fmt(status?.materials_received)} note={t("budgets.status.materialsNote")} icon="procurement" tone="gold" />
        <StatCard label={t("dashboard.financial.spent")} value={fmt(status?.expenses_approved)} note={t("dashboard.financial.spentNote")} icon="expenses" tone="gold" />
        <StatCard
          label={t("budgets.status.pendingExpenses")}
          value={fmt(status?.expenses_pending)}
          note={t("budgets.status.pendingExpensesNote")}
          icon="mail"
          tone="blue"
        />
      </div>

      {hasBudget && forecast !== null && approved !== null && forecast > approved ? (
        <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
          {t("budgets.status.forecastOver", { amount: formatBudgetAmount(forecast - approved, currency) })}
        </div>
      ) : null}

      {status && status.categories.length > 0 ? (
        <div className="overflow-x-auto rounded-[10px] border border-[var(--color-border)]">
          <table className="w-full min-w-[560px] text-left text-[12.5px]">
            <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase tracking-[0.04em] text-[var(--color-text-secondary)]">
              <tr>
                <th className="px-3 py-2">{t("budgets.status.category")}</th>
                <th className="px-3 py-2 text-right">{t("budgets.status.allocated")}</th>
                <th className="px-3 py-2 text-right">{t("budgets.status.spent")}</th>
                <th className="px-3 py-2 text-right">{t("budgets.status.left")}</th>
                <th className="px-3 py-2 w-32">{t("budgets.status.usedCol")}</th>
              </tr>
            </thead>
            <tbody>
              {status.categories.map((category) => {
                const left = num(category.remaining_amount) ?? 0;
                const pct = category.used_percentage;
                const unassigned = category.category_id === null;
                return (
                  <tr key={category.category_id ?? "unassigned"} className="border-t border-[var(--color-border)]">
                    <td className="px-3 py-2 font-medium text-[var(--color-text-primary)]">
                      {unassigned ? t("budgets.status.unassigned") : category.name}
                    </td>
                    <td className="px-3 py-2 text-right">{unassigned ? "—" : formatBudgetAmount(num(category.allocated_amount), currency)}</td>
                    <td className="px-3 py-2 text-right">
                      {formatBudgetAmount(num(category.spent_amount), currency)}
                      {num(category.pending_amount) ? (
                        <span className="block text-[11px] text-[var(--color-text-secondary)]">
                          {t("budgets.status.pendingInline", { amount: formatBudgetAmount(num(category.pending_amount), currency) })}
                        </span>
                      ) : null}
                    </td>
                    <td className={`px-3 py-2 text-right ${!unassigned && left < 0 ? "font-semibold text-[var(--color-danger)]" : ""}`}>
                      {unassigned ? "—" : formatBudgetAmount(left, currency)}
                    </td>
                    <td className="px-3 py-2">
                      {pct === null ? null : (
                        <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
                          <div
                            className={`h-full ${pct > 100 ? "bg-[var(--color-danger)]" : pct > 85 ? "bg-[var(--color-trace-gold)]" : "bg-[var(--color-success)]"}`}
                            style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                          />
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
import { useState } from "react";
import {Badge, Button, ErrorState, Field, inputClass, LoadingState, PageHeader, Panel, PanelHeader, StatCard, TableShell,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { CASH_FLOW_PERMISSIONS } from "../permissions";
import { useCashFlowForecast } from "../hooks";
import { CashFlowChart } from "../components/CashFlowChart";
import { CashFlowSettingsDialog } from "../components/CashFlowSettingsDialog";
import { formatCashFlowCategory, formatCashFlowDate, formatCashFlowMoney } from "../utils/cash-flow.utils";
import { useTranslation } from "react-i18next";

export function CashFlowPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(CASH_FLOW_PERMISSIONS.CASH_FLOW_READ);
  const canManage = permissions.includes(CASH_FLOW_PERMISSIONS.CASH_FLOW_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState<string>(""); // "" = whole organization
  const [horizon, setHorizon] = useState(90);
  const [startingBalanceInput, setStartingBalanceInput] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const startingBalance = startingBalanceInput === "" ? null : Number(startingBalanceInput);
  const forecastQuery = useCashFlowForecast(projectId || undefined, horizon, startingBalance);

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("cashFlow.page.accessUnavailable")} description={t("cashFlow.page.accessUnavailableDesc")} />;
  }
  if (projectsQuery.isLoading) return <LoadingState label={t("cashFlow.page.loadingProjects")} />;

  const forecast = forecastQuery.data;

  return (
    <div className="space-y-7">
      <PageHeader
        title={t("cashFlow.page.title")}
        description={t("cashFlow.page.description")}
        actions={canManage ? <Button variant="secondary" onClick={() => setSettingsOpen(true)}>{t("cashFlow.page.assumptions")}</Button> : null}
      />

      <div className="flex flex-wrap items-end gap-3">
        <Field label={t("cashFlow.page.scope")}>
          <select className={inputClass} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">{t("cashFlow.page.wholeOrganization")}</option>
            {(projectsQuery.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
        <Field label={t("cashFlow.page.horizon")}>
          <select className={inputClass} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            <option value={30}>{t("cashFlow.page.days30")}</option>
            <option value={60}>{t("cashFlow.page.days60")}</option>
            <option value={90}>{t("cashFlow.page.days90")}</option>
          </select>
        </Field>
        <Field label={t("cashFlow.page.startingBalance")} hint={t("cashFlow.page.startingBalanceHint")}>
          <input type="number" className={inputClass} value={startingBalanceInput} onChange={(e) => setStartingBalanceInput(e.target.value)} placeholder={t("cashFlow.page.startingBalancePlaceholder")} />
        </Field>
      </div>

      {forecastQuery.isLoading ? (
        <LoadingState label={t("cashFlow.page.buildingForecast")}/>
      ) : !forecast ? null : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            {[30, 60, 90].filter((d) => d <= horizon).map((days) => {
              const s = forecast.summaries[days];
              return (
                <StatCard
                  key={days}
                  label={t("cashFlow.page.netChange", { days })}
                  value={s ? formatCashFlowMoney(s.cumulative_net, forecast.currency) : "…"}
                  note={s?.projected_balance !== null && s?.projected_balance !== undefined ? t("cashFlow.page.projectedBalance", {amount: formatCashFlowMoney(s.projected_balance, forecast.currency),
                  })
                  : t("cashFlow.page.enterStartingCash")
                  }
                  icon="budget"
                  tone={s && Number(s.cumulative_net) < 0 ? "red" : "green"}
                />
              );
            })}
          </div>

          <CashFlowChart buckets={forecast.weekly_buckets} currency={forecast.currency} />

          <div className="space-y-1.5 rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3.5 py-3">
            {forecast.limitations.map((l, i) => <p key={i} className="text-[12px] text-[var(--color-warning)]">{l}</p>)}
          </div>

          <Panel>
            <PanelHeader eyebrow={t("cashFlow.page.contributingEyebrow")} title={t("cashFlow.page.contributingTitle")} description={t("cashFlow.page.contributingDescription")} />
            <TableShell>
              <table className="w-full min-w-[640px] text-left">
                <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("cashFlow.page.colDate")}</th><th className="px-4 py-3">{t("cashFlow.page.colCategory")}</th><th className="px-4 py-3">{t("cashFlow.page.colDescription")}</th><th className="px-4 py-3 text-right">{t("cashFlow.page.colAmount")}</th></tr></thead>
                <tbody>
                  {forecast.line_items.map((item, i) => (
                    <tr key={i} className="border-t border-[var(--color-border)]">
                      <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">
                        {formatCashFlowDate(item.event_date)}
                        {item.is_overdue ? <Badge tone="red">{t("cashFlow.page.overdue")}</Badge> : null}
                      </td>
                      <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatCashFlowCategory(item.category)}</td>
                      <td className="px-4 py-3.5 text-[13px] text-[var(--color-text-primary)]">{item.description}</td>
                      <td className={`px-4 py-3.5 text-right font-mono text-[13px] font-semibold ${item.direction === "IN" ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}`}>
                        {item.direction === "IN" ? "+" : "-"} {formatCashFlowMoney(item.amount, forecast.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>
          </Panel>
        </>
      )}

      {settingsOpen ? <CashFlowSettingsDialog onClose={() => setSettingsOpen(false)} /> : null}
    </div>
  );
}
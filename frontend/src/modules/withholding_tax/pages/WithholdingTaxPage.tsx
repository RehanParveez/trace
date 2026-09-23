import { useState } from "react";
import {Badge, Button, EmptyState, Field, inputClass, LoadingState, PageHeader, Panel, PanelHeader, StatCard, TableShell,
} from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { WITHHOLDING_TAX_PERMISSIONS } from "../permissions";
import { useWHTDeductions, useWHTRates, useWHTRegisterSummary } from "../hooks";
import { WHTRateForm } from "../components/WHTRateForm";
import { formatWHTCategory, formatWHTMoney } from "../utils/withholding-tax.utils";
import { useTranslation } from "react-i18next";

export function WithholdingTaxPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(WITHHOLDING_TAX_PERMISSIONS.WITHHOLDING_TAX_READ);
  const canManage = permissions.includes(WITHHOLDING_TAX_PERMISSIONS.WITHHOLDING_TAX_MANAGE);

  const ratesQuery = useWHTRates();
  const [formOpen, setFormOpen] = useState(false);

  const monthStart = new Date(); monthStart.setDate(1);
  const periodStart = monthStart.toISOString().slice(0, 10);
  const periodEnd = new Date().toISOString().slice(0, 10);
  const summaryQuery = useWHTRegisterSummary(periodStart, periodEnd);
  const deductionsQuery = useWHTDeductions(periodStart, periodEnd);

  if (!canRead && permissions.length > 0) {
    return <EmptyState icon="alert" title={t("wht.page.accessUnavailable")} description={t("wht.page.accessUnavailableDesc")} />;
  }

  return (
    <div className="space-y-7">
      <PageHeader
        title={t("wht.page.title")}
        description={t("wht.page.description")}
      />

      <StatCard label={t("wht.stat.deductedThisMonth")} value={summaryQuery.data ? formatWHTMoney(summaryQuery.data.total_deducted_amount, summaryQuery.data.currency) : "…"} note={t("wht.stat.acrossCategories")} icon="budget" tone="gold" />

      <Panel>
        <PanelHeader eyebrow={t("wht.rates.eyebrow")} title={t("wht.rates.title")} description={t("wht.rates.description")} action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>{t("wht.rates.setRate")}</Button> : null} />
        {ratesQuery.isLoading ? <LoadingState label={t("wht.rates.loading")} /> : (ratesQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title={t("wht.rates.emptyTitle")} description={t("wht.rates.emptyDesc")} action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>Set rate</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("wht.rates.colCategory")}</th><th className="px-4 py-3 text-right">{t("wht.rates.colFiler")}</th><th className="px-4 py-3 text-right">{t("wht.rates.colNonFiler")}</th><th className="px-4 py-3">{t("wht.rates.colStatus")}</th></tr></thead>
              <tbody>
                {(ratesQuery.data ?? []).map((rate) => (
                  <tr key={rate.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{formatWHTCategory(rate.category)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] text-[var(--color-text-primary)]">{Number(rate.filer_rate_percentage)}%</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] text-[var(--color-text-primary)]">{Number(rate.non_filer_rate_percentage)}%</td>
                    <td className="px-4 py-3.5"><Badge tone={rate.is_active ? "green" : "slate"}>{rate.is_active ? t("common.active") : t("wht.rates.superseded")}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      <Panel>
        <PanelHeader eyebrow={t("wht.deductions.eyebrow")} title={t("wht.deductions.title")} description={t("wht.deductions.description")} />
        {deductionsQuery.isLoading ? <LoadingState label="Loading deductions…" /> : (deductionsQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title={t("wht.deductions.emptyTitle")} description={t("wht.deductions.emptyDesc")} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[680px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("wht.deductions.colPayee")}</th><th className="px-4 py-3">{t("wht.deductions.colCategory")}</th><th className="px-4 py-3 text-right">{t("wht.deductions.colGross")}</th><th className="px-4 py-3 text-right">{t("wht.deductions.colRate")}</th><th className="px-4 py-3 text-right">{t("wht.deductions.colDeducted")}</th></tr></thead>
              <tbody>
                {(deductionsQuery.data ?? []).map((d) => (
                  <tr key={d.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13px] font-medium text-[var(--color-text-primary)]">{d.payee_name}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatWHTCategory(d.category)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{formatWHTMoney(d.gross_amount, d.currency)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{Number(d.rate_percentage)}%</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatWHTMoney(d.deducted_amount, d.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      {formOpen ? <WHTRateForm onClose={() => setFormOpen(false)} /> : null}
    </div>
  );
}
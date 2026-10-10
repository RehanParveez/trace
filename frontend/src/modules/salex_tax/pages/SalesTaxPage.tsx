import { useState } from "react";
import {Badge, Button, EmptyState, LoadingState, PageHeader, Panel, PanelHeader, StatCard, TableShell,
} from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { SALES_TAX_PERMISSIONS } from "../permissions";
import { useSalesTaxCharges, useSalesTaxRates, useSalesTaxRegisterSummary } from "../hooks";
import { SalesTaxRateForm } from "../components/SalesTaxRateForm";
import { formatSalesTaxAuthority, formatSalesTaxMoney } from "../utils/sales-tax.utils";
import { useTranslation } from "react-i18next";
import { monthStartLocal, todayLocal } from "../../../shared/utils/date";

export function SalesTaxPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(SALES_TAX_PERMISSIONS.SALES_TAX_READ);
  const canManage = permissions.includes(SALES_TAX_PERMISSIONS.SALES_TAX_MANAGE);

  const ratesQuery = useSalesTaxRates();
  const [formOpen, setFormOpen] = useState(false);

  const periodStart = monthStartLocal();
  const periodEnd = new Date().toISOString().slice(0, 10);
  const summaryQuery = useSalesTaxRegisterSummary(periodStart, periodEnd);
  const chargesQuery = useSalesTaxCharges(periodStart, periodEnd);

  if (!canRead && permissions.length > 0) {
    return <EmptyState icon="alert" title={t("salesTax.page.accessUnavailable")} description={t("salesTax.page.accessUnavailableDesc")} />;
  }

  return (
    <div className="space-y-7">
      <PageHeader title={t("salesTax.page.title")} description={t("salesTax.page.description")} />

      <StatCard label={t("salesTax.stat.chargedThisMonth")} value={summaryQuery.data ? formatSalesTaxMoney(summaryQuery.data.total_tax_amount, summaryQuery.data.currency) : "…"} note={t("salesTax.stat.acrossAuthorities")} icon="budget" tone="gold" />

      <Panel>
        <PanelHeader eyebrow={t("salesTax.rates.eyebrow")} title={t("salesTax.rates.title")} description={t("salesTax.rates.description")} action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>{t("salesTax.rates.colRate")}</Button> : null} />
        {ratesQuery.isLoading ? <LoadingState label={t("salesTax.rates.loading")} /> : (ratesQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title={t("salesTax.rates.emptyTitle")} description={t("salesTax.rates.emptyDesc")} action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>{t("salesTax.rates.colRate")}</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[500px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("salesTax.rates.colAuthority")}</th><th className="px-4 py-3 text-right">{t("salesTax.rates.colStatus")}</th><th className="px-4 py-3">Status</th></tr></thead>
              <tbody>
                {(ratesQuery.data ?? []).map((rate) => (
                  <tr key={rate.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{formatSalesTaxAuthority(rate.authority)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] text-[var(--color-text-primary)]">{Number(rate.rate_percentage)}%</td>
                    <td className="px-4 py-3.5"><Badge tone={rate.is_active ? "green" : "slate"}>{rate.is_active ? "Active" : "Superseded"}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      <Panel>
        <PanelHeader eyebrow={t("salesTax.charges.eyebrow")} title={t("salesTax.charges.title")} description={t("salesTax.charges.description")} />
        {chargesQuery.isLoading ? <LoadingState label={t("salesTax.charges.loading")} /> : (chargesQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title={t("salesTax.charges.emptyTitle")} description={t("salesTax.charges.emptyDesc")} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[640px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("salesTax.charges.colAuthority")}</th><th className="px-4 py-3 text-right">{t("salesTax.charges.colTaxable")}</th><th className="px-4 py-3 text-right">{t("salesTax.charges.colRate")}</th><th className="px-4 py-3 text-right">{t("salesTax.charges.colTax")}</th></tr></thead>
              <tbody>
                {(chargesQuery.data ?? []).map((c) => (
                  <tr key={c.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13px] text-[var(--color-text-primary)]">{formatSalesTaxAuthority(c.authority)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{formatSalesTaxMoney(c.taxable_amount, c.currency)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{Number(c.rate_percentage)}%</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatSalesTaxMoney(c.tax_amount, c.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      {formOpen ? <SalesTaxRateForm onClose={() => setFormOpen(false)} /> : null}
    </div>
  );
}
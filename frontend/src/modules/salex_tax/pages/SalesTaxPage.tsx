import { useState } from "react";
import {Badge, Button, EmptyState, LoadingState, PageHeader, Panel, PanelHeader, StatCard, TableShell,
} from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { SALES_TAX_PERMISSIONS } from "../permissions";
import { useSalesTaxCharges, useSalesTaxRates, useSalesTaxRegisterSummary } from "../hooks";
import { SalesTaxRateForm } from "../components/SalesTaxRateForm";
import { formatSalesTaxAuthority, formatSalesTaxMoney } from "../utils/sales-tax.utils";

export function SalesTaxPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(SALES_TAX_PERMISSIONS.SALES_TAX_READ);
  const canManage = permissions.includes(SALES_TAX_PERMISSIONS.SALES_TAX_MANAGE);

  const ratesQuery = useSalesTaxRates();
  const [formOpen, setFormOpen] = useState(false);

  const monthStart = new Date(); monthStart.setDate(1);
  const periodStart = monthStart.toISOString().slice(0, 10);
  const periodEnd = new Date().toISOString().slice(0, 10);
  const summaryQuery = useSalesTaxRegisterSummary(periodStart, periodEnd);
  const chargesQuery = useSalesTaxCharges(periodStart, periodEnd);

  if (!canRead && permissions.length > 0) {
    return <EmptyState icon="alert" title="Sales tax unavailable" description="You don't have permission to view this." />;
  }

  return (
    <div className="space-y-7">
      <PageHeader title="Sales tax on services" description="Provincial sales tax charged on running bills and subcontractor bills — a distinct tax from income tax withholding. Configure your current, authority-notified rates below." />

      <StatCard label="Charged this month" value={summaryQuery.data ? formatSalesTaxMoney(summaryQuery.data.total_tax_amount, summaryQuery.data.currency) : "…"} note="Across all authorities" icon="budget" tone="gold" />

      <Panel>
        <PanelHeader eyebrow="RATE CONFIGURATION" title="Rates" description="One active rate per authority. Several can be active at once if you operate across provinces." action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>Set rate</Button> : null} />
        {ratesQuery.isLoading ? <LoadingState label="Loading rates…" /> : (ratesQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title="No rates configured yet" description="Add a rate for each authority you invoice under before generating a bill with sales tax applied." action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>Set rate</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[500px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Authority</th><th className="px-4 py-3 text-right">Rate</th><th className="px-4 py-3">Status</th></tr></thead>
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
        <PanelHeader eyebrow="TAX REGISTER" title="This month's charges" description="For provincial sales tax filing." />
        {chargesQuery.isLoading ? <LoadingState label="Loading charges…" /> : (chargesQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title="No charges this month" description="Sales tax charged on issued bills will appear here." />
        ) : (
          <TableShell>
            <table className="w-full min-w-[640px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Authority</th><th className="px-4 py-3 text-right">Taxable</th><th className="px-4 py-3 text-right">Rate</th><th className="px-4 py-3 text-right">Tax</th></tr></thead>
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
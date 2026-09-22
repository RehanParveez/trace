import { useState } from "react";
import {Badge, Button, EmptyState, Field, inputClass, LoadingState, PageHeader, Panel, PanelHeader, StatCard, TableShell,
} from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { WITHHOLDING_TAX_PERMISSIONS } from "../permissions";
import { useWHTDeductions, useWHTRates, useWHTRegisterSummary } from "../hooks";
import { WHTRateForm } from "../components/WHTRateForm";
import { formatWHTCategory, formatWHTMoney } from "../utils/withholding-tax.utils";

export function WithholdingTaxPage() {
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
    return <EmptyState icon="alert" title="Withholding tax unavailable" description="You don't have permission to view this." />;
  }

  return (
    <div className="space-y-7">
      <PageHeader
        title="Withholding tax"
        description="Configure your organization's current WHT rates and view the deduction register for FBR filing. Rates are never assumed — set your own current, FBR-notified rates below."
      />

      <StatCard label="Deducted this month" value={summaryQuery.data ? formatWHTMoney(summaryQuery.data.total_deducted_amount, summaryQuery.data.currency) : "…"} note="Across all categories" icon="budget" tone="gold" />

      <Panel>
        <PanelHeader eyebrow="RATE CONFIGURATION" title="Rates" description="One active rate per category. Setting a new rate replaces the previous one." action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>Set rate</Button> : null} />
        {ratesQuery.isLoading ? <LoadingState label="Loading rates…" /> : (ratesQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title="No rates configured yet" description="Add a rate for each category you make taxable payments under before recording any deductions." action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>Set rate</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Category</th><th className="px-4 py-3 text-right">Filer</th><th className="px-4 py-3 text-right">Non-filer</th><th className="px-4 py-3">Status</th></tr></thead>
              <tbody>
                {(ratesQuery.data ?? []).map((rate) => (
                  <tr key={rate.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{formatWHTCategory(rate.category)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] text-[var(--color-text-primary)]">{Number(rate.filer_rate_percentage)}%</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] text-[var(--color-text-primary)]">{Number(rate.non_filer_rate_percentage)}%</td>
                    <td className="px-4 py-3.5"><Badge tone={rate.is_active ? "green" : "slate"}>{rate.is_active ? "Active" : "Superseded"}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      <Panel>
        <PanelHeader eyebrow="DEDUCTION REGISTER" title="This month's deductions" description="For your quarterly WHT statement filing with FBR." />
        {deductionsQuery.isLoading ? <LoadingState label="Loading deductions…" /> : (deductionsQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title="No deductions this month" description="Deductions recorded from subcontractor and labour payments will appear here." />
        ) : (
          <TableShell>
            <table className="w-full min-w-[680px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Payee</th><th className="px-4 py-3">Category</th><th className="px-4 py-3 text-right">Gross</th><th className="px-4 py-3 text-right">Rate</th><th className="px-4 py-3 text-right">Deducted</th></tr></thead>
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
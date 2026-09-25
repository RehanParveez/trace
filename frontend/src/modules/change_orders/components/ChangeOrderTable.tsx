import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, StatCard, TableShell } from "../../organizations/components/OrganizationUi";
import type { ChangeOrder, ProjectChangeOrderSummary } from "../types/change-order.types";
import { formatChangeOrderMoney, formatChangeOrderStatus, formatChangeOrderType, getChangeOrderStatusTone } from "../utils/change-order.utils";

interface ChangeOrderTableProps {
  changeOrders: ChangeOrder[];
  summary?: ProjectChangeOrderSummary;
  canCreate: boolean;
  onCreate: () => void;
  onView: (co: ChangeOrder) => void;
}

export function ChangeOrderTable({ changeOrders, summary, canCreate, onCreate, onView }: ChangeOrderTableProps) {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label="Approved net impact" value={summary ? formatChangeOrderMoney(summary.approved_net_value_impact, summary.currency) : "…"} note={summary ? `${summary.approved_count} approved change order${summary.approved_count === 1 ? "" : "s"}` : ""} icon="budget" tone="gold" />
        <StatCard label="Awaiting decision" value={summary?.draft_count ?? "…"} note="Draft change orders" icon="alert" tone={summary && summary.draft_count > 0 ? "gold" : "green"} />
      </div>

      <Panel>
        <PanelHeader
          eyebrow="SCOPE CHANGES"
          title="Change orders"
          description="Additions, omissions and variations against this project's BOQ, and their effect on contract value."
          action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />New change order</Button> : null}
        />

        {changeOrders.length === 0 ? (
          <EmptyState icon="budget" title="No change orders yet" description="Record a scope change here so it's priced, approved, and reflected in future bills — not lost in an email thread." action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>New change order</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[700px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                  <th className="px-4 py-3">CO</th><th className="px-4 py-3">Title</th><th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3 text-right">Value impact</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {changeOrders.map((co) => (
                  <tr key={co.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                    <td className="px-4 py-3.5 text-[14px] font-semibold text-[var(--color-text-primary)]">#{co.change_order_number}</td>
                    <td className="px-4 py-3.5 text-[13px] text-[var(--color-text-primary)]">{co.title}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatChangeOrderType(co.change_type)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatChangeOrderMoney(co.value_impact, co.currency)}</td>
                    <td className="px-4 py-3.5"><Badge tone={getChangeOrderStatusTone(co.status)}>{formatChangeOrderStatus(co.status)}</Badge></td>
                    <td className="px-4 py-3.5 text-right"><Button variant="ghost" size="sm" onClick={() => onView(co)}>View</Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>
    </div>
  );
}
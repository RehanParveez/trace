import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, StatCard, TableShell } from "../../organizations/components/OrganizationUi";
import type { ChangeOrder, ProjectChangeOrderSummary } from "../types/change-order.types";
import { formatChangeOrderMoney, formatChangeOrderStatus, formatChangeOrderType, getChangeOrderStatusTone } from "../utils/change-order.utils";
import { useTranslation } from "react-i18next";

interface ChangeOrderTableProps {
  changeOrders: ChangeOrder[];
  summary?: ProjectChangeOrderSummary;
  canCreate: boolean;
  onCreate: () => void;
  onView: (co: ChangeOrder) => void;
}

export function ChangeOrderTable({ changeOrders, summary, canCreate, onCreate, onView }: ChangeOrderTableProps) {
  const { t } = useTranslation();
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label={t("changeOrders.stat.approvedNet")} value={summary ? formatChangeOrderMoney(summary.approved_net_value_impact, summary.currency) : "…"} note={summary ? t("changeOrders.stat.approvedNote", { count: summary.approved_count }) : ""} icon="budget" tone="gold"
        />
        <StatCard label={t("changeOrders.stat.awaiting")} value={summary?.draft_count ?? "…"} note={t("changeOrders.stat.awaitingNote")} icon="alert" tone={summary && summary.draft_count > 0 ? "gold" : "green"} />
      </div>

      <Panel>
        <PanelHeader
          eyebrow={t("changeOrders.table.eyebrow")}
          title={t("changeOrders.table.title")}
          description={t("changeOrders.table.description")}
          action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />{t("changeOrders.table.new")}</Button> : null}
        />

        {changeOrders.length === 0 ? (
          <EmptyState icon="budget" title={t("changeOrders.table.emptyTitle")} description={t("changeOrders.table.emptyDesc")} action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>{t("changeOrders.table.new")}</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[700px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("changeOrders.table.colCo")}</th> <th className="px-4 py-3">{t("changeOrders.table.colTitle")}</th> <th className="px-4 py-3">{t("changeOrders.table.colType")}</th>
                  <th className="px-4 py-3 text-right">{t("changeOrders.table.colValueImpact")}</th> <th className="px-4 py-3">{t("changeOrders.table.colStatus")}</th> <th className="px-4 py-3 text-right">{t("changeOrders.table.colActions")}</th>
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
                    <td className="px-4 py-3.5 text-right"><Button variant="ghost" size="sm" onClick={() => onView(co)}>{t("changeOrders.table.view")}</Button></td>
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
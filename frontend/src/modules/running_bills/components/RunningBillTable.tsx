import {Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell,
} from "../../organizations/components/OrganizationUi";
import type { RunningBill } from "../types/running-bill.types";
import {formatBillDate, formatBillMoney, formatRunningBillStatus, getRunningBillStatusTone,
} from "../utils/running-bill.utils";
import { useTranslation } from "react-i18next";

interface RunningBillTableProps {
  bills: RunningBill[];
  canCreate: boolean;
  onCreate: () => void;
  onView: (bill: RunningBill) => void;
}

export function RunningBillTable({
  bills,
  canCreate,
  onCreate,
  onView,
}: RunningBillTableProps) {
  const { t } = useTranslation();
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("runningBills.table.eyebrow")}
        title={t("runningBills.table.title")}
        description={t("runningBills.table.description")}
        action={
          canCreate ? (
            <Button variant="primary" size="sm" onClick={onCreate}>
              <Icon name="plus" size={13} />
              {t("runningBills.table.generateBill")}
            </Button>
          ) : null
        }
      />

      {bills.length === 0 ? (
        <EmptyState
          icon="budget"
          title={t("runningBills.table.emptyTitle")}
          description={t("runningBills.table.emptyDescription")}
          action={
            canCreate ? (
              <Button variant="primary" size="sm" onClick={onCreate}>
                {t("runningBills.table.generateBill")}
              </Button>
            ) : undefined
          }
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("runningBills.table.colBill")}</th>
                <th className="px-4 py-3">{t("runningBills.table.colPeriod")}</th>
                <th className="px-4 py-3 text-right">{t("runningBills.table.colNetPayable")}</th>
                <th className="px-4 py-3">{t("runningBills.table.colStatus")}</th>
                <th className="px-4 py-3 text-right">{t("runningBills.table.colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {bills.map((bill) => (
                <tr
                  key={bill.id}
                  className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]"
                >
                  <td className="px-4 py-3.5 text-[14px] font-semibold text-[var(--color-text-primary)]">
                    #{bill.bill_number}
                  </td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">
                    {formatBillDate(bill.period_start)} –{" "}
                    {formatBillDate(bill.period_end)}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">
                    {formatBillMoney(bill.net_payable, bill.currency)}
                  </td>
                  <td className="px-4 py-3.5">
                    <Badge tone={getRunningBillStatusTone(bill.status)}>
                      {formatRunningBillStatus(bill.status)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onView(bill)}
                    >
                       {t("runningBills.table.view")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
import {Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell,
} from "../../organizations/components/OrganizationUi";
import type { RunningBill } from "../types/running-bill.types";
import {formatBillDate, formatBillMoney, formatRunningBillStatus, getRunningBillStatusTone,
} from "../utils/running-bill.utils";

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
  return (
    <Panel>
      <PanelHeader
        eyebrow="CLIENT BILLING"
        title="Running bills / IPCs"
        description="Generated from approved progress claims for this project."
        action={
          canCreate ? (
            <Button variant="primary" size="sm" onClick={onCreate}>
              <Icon name="plus" size={13} />
              Generate bill
            </Button>
          ) : null
        }
      />

      {bills.length === 0 ? (
        <EmptyState
          icon="budget"
          title="No running bills yet"
          description="Once site progress has been claimed and approved, generate a running bill here to send to your client."
          action={
            canCreate ? (
              <Button variant="primary" size="sm" onClick={onCreate}>
                Generate bill
              </Button>
            ) : undefined
          }
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Bill</th>
                <th className="px-4 py-3">Period</th>
                <th className="px-4 py-3 text-right">Net payable</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
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
                      View
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
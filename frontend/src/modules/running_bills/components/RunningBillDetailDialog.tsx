import {Badge, Button, ErrorState, Icon, LoadingState, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import {useCancelRunningBill, useIssueRunningBill, useRunningBill,
} from "../hooks";
import { runningBillsApi } from "../api/running-bills.api";
import {formatBillDate, formatBillMoney, formatRunningBillStatus, getRunningBillStatusTone, openBlobDownload,
} from "../utils/running-bill.utils";

interface RunningBillDetailDialogProps {
  billId: string;
  canIssue: boolean;
  onClose: () => void;
}

export function RunningBillDetailDialog({
  billId,
  canIssue,
  onClose,
}: RunningBillDetailDialogProps) {
  const billQuery = useRunningBill(billId);
  const issueBill = useIssueRunningBill();
  const cancelBill = useCancelRunningBill();
  const { showToast } = useToast();

  const bill = billQuery.data;

  async function handleDownload(format: "pdf" | "xlsx") {
    if (!bill) return;
    try {
      const blob =
        format === "pdf"
          ? await runningBillsApi.downloadPdf(bill.id)
          : await runningBillsApi.downloadXlsx(bill.id);
      openBlobDownload(blob, `running-bill-${bill.bill_number}.${format}`);
    } catch (error) {
      showToast({
        tone: "error",
        title: "Couldn't download this file",
        description: getApiErrorMessage(error, "Please try again."),
      });
    }
  }

  return (
    <Modal
      title={bill ? `Running bill #${bill.bill_number}` : "Running bill"}
      description={
        bill
          ? `${formatBillDate(bill.period_start)} – ${formatBillDate(bill.period_end)}`
          : undefined
      }
      onClose={onClose}
      wide
    >
      {billQuery.isLoading ? (
        <LoadingState label="Loading bill…" />
      ) : billQuery.isError || !bill ? (
        <ErrorState
          title="Couldn't load this bill"
          onRetry={() => void billQuery.refetch()}
        />
      ) : (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <Badge tone={getRunningBillStatusTone(bill.status)}>
              {formatRunningBillStatus(bill.status)}
            </Badge>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void handleDownload("pdf")}
              >
                <Icon name="download" size={13} />
                PDF
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void handleDownload("xlsx")}
              >
                <Icon name="download" size={13} />
                Excel
              </Button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
            <table className="w-full min-w-[720px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                  <th className="px-3 py-2.5">Item</th>
                  <th className="px-3 py-2.5 text-right">Cum. %</th>
                  <th className="px-3 py-2.5 text-right">This period qty</th>
                  <th className="px-3 py-2.5 text-right">Rate</th>
                  <th className="px-3 py-2.5 text-right">This period value</th>
                </tr>
              </thead>
              <tbody>
                {bill.line_items.map((line) => (
                  <tr
                    key={line.id}
                    className="border-t border-[var(--color-border)]"
                  >
                    <td className="px-3 py-2.5 text-[13px] font-medium text-[var(--color-text-primary)]">
                      {line.material_name}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">
                      {Number(line.cumulative_percentage).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">
                      {Number(line.this_period_quantity).toFixed(2)} {line.unit}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">
                      {formatBillMoney(line.unit_rate, bill.currency)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">
                      {formatBillMoney(line.this_period_value, bill.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-1.5 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[13px]">
            <div className="flex justify-between">
              <span className="text-[var(--color-text-secondary)]">
                Gross value this period
              </span>
              <span className="font-semibold text-[var(--color-text-primary)]">
                {formatBillMoney(bill.gross_value_this_period, bill.currency)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-secondary)]">
                Retention ({Number(bill.retention_percentage)}%)
              </span>
              <span className="text-[var(--color-danger)]">
                - {formatBillMoney(bill.retention_this_period, bill.currency)}
              </span>
            </div>
            {Number(bill.advance_recovery_amount) > 0 ? (
              <div className="flex justify-between">
                <span className="text-[var(--color-text-secondary)]">
                  Advance recovery
                </span>
                <span className="text-[var(--color-danger)]">
                  -{" "}
                  {formatBillMoney(
                    bill.advance_recovery_amount,
                    bill.currency,
                  )}
                </span>
              </div>
            ) : null}
            {Number(bill.other_deductions_amount) > 0 ? (
              <div className="flex justify-between">
                <span className="text-[var(--color-text-secondary)]">
                  {bill.other_deductions_note || "Other deductions"}
                </span>
                <span className="text-[var(--color-danger)]">
                  -{" "}
                  {formatBillMoney(
                    bill.other_deductions_amount,
                    bill.currency,
                  )}
                </span>
              </div>
            ) : null}
            <div className="mt-2 flex justify-between border-t border-[var(--color-border)] pt-2 text-[14px] font-bold text-[var(--color-text-primary)]">
              <span>Net payable</span>
              <span>
                {formatBillMoney(bill.net_payable, bill.currency)}
              </span>
            </div>
          </div>

          {canIssue && bill.status === "DRAFT" ? (
            <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
              <Button
                variant="danger"
                disabled={cancelBill.isPending}
                onClick={() =>
                  cancelBill.mutate(
                    { billId: bill.id, version: bill.version },
                    {
                      onSuccess: () =>
                        showToast({
                          tone: "success",
                          title: `Bill #${bill.bill_number} cancelled`,
                        }),
                      onError: (error) =>
                        showToast({
                          tone: "error",
                          title: "Couldn't cancel this bill",
                          description: getApiErrorMessage(
                            error,
                            "Please try again.",
                          ),
                        }),
                    },
                  )
                }
              >
                Cancel bill
              </Button>
              <Button
                variant="primary"
                disabled={issueBill.isPending}
                onClick={() =>
                  issueBill.mutate(
                    { billId: bill.id, version: bill.version },
                    {
                      onSuccess: () =>
                        showToast({
                          tone: "success",
                          title: `Bill #${bill.bill_number} issued`,
                        }),
                      onError: (error) =>
                        showToast({
                          tone: "error",
                          title: "Couldn't issue this bill",
                          description: getApiErrorMessage(
                            error,
                            "Please try again.",
                          ),
                        }),
                    },
                  )
                }
              >
                {issueBill.isPending ? "Issuing…" : "Issue to client"}
              </Button>
            </div>
          ) : null}
        </div>
      )}
    </Modal>
  );
}
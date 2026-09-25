import { useState } from "react";
import { Badge, Button, ErrorState, Field, inputClass, LoadingState, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { useApproveChangeOrder, useCancelChangeOrder, useChangeOrder, useRejectChangeOrder } from "../hooks";
import { formatChangeOrderMoney, formatChangeOrderStatus, getChangeOrderStatusTone } from "../utils/change-order.utils";
import { useTranslation } from "react-i18next";

export function ChangeOrderDetailDialog({ projectId, changeOrderId, canApprove, onClose }: {
  projectId: string; changeOrderId: string; canApprove: boolean; onClose: () => void;
}) {
  const { t } = useTranslation();
  const coQuery = useChangeOrder(changeOrderId);
  const approveCo = useApproveChangeOrder(projectId);
  const rejectCo = useRejectChangeOrder(projectId);
  const cancelCo = useCancelChangeOrder(projectId);
  const { showToast } = useToast();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  const co = coQuery.data;

  return (
    <Modal title={co ? t("changeOrders.detail.title", { number: co.change_order_number }) : t("changeOrders.detail.titleFallback")} description={co?.title} onClose={onClose} wide>
      {coQuery.isLoading || !co ? (
        <LoadingState label={t("changeOrders.detail.loading")} />
      ) : coQuery.isError ? (
        <ErrorState title={t("changeOrders.detail.loadError")} onRetry={() => void coQuery.refetch()} />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Badge tone={getChangeOrderStatusTone(co.status)}>{formatChangeOrderStatus(co.status)}</Badge>
            <span className="font-mono text-[15px] font-bold text-[var(--color-text-primary)]">{formatChangeOrderMoney(co.value_impact, co.currency)}</span>
          </div>

          {co.description ? <p className="text-[13px] leading-5 text-[var(--color-text-secondary)]">{co.description}</p> : null}
          {co.client_reference ? <p className="text-[12px] text-[var(--color-text-muted)]">{t("changeOrders.detail.reference", { ref: co.client_reference })}</p> : null}
          {co.rejection_reason ? (
            <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
              {t("changeOrders.detail.rejected", { reason: co.rejection_reason })}
            </div>
          ) : null}

          <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
            <table className="w-full min-w-[600px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                  <th className="px-3 py-2.5">{t("changeOrders.detail.colDescription")}</th>
                  <th className="px-3 py-2.5">{t("changeOrders.detail.colType")}</th>
                  <th className="px-3 py-2.5 text-right">{t("changeOrders.detail.colQty")}</th>
                  <th className="px-3 py-2.5 text-right">{t("changeOrders.detail.colRate")}</th>
                  <th className="px-3 py-2.5 text-right">{t("changeOrders.detail.colImpact")}</th>
                </tr>
              </thead>
              <tbody>
                {co.line_items.map((line) => (
                  <tr key={line.id} className="border-t border-[var(--color-border)]">
                    <td className="px-3 py-2.5 text-[13px] text-[var(--color-text-primary)]">{line.description}</td>
                    <td className="px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
                      {line.boq_item_id ? t("changeOrders.detail.lineTypeAdjustment") : t("changeOrders.detail.lineTypeNew")}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">
                      {Number(line.quantity) > 0 ? "+" : ""}{Number(line.quantity).toFixed(2)} {line.unit}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">
                      {line.unit_rate !== null ? Number(line.unit_rate).toFixed(2) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">
                      {line.realized_value_impact !== null
                        ? formatChangeOrderMoney(line.realized_value_impact, co.currency)
                        : t("changeOrders.detail.pendingApproval")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {canApprove && co.status === "DRAFT" ? (
            rejecting ? (
              <div className="space-y-3 border-t border-[var(--color-border)] pt-4">
                <Field label={t("changeOrders.detail.rejectionReason")}>
                  <textarea className={`${inputClass} resize-y`} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
                </Field>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" onClick={() => setRejecting(false)}>{t("changeOrders.detail.back")}</Button>
                  <Button
                    variant="danger"
                    disabled={rejectCo.isPending || !reason.trim()}
                    onClick={() =>
                      rejectCo.mutate(
                        { id: co.id, version: co.version, reason: reason.trim() },
                        { onSuccess: () => showToast({ tone: "success", title: t("changeOrders.detail.rejectedToast") }) },
                      )
                    }
                  >
                    {rejectCo.isPending ? t("changeOrders.detail.rejecting") : t("changeOrders.detail.confirmRejection")}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
                <Button
                  variant="ghost"
                  disabled={cancelCo.isPending}
                  onClick={() =>
                    cancelCo.mutate(
                      { id: co.id, version: co.version },
                      { onSuccess: () => showToast({ tone: "success", title: t("changeOrders.detail.cancelledToast") }) },
                    )
                  }
                >
                  {t("changeOrders.detail.cancelCo")}
                </Button>
                <Button variant="danger" onClick={() => setRejecting(true)}>{t("changeOrders.detail.reject")}</Button>
                <Button
                  variant="primary"
                  disabled={approveCo.isPending}
                  onClick={() =>
                    approveCo.mutate(
                      { id: co.id, version: co.version },
                      {
                        onSuccess: () =>
                          showToast({
                            tone: "success",
                            title: t("changeOrders.detail.approvedToast", {
                              amount: formatChangeOrderMoney(co.value_impact, co.currency),
                            }),
                          }),
                      },
                    )
                  }
                >
                  {approveCo.isPending ? t("changeOrders.detail.approving") : t("changeOrders.detail.approve")}
                </Button>
              </div>
            )
          ) : null}
        </div>
      )}
    </Modal>
  );
}
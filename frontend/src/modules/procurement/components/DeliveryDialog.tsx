import { useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { getApiErrorCode } from "../../../shared/utils/apiError";
import { todayLocal } from "../../../shared/utils/date";
import { useProcurementDeliveries, useRecordDelivery, useVoidDelivery } from "../hooks";
import type { ProcurementRequest } from "../types/procurement.types";
import { formatProcurementAmount, formatProcurementDate } from "../utils/procurement.utils";
import { useTranslation } from "react-i18next";

interface DeliveryDialogProps {
  request: ProcurementRequest;
  canManage: boolean;
  onClose: () => void;
}

export function DeliveryDialog({ request, canManage, onClose }: DeliveryDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const deliveriesQuery = useProcurementDeliveries(request.id);
  const recordDelivery = useRecordDelivery(request.id);
  const voidDelivery = useVoidDelivery();

  const ordered = Number(request.quantity);
  const delivered = Number(request.delivered_quantity ?? 0);
  const remaining = Math.max(0, ordered - delivered);
  const open = request.status === "APPROVED" || request.status === "ORDERED";

  const [receivedDate, setReceivedDate] = useState(() => todayLocal());
  const [quantity, setQuantity] = useState(remaining > 0 ? String(remaining) : "");
  const [supplier, setSupplier] = useState(request.supplier_name ?? "");
  const [invoice, setInvoice] = useState("");
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [overDelivery, setOverDelivery] = useState(false);
  const [voidingId, setVoidingId] = useState<string | null>(null);
  const [voidReason, setVoidReason] = useState("");

  function submit(event?: FormEvent<HTMLFormElement>, allowOver = false) {
    event?.preventDefault();
    setError(null);
    recordDelivery.mutate(
      {
        received_date: receivedDate,
        quantity: Number(quantity),
        supplier_name: supplier.trim() || null,
        invoice_number: invoice.trim() || null,
        amount: amount === "" ? null : Number(amount),
        notes: notes.trim() || null,
        allow_over_delivery: allowOver,
      },
      {
        onSuccess: () => {
          showToast({ tone: "success", title: t("procurement.delivery.recorded", { name: request.material_name }) });
          onClose();
        },
        onError: (err) => {
          if (getApiErrorCode(err) === "DELIVERY_EXCEEDS_ORDER") {
            setOverDelivery(true);
          }
          setError(getApiErrorMessage(err, t("procurement.delivery.saveError")));
        },
      },
    );
  }

  function submitVoid(deliveryId: string) {
    voidDelivery.mutate(
      { deliveryId, reason: voidReason.trim() },
      {
        onSuccess: () => {
          setVoidingId(null);
          setVoidReason("");
          showToast({ tone: "success", title: t("procurement.delivery.voided") });
        },
        onError: (err) => showToast({ tone: "error", title: t("procurement.delivery.voidError"), description: getApiErrorMessage(err, t("procurement.delivery.voidError")) }),
      },
    );
  }

  const deliveries = deliveriesQuery.data ?? [];

  return (
    <Modal
      title={t("procurement.delivery.title", { name: request.material_name })}
      description={t("procurement.delivery.progress", { delivered, ordered, unit: request.unit })}
      onClose={onClose}
      wide
    >
      <div className="space-y-5">
        {deliveries.length > 0 ? (
          <div className="overflow-x-auto rounded-[10px] border border-[var(--color-border)]">
            <table className="w-full min-w-[520px] text-left text-[12.5px]">
              <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase tracking-[0.04em] text-[var(--color-text-secondary)]">
                <tr>
                  <th className="px-3 py-2">{t("procurement.delivery.colDate")}</th>
                  <th className="px-3 py-2 text-right">{t("procurement.delivery.colQty")}</th>
                  <th className="px-3 py-2">{t("procurement.delivery.colSupplier")}</th>
                  <th className="px-3 py-2 text-right">{t("procurement.delivery.colAmount")}</th>
                  {canManage ? <th className="px-3 py-2" /> : null}
                </tr>
              </thead>
              <tbody>
                {deliveries.map((delivery) => (
                  <tr key={delivery.id} className={`border-t border-[var(--color-border)] ${delivery.voided_at ? "opacity-60" : ""}`}>
                    <td className="px-3 py-2">{formatProcurementDate(delivery.received_date)}</td>
                    <td className="px-3 py-2 text-right font-mono">
                      {delivery.voided_at ? <s>{delivery.quantity}</s> : delivery.quantity} {delivery.unit}
                    </td>
                    <td className="px-3 py-2">
                      {delivery.supplier_name ?? "—"}
                      {delivery.invoice_number ? <span className="block text-[11px] text-[var(--color-text-secondary)]">#{delivery.invoice_number}</span> : null}
                    </td>
                    <td className="px-3 py-2 text-right font-mono">{formatProcurementAmount(delivery.amount)}</td>
                    {canManage ? (
                      <td className="px-3 py-2 text-right">
                        {delivery.voided_at ? (
                          <Badge tone="red">{t("procurement.delivery.voidedBadge")}</Badge>
                        ) : voidingId === delivery.id ? (
                          <div className="flex items-center justify-end gap-1">
                            <input className={`${inputClass} !h-8 w-40`} placeholder={t("procurement.delivery.voidReason")} value={voidReason} onChange={(e) => setVoidReason(e.target.value)} />
                            <Button variant="danger" size="sm" disabled={voidReason.trim().length < 3 || voidDelivery.isPending} onClick={() => submitVoid(delivery.id)}>
                              {t("procurement.delivery.void")}
                            </Button>
                          </div>
                        ) : (
                          <Button variant="ghost" size="sm" onClick={() => setVoidingId(delivery.id)}>{t("procurement.delivery.void")}</Button>
                        )}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {canManage && open ? (
          <form onSubmit={(event) => submit(event, false)} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label={t("procurement.delivery.date")}>
                <input type="date" required max={todayLocal()} className={inputClass} value={receivedDate} onChange={(e) => setReceivedDate(e.target.value)} />
              </Field>
              <Field label={t("procurement.delivery.quantity", { unit: request.unit })} hint={remaining > 0 ? t("procurement.delivery.remainingHint", { remaining, unit: request.unit }) : undefined}>
                <input type="number" step="any" min="0.001" required className={inputClass} value={quantity} onChange={(e) => { setQuantity(e.target.value); setOverDelivery(false); }} />
              </Field>
              <Field label={t("procurement.delivery.amount")} hint={t("procurement.delivery.amountHint")}>
                <input type="number" step="any" min="0" className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} />
              </Field>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("procurement.delivery.supplier")}>
                <input className={inputClass} value={supplier} onChange={(e) => setSupplier(e.target.value)} />
              </Field>
              <Field label={t("procurement.delivery.invoice")}>
                <input className={inputClass} value={invoice} onChange={(e) => setInvoice(e.target.value)} />
              </Field>
            </div>
            <Field label={t("procurement.delivery.notes")}>
              <input className={inputClass} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </Field>

            {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

            <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
              <Button type="button" variant="ghost" onClick={onClose} disabled={recordDelivery.isPending}>{t("common.cancel")}</Button>
              {overDelivery ? (
                <Button type="button" variant="danger" disabled={recordDelivery.isPending} onClick={() => submit(undefined, true)}>
                  {t("procurement.delivery.receiveAnyway")}
                </Button>
              ) : (
                <Button type="submit" variant="primary" disabled={recordDelivery.isPending || !quantity}>
                  {recordDelivery.isPending ? t("common.saving") : t("procurement.delivery.record")}
                </Button>
              )}
            </div>
          </form>
        ) : (
          <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
            <Button variant="ghost" onClick={onClose}>{t("common.close", "Close")}</Button>
          </div>
        )}
      </div>
    </Modal>
  );
}
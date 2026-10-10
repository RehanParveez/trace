import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Badge, Button, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { runningBillsApi } from "../api/running-bills.api";
import { invalidateBillAfterCollectionChange, useCancelRunningBill, useRunningBillCollections } from "../hooks/useRunningBills";
import { formatBillDate, formatBillMoney } from "../utils/running-bill.utils";
import { todayLocal } from "../../../shared/utils/date";
import type { RunningBillDetail } from "../types/running-bill.types";

interface Props {
  bill: RunningBillDetail;
  canManage: boolean;
}

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const inputClass =
  "rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12.5px] outline-none";

export function RunningBillCollections({ bill, canManage }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const collectionsQuery = useRunningBillCollections(bill.id);
  const cancelBill = useCancelRunningBill();

  const [amount, setAmount] = useState("");
  const [wht, setWht] = useState("");
  const [date, setDate] = useState(() => todayLocal());
  const [reference, setReference] = useState("");
  const [key, setKey] = useState(newKey);
  const [saving, setSaving] = useState(false);
  const [voidingId, setVoidingId] = useState<string | null>(null);
  const [voidReason, setVoidReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const totalDue = Number(bill.net_payable) + Number(bill.sales_tax_amount);
  const collected = Number(bill.collected_amount);
  const outstanding = totalDue - collected;
  const entered = Number(amount || 0) + Number(wht || 0);
  const collections = collectionsQuery.data ?? [];
  const activeCollections = collections.filter((c) => !c.voided_at);
  const whtTotal = activeCollections.reduce((sum, c) => sum + Number(c.client_wht_amount), 0);

  function refresh() {
    invalidateBillAfterCollectionChange(queryClient, bill.id, bill.project_id);
  }

  async function handleRecord() {
    setSaving(true);
    try {
      await runningBillsApi.recordCollection(bill.id, {
        amount: Number(amount || 0),
        client_wht_amount: Number(wht || 0),
        collection_date: date,
        reference: reference.trim() || null,
        idempotency_key: key,
      });
      setAmount("");
      setWht("");
      setReference("");
      setKey(newKey());
      refresh();
      showToast({ tone: "success", title: t("runningBills.collections.recorded", "Collection recorded") });
    } catch (error) {
      showToast({
        tone: "error",
        title: t("runningBills.collections.recordError", "Could not record collection"),
        description: getApiErrorMessage(error, t("common.retry")),
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleVoid(collectionId: string) {
    try {
      await runningBillsApi.voidCollection(bill.id, collectionId, voidReason.trim());
      setVoidingId(null);
      setVoidReason("");
      refresh();
      showToast({ tone: "success", title: t("runningBills.collections.voided", "Collection voided") });
    } catch (error) {
      showToast({
        tone: "error",
        title: t("runningBills.collections.voidError", "Could not void collection"),
        description: getApiErrorMessage(error, t("common.retry")),
      });
    }
  }

  function handleCancelIssued() {
    cancelBill.mutate(
      { billId: bill.id, version: bill.version, reason: cancelReason.trim() },
      {
        onSuccess: () => {
          setCancelling(false);
          showToast({
            tone: "success",
            title: t("runningBills.detail.cancelledToast", { number: bill.bill_number }),
          });
        },
        onError: (error) =>
          showToast({
            tone: "error",
            title: t("runningBills.detail.cancelError"),
            description: getApiErrorMessage(error, t("common.retry")),
          }),
      },
    );
  }

  return (
    <div className="space-y-3 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[12px] text-[var(--color-text-secondary)]">
        {formatBillMoney(collected, bill.currency)} {t("runningBills.collections.collectedOf", "collected of")}{" "}
        {formatBillMoney(totalDue, bill.currency)} — {formatBillMoney(outstanding, bill.currency)}{" "}
        {t("runningBills.collections.outstanding", "outstanding")}.
        {whtTotal > 0 ? (
          <span className="ms-1">
            {t("runningBills.collections.whtTotal", "Tax withheld by client so far:")}{" "}
            <strong>{formatBillMoney(whtTotal, bill.currency)}</strong>
          </span>
        ) : null}
      </div>

      {canManage && bill.status === "ISSUED" && outstanding > 0 ? (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <input
              type="number" step="any" min="0" inputMode="decimal"
              placeholder={t("runningBills.collections.amountReceived", "Amount received")}
              value={amount} onChange={(e) => setAmount(e.target.value)}
              className={`${inputClass} w-36`}
            />
            <input
              type="number" step="any" min="0" inputMode="decimal"
              placeholder={t("runningBills.collections.whtWithheld", "Tax client withheld")}
              value={wht} onChange={(e) => setWht(e.target.value)}
              className={`${inputClass} w-36`}
            />
            <input type="date" value={date} max={todayLocal()} onChange={(e) => setDate(e.target.value)} className={inputClass} />
            <input
              type="text" maxLength={120}
              placeholder={t("runningBills.collections.reference", "Cheque / IBFT ref")}
              value={reference} onChange={(e) => setReference(e.target.value)}
              className={`${inputClass} w-40`}
            />
            <Button variant="secondary" size="sm" disabled={saving || entered <= 0} onClick={() => void handleRecord()}>
              {saving ? t("common.saving", "Saving…") : t("runningBills.collections.record", "Record collection")}
            </Button>
          </div>
          {entered > outstanding ? (
            <div className="text-[11.5px] text-[var(--color-danger)]">
              {t("runningBills.collections.exceeds", "That is more than what is outstanding.")}
            </div>
          ) : null}
        </div>
      ) : null}

      {collections.length > 0 ? (
        <div className="overflow-x-auto rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full min-w-[520px] text-left text-[12px]">
            <thead>
              <tr className="text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-2 py-1.5">{t("runningBills.collections.colDate", "Date")}</th>
                <th className="px-2 py-1.5">{t("runningBills.collections.colRef", "Reference")}</th>
                <th className="px-2 py-1.5 text-right">{t("runningBills.collections.colReceived", "Received")}</th>
                <th className="px-2 py-1.5 text-right">{t("runningBills.collections.colWht", "Tax withheld")}</th>
                <th className="px-2 py-1.5" />
              </tr>
            </thead>
            <tbody>
              {collections.map((c) => (
                <tr key={c.id} className={`border-t border-[var(--color-border)] ${c.voided_at ? "opacity-50 line-through" : ""}`}>
                  <td className="px-2 py-1.5">{formatBillDate(c.collection_date)}</td>
                  <td className="px-2 py-1.5">{c.reference ?? "—"}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{formatBillMoney(c.amount_received, bill.currency)}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{formatBillMoney(c.client_wht_amount, bill.currency)}</td>
                  <td className="px-2 py-1.5 text-right">
                    {c.voided_at ? (
                      <Badge tone="slate">{t("runningBills.collections.voidedBadge", "Voided")}</Badge>
                    ) : canManage ? (
                      voidingId === c.id ? (
                        <span className="flex items-center justify-end gap-1">
                          <input
                            autoFocus value={voidReason} onChange={(e) => setVoidReason(e.target.value)}
                            placeholder={t("runningBills.collections.voidReason", "Reason")}
                            className={`${inputClass} w-32`}
                          />
                          <Button variant="danger" size="sm" disabled={voidReason.trim().length < 3} onClick={() => void handleVoid(c.id)}>
                            {t("runningBills.collections.void", "Void")}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setVoidingId(null)}>
                            {t("common.cancel", "Cancel")}
                          </Button>
                        </span>
                      ) : (
                        <Button variant="ghost" size="sm" onClick={() => { setVoidingId(c.id); setVoidReason(""); }}>
                          {t("runningBills.collections.void", "Void")}
                        </Button>
                      )
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {canManage && bill.status === "ISSUED" && activeCollections.length === 0 ? (
        <div className="border-t border-[var(--color-border)] pt-2">
          {cancelling ? (
            <div className="flex flex-wrap items-center gap-2">
              <input
                autoFocus value={cancelReason} onChange={(e) => setCancelReason(e.target.value)}
                placeholder={t("runningBills.collections.cancelReason", "Why is this issued bill being cancelled?")}
                className={`${inputClass} w-72`}
              />
              <Button variant="danger" size="sm" disabled={cancelReason.trim().length < 3 || cancelBill.isPending} onClick={handleCancelIssued}>
                {t("runningBills.collections.confirmCancel", "Cancel bill and reverse its tax")}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setCancelling(false)}>
                {t("common.back", "Back")}
              </Button>
            </div>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => setCancelling(true)}>
              {t("runningBills.collections.cancelIssued", "Cancel this issued bill…")}
            </Button>
          )}
        </div>
      ) : null}
    </div>
  );
}
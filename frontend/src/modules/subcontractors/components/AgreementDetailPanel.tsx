import { useState } from "react";
import type { FormEvent } from "react";
import {Badge, Button, EmptyState, Field, inputClass, Modal, Panel, PanelHeader, StatCard, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import {useAdvances, useBills, useCancelBill, useCreateAdvance, useCreateBill, useCreatePayment, useIssueBill, useLedger, usePayments,
} from "../hooks";
import { subcontractorsApi } from "../api/subcontractors.api";
import type { SubcontractAgreementDetail, SubcontractorBill } from "../types/subcontractor.types";
import { formatDate, formatMoney, getBillStatusTone, openBlobDownload } from "../utils/subcontractor.utils";
import { useWHTPreview } from "../../withholding_tax"; 
import type { WHTCategory } from "../../withholding_tax";
import { formatWHTMoney } from "../../withholding_tax";
import { useTranslation } from "react-i18next";

export function AgreementDetailPanel({ agreement, subcontractor, canManage, canManagePayments, onClose }: {
  agreement: SubcontractAgreementDetail; subcontractor: { is_active_taxpayer: boolean }; canManage: boolean; canManagePayments: boolean; onClose: () => void;
}) {
  const { t } = useTranslation();
  const billsQuery = useBills(agreement.id);
  const ledgerQuery = useLedger(agreement.id);
  const advancesQuery = useAdvances(agreement.id);
  const paymentsQuery = usePayments(agreement.id);
  const { showToast } = useToast();

  const [billFormOpen, setBillFormOpen] = useState(false);
  const [advanceFormOpen, setAdvanceFormOpen] = useState(false);
  const [paymentFormOpen, setPaymentFormOpen] = useState(false);
  const [viewingBillId, setViewingBillId] = useState<string | null>(null);

  const ledger = ledgerQuery.data;

  return (
    <Modal title={agreement.scope_description} description={t("subcontractors.detail.contractValue", { value: formatMoney(agreement.contract_value) })} onClose={onClose} wide>
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <StatCard label={t("subcontractors.detail.billedToDate")} value={ledger ? formatMoney(ledger.total_billed, ledger.currency) : "…"} note={t("subcontractors.detail.billedNote")} icon="budget" tone="gold" />
          <StatCard label={t("subcontractors.detail.outstanding")} value={ledger ? formatMoney(ledger.outstanding_bill_balance, ledger.currency) : "…"} note={t("subcontractors.detail.outstandingNote")} icon="alert" tone={Number(ledger?.outstanding_bill_balance ?? 0) > 0 ? "gold" : "green"} />
        </div>

        <Panel>
          <PanelHeader eyebrow={t("subcontractors.detail.billsEyebrow")} title={t("subcontractors.detail.billsTitle")} description={t("subcontractors.detail.billsDescription")} action={canManage ? <Button variant="primary" size="sm" onClick={() => setBillFormOpen(true)}>{t("subcontractors.detail.generateBill")}</Button> : null} />
          {(billsQuery.data ?? []).length === 0 ? (
            <EmptyState icon="budget" title={t("subcontractors.detail.noBillsTitle")} description={t("subcontractors.detail.noBillsDesc")} />
          ) : (
            <TableShell>
              <table className="w-full min-w-[560px] text-left">
                <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("subcontractors.detail.colBill")}</th><th className="px-4 py-3">{t("subcontractors.detail.colPeriod")}</th><th className="px-4 py-3 text-right">{t("subcontractors.detail.colNetPayable")}</th><th className="px-4 py-3"></th>{t("subcontractors.detail.colStatus")}<th className="px-4 py-3 text-right">{t("subcontractors.detail.colActions")}</th></tr></thead>
                <tbody>
                  {(billsQuery.data ?? []).map((bill) => (
                    <tr key={bill.id} className="border-t border-[var(--color-border)]">
                      <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">#{bill.bill_number}</td>
                      <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatDate(bill.period_start)} – {formatDate(bill.period_end)}</td>
                      <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatMoney(bill.net_payable, bill.currency)}</td>
                      <td className="px-4 py-3.5"><Badge tone={getBillStatusTone(bill.status)}>{bill.status}</Badge></td>
                      <td className="px-4 py-3.5 text-right"><Button variant="ghost" size="sm" onClick={() => setViewingBillId(bill.id)}>{t("subcontractors.detail.view")}</Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>
          )}
        </Panel>

        <div className="grid gap-5 sm:grid-cols-2">
          <Panel>
            <PanelHeader eyebrow={t("subcontractors.detail.financeEyebrow")} title={t("subcontractors.detail.advancesTitle")} action={canManagePayments ? <Button variant="secondary" size="sm" onClick={() => setAdvanceFormOpen(true)}>{t("subcontractors.detail.recordAdvance")}</Button> : null} />
            <div className="divide-y divide-[var(--color-border)]">
              {(advancesQuery.data ?? []).length === 0 ? <div className="p-4 text-[12.5px] text-[var(--color-text-secondary)]">{t("subcontractors.detail.noAdvances")}</div> : (advancesQuery.data ?? []).map((a) => (
                <div key={a.id} className="flex justify-between px-4 py-2.5 text-[12.5px]"><span className="text-[var(--color-text-secondary)]">{formatDate(a.advance_date)}</span><span className="font-mono font-semibold text-[var(--color-text-primary)]">{formatMoney(a.amount)}</span></div>
              ))}
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow={t("subcontractors.detail.financeEyebrow")} title={t("subcontractors.detail.paymentsTitle")} action={canManagePayments ? <Button variant="secondary" size="sm" onClick={() => setPaymentFormOpen(true)}>{t("subcontractors.detail.recordPayment")}</Button> : null} />
            <div className="divide-y divide-[var(--color-border)]">
              {(paymentsQuery.data ?? []).length === 0 ? <div className="p-4 text-[12.5px] text-[var(--color-text-secondary)]">{t("subcontractors.detail.noPayments")}</div> : (paymentsQuery.data ?? []).map((p) => (
                <div key={p.id} className="flex justify-between px-4 py-2.5 text-[12.5px]"><span className="text-[var(--color-text-secondary)]">{formatDate(p.payment_date)}</span><span className="font-mono font-semibold text-[var(--color-text-primary)]">{formatMoney(p.net_paid_amount)}</span></div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      {billFormOpen ? <BillGenerationForm agreement={agreement} onClose={() => setBillFormOpen(false)} /> : null}
      {advanceFormOpen ? <AdvanceForm agreementId={agreement.id} onClose={() => setAdvanceFormOpen(false)} /> : null}
      {paymentFormOpen ? <PaymentForm agreementId={agreement.id} subcontractor={subcontractor} onClose={() => setPaymentFormOpen(false)} /> : null}
      {viewingBillId ? <BillDetailDialog billId={viewingBillId} agreementId={agreement.id} canManage={canManage} onClose={() => setViewingBillId(null)} /> : null}
    </Modal>
  );
}

function BillGenerationForm({ agreement, onClose }: { agreement: SubcontractAgreementDetail; onClose: () => void }) {
  const { t } = useTranslation();
  const createBill = useCreateBill(agreement.id);
  const { showToast } = useToast();
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState(() => new Date().toISOString().slice(0, 10));
  const [percentages, setPercentages] = useState<Record<string, string>>({});
  const [salesTaxAuthority, setSalesTaxAuthority] = useState<"PRA" | "SRB" | "KPRA" | "BRA" | "ICT" | "">("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const measurements = agreement.items
      .filter((item) => percentages[item.id] !== undefined && percentages[item.id] !== "")
      .map((item) => ({ agreement_item_id: item.id, cumulative_percentage: Number(percentages[item.id]) }));

    createBill.mutate(
      { period_start: periodStart, period_end: periodEnd, measurements, sales_tax_authority: salesTaxAuthority || undefined },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: t("subcontractors.billForm.generatedToast") }); },
        onError: (mutationError) => setError(getApiErrorMessage(mutationError, t("subcontractors.billForm.generateError"))),
      },
    );
  }

  return (
    <Modal title={t("subcontractors.billForm.title")} description={t("subcontractors.billForm.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("subcontractors.billForm.periodStart")}>
            <input type="date" required className={inputClass} value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
          </Field>
          <Field label={t("subcontractors.billForm.periodEnd")}>
            <input type="date" required className={inputClass} value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
          </Field>
        </div>

        <div className="space-y-2">
          {agreement.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between gap-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5">
              <span className="text-[13px] font-medium text-[var(--color-text-primary)]">
                {item.description} <span className="text-[var(--color-text-muted)]">({item.unit})</span>
              </span>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="w-24 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-right text-[13px] outline-none focus:border-[var(--color-trace-gold-dark)]"
                placeholder="Cum. %"
                value={percentages[item.id] ?? ""}
                onChange={(e) => setPercentages((cur) => ({ ...cur, [item.id]: e.target.value }))}
              />
            </div>
          ))}
        </div>

        <Field label={t("subcontractors.billForm.salesTaxAuthority")}>
          <select className={inputClass} value={salesTaxAuthority} onChange={(e) => setSalesTaxAuthority(e.target.value as "PRA" | "SRB" | "KPRA" | "BRA" | "ICT" | "")}>
            <option value="">{t("subcontractors.billForm.noSalesTax")}</option>
            <option value="PRA">PRA</option>
            <option value="SRB">SRB</option>
            <option value="KPRA">KPRA</option>
            <option value="BRA">BRA</option>
            <option value="ICT">ICT</option>
          </select>
        </Field>

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createBill.isPending}>
            {t("subcontractors.advanceForm.cancel")}
          </Button>
          <Button type="submit" variant="primary" disabled={createBill.isPending || !periodStart || !periodEnd}>
            {createBill.isPending ? t("subcontractors.billForm.generating") : t("subcontractors.billForm.generate")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function AdvanceForm({ agreementId, onClose }: { agreementId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const createAdvance = useCreateAdvance(agreementId);
  const { showToast } = useToast();
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createAdvance.mutate({ amount: Number(amount), advance_date: date }, {
      onSuccess: () => { onClose(); showToast({ tone: "success", title: t("subcontractors.advanceForm.recordedToast") }); },
    });
  }

  return (
    <Modal title={t("subcontractors.advanceForm.title")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("subcontractors.advanceForm.amount")}><input type="number" min="0.01" step="any" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
        <Field label={t("subcontractors.advanceForm.date")}><input type="date" required className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createAdvance.isPending}>{t("subcontractors.advanceForm.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createAdvance.isPending || !amount}>{createAdvance.isPending ? t("subcontractors.advanceForm.saving") : t("subcontractors.advanceForm.submit")}</Button>
        </div>
      </form>
    </Modal>
  );
}

function PaymentForm({agreementId, subcontractor, onClose,  
}: {
  agreementId: string;
  subcontractor: { is_active_taxpayer: boolean };
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const createPayment = useCreatePayment(agreementId);
  const { showToast } = useToast();
  const [gross, setGross] = useState("");
  const [whtCategory, setWhtCategory] = useState<WHTCategory | "">("");
  const [advanceRecovered, setAdvanceRecovered] = useState("0");
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  const whtPreview = useWHTPreview(
    whtCategory || null,
    Number(gross) || 0,
    subcontractor.is_active_taxpayer,
    { enabled: Boolean(whtCategory) && Number(gross) > 0 },
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createPayment.mutate(
      { gross_amount: Number(gross), advance_recovered_amount: Number(advanceRecovered), wht_category: whtCategory || undefined, payment_date: paymentDate },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: t("subcontractors.paymentForm.recordedToast") }); },
        onError: (e) => setError(getApiErrorMessage(e, t("subcontractors.paymentForm.recordError"))),
      },
    );
  }

  return (
    <Modal title={t("subcontractors.paymentForm.title")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("subcontractors.paymentForm.gross")}><input type="number" min="0.01" step="any" required className={inputClass} value={gross} onChange={(e) => setGross(e.target.value)} /></Field>
        <Field label={t("subcontractors.paymentForm.advanceRecovered")}><input type="number" min="0" step="any" className={inputClass} value={advanceRecovered} onChange={(e) => setAdvanceRecovered(e.target.value)} /></Field>
        <Field label={t("subcontractors.paymentForm.wht")}>
          <select className={inputClass} value={whtCategory} onChange={(e) => setWhtCategory(e.target.value as WHTCategory | "")}>
            <option value="">{t("subcontractors.paymentForm.noWht")}</option>
            <option value="GOODS_SUPPLY">{t("subcontractors.paymentForm.goodsSupply")}</option>
            <option value="SERVICES">{t("subcontractors.paymentForm.services")}</option>
            <option value="CONTRACTS_EXECUTION">{t("subcontractors.paymentForm.contracts")}</option>
          </select>
        </Field>
        {whtCategory && whtPreview.data ? (
          <div className="rounded-[8px] border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] px-3 py-2.5 text-[12px] text-[var(--color-info)]">
            {t("subcontractors.paymentForm.whtPreview", {rate: Number(whtPreview.data.rate_percentage), filer: subcontractor.is_active_taxpayer
              ? t("subcontractors.paymentForm.filer")
              : t("subcontractors.paymentForm.nonFiler"),
               deducted: formatWHTMoney(whtPreview.data.deducted_amount), net: formatWHTMoney(whtPreview.data.net_after_wht),
            })}
          </div>
        ) : null}
        {whtCategory && whtPreview.isError ? (
          <div className="rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]">{getApiErrorMessage(whtPreview.error, t("subcontractors.paymentForm.whtError"))}</div>
        ) : null}
        <Field label={t("subcontractors.paymentForm.paymentDate")}><input type="date" required className={inputClass} value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} /></Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createPayment.isPending}>{t("subcontractors.paymentForm.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createPayment.isPending || !gross}>{createPayment.isPending ? t("subcontractors.paymentForm.saving") : t("subcontractors.paymentForm.submit")}</Button>
        </div>
      </form>
    </Modal>
  );
}

function BillDetailDialog({ billId, agreementId, canManage, onClose }: { billId: string; agreementId: string; canManage: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const issueBill = useIssueBill(agreementId);
  const cancelBill = useCancelBill(agreementId);
  const { showToast } = useToast();
  const [bill, setBill] = useState<SubcontractorBill | null>(null);

  useState(() => {
    subcontractorsApi.getBill(billId).then(setBill as any);
  });

  async function handleDownload(format: "pdf" | "xlsx") {
    const blob = format === "pdf" ? await subcontractorsApi.downloadBillPdf(billId) : await subcontractorsApi.downloadBillXlsx(billId);
    openBlobDownload(blob, `subcontractor-bill.${format}`);
  }

  if (!bill) return null;

  return (
    <Modal title={t("subcontractors.billDetail.title", { number: bill.bill_number })} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex justify-between"><Badge tone={getBillStatusTone(bill.status)}>{bill.status}</Badge>
          <div className="flex gap-2"><Button variant="ghost" size="sm" onClick={() => void handleDownload("pdf")}>{t("subcontractors.billDetail.pdf")}</Button><Button variant="ghost" size="sm" onClick={() => void handleDownload("xlsx")}>{t("subcontractors.billDetail.excel")}</Button></div>
        </div>
        <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[13px]">
          <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">{t("subcontractors.billDetail.grossThisPeriod")}</span><span className="font-semibold">{formatMoney(bill.gross_value_this_period, bill.currency)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">{t("subcontractors.billDetail.retention", { percent: Number(bill.retention_percentage) })} ({Number(bill.retention_percentage)}%)</span><span className="text-[var(--color-danger)]">- {formatMoney(bill.retention_this_period, bill.currency)}</span></div>
          <div className="mt-2 flex justify-between border-t border-[var(--color-border)] pt-2 text-[14px] font-bold text-[var(--color-text-primary)]"><span>Net payable (work value)</span><span>{formatMoney(bill.net_payable, bill.currency)}</span></div>
          {bill.sales_tax_authority ? (
           <div className="flex justify-between text-[13px] text-[var(--color-text-secondary)]">
             <span>+ Sales tax ({bill.sales_tax_authority}, {Number(bill.sales_tax_rate_percentage)}%)</span>
              <span>{formatMoney(bill.sales_tax_amount, bill.currency)}</span>
            </div>
            ) : null}
           {bill.sales_tax_authority ? (
            <div className="flex justify-between border-t border-[var(--color-border)] pt-2 text-[15px] font-bold text-[var(--color-trace-gold-dark)]">
             <span>Total amount due</span><span>{formatMoney(bill.total_amount_due, bill.currency)}</span>
             </div>
            ) : null}
        </div>
        {canManage && bill.status === "DRAFT" ? (
          <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
            <Button variant="danger" onClick={() => cancelBill.mutate({ billId: bill.id, version: bill.version }, { onSuccess: () => showToast({ tone: "success", title: t("subcontractors.billDetail.cancelledToast") }) })}>{t("subcontractors.billDetail.cancelBill")}</Button>
            <Button variant="primary" onClick={() => issueBill.mutate({ billId: bill.id, version: bill.version }, { onSuccess: () => showToast({ tone: "success", title: t("subcontractors.billDetail.issuedToast") }) })}>{t("subcontractors.billDetail.issueBill")}</Button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
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

export function AgreementDetailPanel({ agreement, canManage, canManagePayments, onClose }: {
  agreement: SubcontractAgreementDetail; canManage: boolean; canManagePayments: boolean; onClose: () => void;
}) {
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
    <Modal title={agreement.scope_description} description={`Contract value ${formatMoney(agreement.contract_value)}`} onClose={onClose} wide>
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <StatCard label="Billed to date" value={ledger ? formatMoney(ledger.total_billed, ledger.currency) : "…"} note="Issued bills, net payable" icon="budget" tone="gold" />
          <StatCard label="Outstanding payable" value={ledger ? formatMoney(ledger.outstanding_bill_balance, ledger.currency) : "…"} note="Billed minus paid" icon="alert" tone={Number(ledger?.outstanding_bill_balance ?? 0) > 0 ? "gold" : "green"} />
        </div>

        <Panel>
          <PanelHeader eyebrow="BILLING" title="Bills" description="Measured work billed against this agreement." action={canManage ? <Button variant="primary" size="sm" onClick={() => setBillFormOpen(true)}>Generate bill</Button> : null} />
          {(billsQuery.data ?? []).length === 0 ? (
            <EmptyState icon="budget" title="No bills yet" description="Generate a bill once measurable progress has been made." />
          ) : (
            <TableShell>
              <table className="w-full min-w-[560px] text-left">
                <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Bill</th><th className="px-4 py-3">Period</th><th className="px-4 py-3 text-right">Net payable</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
                <tbody>
                  {(billsQuery.data ?? []).map((bill) => (
                    <tr key={bill.id} className="border-t border-[var(--color-border)]">
                      <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">#{bill.bill_number}</td>
                      <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatDate(bill.period_start)} – {formatDate(bill.period_end)}</td>
                      <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatMoney(bill.net_payable, bill.currency)}</td>
                      <td className="px-4 py-3.5"><Badge tone={getBillStatusTone(bill.status)}>{bill.status}</Badge></td>
                      <td className="px-4 py-3.5 text-right"><Button variant="ghost" size="sm" onClick={() => setViewingBillId(bill.id)}>View</Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>
          )}
        </Panel>

        <div className="grid gap-5 sm:grid-cols-2">
          <Panel>
            <PanelHeader eyebrow="FINANCE" title="Advances" action={canManagePayments ? <Button variant="secondary" size="sm" onClick={() => setAdvanceFormOpen(true)}>Record advance</Button> : null} />
            <div className="divide-y divide-[var(--color-border)]">
              {(advancesQuery.data ?? []).length === 0 ? <div className="p-4 text-[12.5px] text-[var(--color-text-secondary)]">No advances recorded.</div> : (advancesQuery.data ?? []).map((a) => (
                <div key={a.id} className="flex justify-between px-4 py-2.5 text-[12.5px]"><span className="text-[var(--color-text-secondary)]">{formatDate(a.advance_date)}</span><span className="font-mono font-semibold text-[var(--color-text-primary)]">{formatMoney(a.amount)}</span></div>
              ))}
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="FINANCE" title="Payments" action={canManagePayments ? <Button variant="secondary" size="sm" onClick={() => setPaymentFormOpen(true)}>Record payment</Button> : null} />
            <div className="divide-y divide-[var(--color-border)]">
              {(paymentsQuery.data ?? []).length === 0 ? <div className="p-4 text-[12.5px] text-[var(--color-text-secondary)]">No payments recorded.</div> : (paymentsQuery.data ?? []).map((p) => (
                <div key={p.id} className="flex justify-between px-4 py-2.5 text-[12.5px]"><span className="text-[var(--color-text-secondary)]">{formatDate(p.payment_date)}</span><span className="font-mono font-semibold text-[var(--color-text-primary)]">{formatMoney(p.net_paid_amount)}</span></div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      {billFormOpen ? <BillGenerationForm agreement={agreement} onClose={() => setBillFormOpen(false)} /> : null}
      {advanceFormOpen ? <AdvanceForm agreementId={agreement.id} onClose={() => setAdvanceFormOpen(false)} /> : null}
      {paymentFormOpen ? <PaymentForm agreementId={agreement.id} onClose={() => setPaymentFormOpen(false)} /> : null}
      {viewingBillId ? <BillDetailDialog billId={viewingBillId} agreementId={agreement.id} canManage={canManage} onClose={() => setViewingBillId(null)} /> : null}
    </Modal>
  );
}

function BillGenerationForm({ agreement, onClose }: { agreement: SubcontractAgreementDetail; onClose: () => void }) {
  const createBill = useCreateBill(agreement.id);
  const { showToast } = useToast();
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState(() => new Date().toISOString().slice(0, 10));
  const [percentages, setPercentages] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const measurements = agreement.items
      .filter((item) => percentages[item.id] !== undefined && percentages[item.id] !== "")
      .map((item) => ({ agreement_item_id: item.id, cumulative_percentage: Number(percentages[item.id]) }));

    createBill.mutate(
      { period_start: periodStart, period_end: periodEnd, measurements },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "Bill generated as draft" }); },
        onError: (mutationError) => setError(getApiErrorMessage(mutationError, "Couldn't generate this bill.")),
      },
    );
  }

  return (
    <Modal title="Generate bill" description="Enter cumulative % complete for each item as measured today." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Period start"><input type="date" required className={inputClass} value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} /></Field>
          <Field label="Period end"><input type="date" required className={inputClass} value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} /></Field>
        </div>

        <div className="space-y-2">
          {agreement.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between gap-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5">
              <span className="text-[13px] font-medium text-[var(--color-text-primary)]">{item.description} <span className="text-[var(--color-text-muted)]">({item.unit})</span></span>
              <input type="number" min="0" max="100" step="0.1" className="w-24 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-right text-[13px] outline-none focus:border-[var(--color-trace-gold-dark)]" placeholder="Cum. %" value={percentages[item.id] ?? ""} onChange={(e) => setPercentages((cur) => ({ ...cur, [item.id]: e.target.value }))} />
            </div>
          ))}
        </div>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createBill.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createBill.isPending || !periodStart || !periodEnd}>{createBill.isPending ? "Generating…" : "Generate bill"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function AdvanceForm({ agreementId, onClose }: { agreementId: string; onClose: () => void }) {
  const createAdvance = useCreateAdvance(agreementId);
  const { showToast } = useToast();
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createAdvance.mutate({ amount: Number(amount), advance_date: date }, {
      onSuccess: () => { onClose(); showToast({ tone: "success", title: "Advance recorded" }); },
    });
  }

  return (
    <Modal title="Record advance" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Amount (PKR)"><input type="number" min="0.01" step="any" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
        <Field label="Date"><input type="date" required className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createAdvance.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createAdvance.isPending || !amount}>{createAdvance.isPending ? "Saving…" : "Record advance"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function PaymentForm({ agreementId, onClose }: { agreementId: string; onClose: () => void }) {
  const createPayment = useCreatePayment(agreementId);
  const { showToast } = useToast();
  const [gross, setGross] = useState("");
  const [advanceRecovered, setAdvanceRecovered] = useState("0");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createPayment.mutate({ gross_amount: Number(gross), advance_recovered_amount: Number(advanceRecovered), payment_date: date }, {
      onSuccess: () => { onClose(); showToast({ tone: "success", title: "Payment recorded" }); },
    });
  }

  return (
    <Modal title="Record payment" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Gross amount (PKR)"><input type="number" min="0.01" step="any" required className={inputClass} value={gross} onChange={(e) => setGross(e.target.value)} /></Field>
        <Field label="Advance recovered (PKR)"><input type="number" min="0" step="any" className={inputClass} value={advanceRecovered} onChange={(e) => setAdvanceRecovered(e.target.value)} /></Field>
        <Field label="Payment date"><input type="date" required className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createPayment.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createPayment.isPending || !gross}>{createPayment.isPending ? "Saving…" : "Record payment"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function BillDetailDialog({ billId, agreementId, canManage, onClose }: { billId: string; agreementId: string; canManage: boolean; onClose: () => void }) {
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
    <Modal title={`Bill #${bill.bill_number}`} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex justify-between"><Badge tone={getBillStatusTone(bill.status)}>{bill.status}</Badge>
          <div className="flex gap-2"><Button variant="ghost" size="sm" onClick={() => void handleDownload("pdf")}>PDF</Button><Button variant="ghost" size="sm" onClick={() => void handleDownload("xlsx")}>Excel</Button></div>
        </div>
        <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[13px]">
          <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Gross this period</span><span className="font-semibold">{formatMoney(bill.gross_value_this_period, bill.currency)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Retention ({Number(bill.retention_percentage)}%)</span><span className="text-[var(--color-danger)]">- {formatMoney(bill.retention_this_period, bill.currency)}</span></div>
          <div className="mt-2 flex justify-between border-t border-[var(--color-border)] pt-2 text-[14px] font-bold"><span>Net payable</span><span>{formatMoney(bill.net_payable, bill.currency)}</span></div>
        </div>
        {canManage && bill.status === "DRAFT" ? (
          <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
            <Button variant="danger" onClick={() => cancelBill.mutate({ billId: bill.id, version: bill.version }, { onSuccess: () => showToast({ tone: "success", title: "Bill cancelled" }) })}>Cancel bill</Button>
            <Button variant="primary" onClick={() => issueBill.mutate({ billId: bill.id, version: bill.version }, { onSuccess: () => showToast({ tone: "success", title: "Bill issued" }) })}>Issue bill</Button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
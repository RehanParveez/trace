import { useState } from "react";
import type { FormEvent } from "react";
import {Badge, Button, EmptyState, Field, inputClass, Modal, Panel, PanelHeader, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import {useCreateLabourAdvance, useCreateLabourPayment, useLabourAdvances, useLabourPayments, useLabourSources,
} from "../hooks";
import { formatLabourDate, formatLabourMoney } from "../utils/labour.utils";
import { useTranslation } from "react-i18next";

export function LabourFinancePanel({ projectId, canManagePayments }: { projectId: string; canManagePayments: boolean }) {
  const { t } = useTranslation();
  const sourcesQuery = useLabourSources();
  const advancesQuery = useLabourAdvances(projectId);
  const paymentsQuery = useLabourPayments(projectId);
  const [advanceOpen, setAdvanceOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);

  const sources = sourcesQuery.data ?? [];
  const sourceNameById = new Map(sources.map((s) => [s.id, s.name]));

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          eyebrow={t("labour.finance.eyebrow")}
          title={t("labour.finance.advancesTitle")}
          description={t("labour.finance.advancesDescription")}
          action={canManagePayments ? <Button variant="primary" size="sm" onClick={() => setAdvanceOpen(true)}> {t("labour.finance.recordAdvance")}</Button> : null}
        />
        {(advancesQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget" title={t("labour.finance.noAdvancesTitle")} description={t("labour.finance.noAdvancesDescription")} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[500px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("labour.finance.source")}</th><th className="px-4 py-3">{t("labour.finance.date")}</th><th className="px-4 py-3 text-right">{t("labour.finance.amount")}</th></tr></thead>
              <tbody>
                {(advancesQuery.data ?? []).map((advance) => (
                  <tr key={advance.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13px] font-medium text-[var(--color-text-primary)]">{sourceNameById.get(advance.source_id) ?? "—"}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatLabourDate(advance.advance_date)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatLabourMoney(advance.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      <Panel>
        <PanelHeader
          eyebrow={t("labour.finance.eyebrow")}
          title={t("labour.finance.paymentsTitle")}
          description={t("labour.finance.paymentsDescription")}
          action={canManagePayments ? <Button variant="primary" size="sm" onClick={() => setPaymentOpen(true)}>{t("labour.finance.recordPayment")}</Button> : null}
        />
        {(paymentsQuery.data ?? []).length === 0 ? (
          <EmptyState icon="budget"  title={t("labour.finance.noPaymentsTitle")} description={t("labour.finance.noPaymentsDescription")} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[600px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("labour.finance.source")}</th><th className="px-4 py-3">{t("labour.finance.period")}</th><th className="px-4 py-3 text-right">{t("labour.finance.gross")}</th><th className="px-4 py-3 text-right">{t("labour.finance.netPaid")}</th></tr></thead>
              <tbody>
                {(paymentsQuery.data ?? []).map((payment) => (
                  <tr key={payment.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13px] font-medium text-[var(--color-text-primary)]">{sourceNameById.get(payment.source_id) ?? "—"}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatLabourDate(payment.period_start)} – {formatLabourDate(payment.period_end)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{formatLabourMoney(payment.gross_wage_amount)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatLabourMoney(payment.net_paid_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      {advanceOpen ? <AdvanceDialog projectId={projectId} sources={sources} onClose={() => setAdvanceOpen(false)} /> : null}
      {paymentOpen ? <PaymentDialog projectId={projectId} sources={sources} onClose={() => setPaymentOpen(false)} /> : null}
    </div>
  );
}

function AdvanceDialog({ projectId, sources, onClose }: { projectId: string; sources: { id: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const createAdvance = useCreateLabourAdvance(projectId);
  const { showToast } = useToast();
  const [sourceId, setSourceId] = useState(sources[0]?.id ?? "");
  const [amount, setAmount] = useState("");
  const [advanceDate, setAdvanceDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createAdvance.mutate({ source_id: sourceId, amount: Number(amount), advance_date: advanceDate }, {
      onSuccess: () => {onClose(); showToast({tone: "success", title: t("labour.finance.advanceRecorded"),
  });
},
      onError: (mutationError) => setError(
       getApiErrorMessage(mutationError,
         t("labour.finance.advanceError"),),
      ),
    });
  }

  return (
    <Modal title={t("labour.finance.recordAdvanceTitle")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("labour.finance.source")}><select className={inputClass} value={sourceId} onChange={(e) => setSourceId(e.target.value)}>{sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></Field>
        <Field label={t("labour.finance.amountPkr")}><input type="number" min="0.01" step="any" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
        <Field label="Date"><input type="date" required className={inputClass} value={advanceDate} onChange={(e) => setAdvanceDate(e.target.value)} /></Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createAdvance.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createAdvance.isPending || !sourceId || !amount}>{createAdvance.isPending ? t("common.saving") : t("labour.finance.recordAdvance")}</Button>
        </div>
      </form>
    </Modal>
  );
}

function PaymentDialog({ projectId, sources, onClose }: { projectId: string; sources: { id: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const createPayment = useCreateLabourPayment(projectId);
  const { showToast } = useToast();
  const [sourceId, setSourceId] = useState(sources[0]?.id ?? "");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState(() => new Date().toISOString().slice(0, 10));
  const [gross, setGross] = useState("");
  const [advanceRecovered, setAdvanceRecovered] = useState("0");
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createPayment.mutate(
      { source_id: sourceId, period_start: periodStart, period_end: periodEnd, gross_wage_amount: Number(gross), advance_recovered_amount: Number(advanceRecovered), payment_date: paymentDate },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: t("labour.finance.paymentRecorded"), }); },
        onError: (mutationError) => setError(getApiErrorMessage(mutationError, t("labour.finance.paymentError"),)),
      },
    );
  }

  return (
    <Modal title={t("labour.finance.recordPaymentTitle")} description={t("labour.finance.netPaymentDescription")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("labour.finance.source")}><select className={inputClass} value={sourceId} onChange={(e) => setSourceId(e.target.value)}>{sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("labour.finance.periodStart")}><input type="date" required className={inputClass} value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} /></Field>
          <Field label={t("labour.finance.periodEnd")}><input type="date" required className={inputClass} value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} /></Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("labour.finance.grossWagesPkr")}><input type="number" min="0" step="any" required className={inputClass} value={gross} onChange={(e) => setGross(e.target.value)} /></Field>
          <Field label={t("labour.finance.advanceRecoveredPkr")}><input type="number" min="0" step="any" className={inputClass} value={advanceRecovered} onChange={(e) => setAdvanceRecovered(e.target.value)} /></Field>
        </div>
        <Field label={t("labour.finance.paymentDate")}><input type="date" required className={inputClass} value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} /></Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createPayment.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createPayment.isPending || !sourceId || !periodStart || !gross}>{createPayment.isPending ? t("common.saving") : t("labour.finance.recordPayment")}</Button>
        </div>
      </form>
    </Modal>
  );
}
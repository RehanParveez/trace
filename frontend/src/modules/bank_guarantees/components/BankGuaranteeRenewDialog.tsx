import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useRenewBankGuarantee } from "../hooks/index.ts";
import type { BankGuarantee } from "../types/bank-guarantee.types";
import { useTranslation } from "react-i18next";

export function BankGuaranteeRenewDialog({ projectId, guarantee, onClose }: { projectId: string; guarantee: BankGuarantee; onClose: () => void }) {
  const { t } = useTranslation();
  const renew = useRenewBankGuarantee(projectId);
  const { showToast } = useToast();
  const [guaranteeNumber, setGuaranteeNumber] = useState("");
  const [issueDate, setIssueDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [expiryDate, setExpiryDate] = useState("");
  const [amount, setAmount] = useState(String(guarantee.amount));
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    renew.mutate(
      { id: guarantee.id, payload: { guarantee_number: guaranteeNumber.trim(), issue_date: issueDate, expiry_date: expiryDate, amount: Number(amount) } },
      { onSuccess: () => { onClose(); showToast({ tone: "success", title: t("bankGuarantees.renew.successToast") }); }, onError: (e) => setError(getApiErrorMessage(e, t("bankGuarantees.renew.errorFallback"))) },
    );
  }

  return (
    <Modal title={t("bankGuarantees.renew.title", { number: guarantee.guarantee_number })} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("bankGuarantees.renew.newNumber")}><input required className={inputClass} value={guaranteeNumber} onChange={(e) => setGuaranteeNumber(e.target.value)} /></Field>
        <Field label={t("bankGuarantees.renew.amount")}><input type="number" min="0.01" step="any" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("bankGuarantees.renew.newIssueDate")}><input type="date" required className={inputClass} value={issueDate} onChange={(e) => setIssueDate(e.target.value)} /></Field>
          <Field label={t("bankGuarantees.renew.newExpiryDate")}><input type="date" required className={inputClass} value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} /></Field>
        </div>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={renew.isPending}>{t("bankGuarantees.renew.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={renew.isPending || !guaranteeNumber.trim() || !expiryDate}>{renew.isPending ? t("bankGuarantees.renew.renewing") : t("bankGuarantees.renew.submit")}</Button>
        </div>
      </form>
    </Modal>
  );
}
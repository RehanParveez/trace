import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useBOQVersions } from "../../drawings_boq";
import { useAgreements } from "../../subcontractors";
import { useCreateBankGuarantee } from "../hooks/index.ts";
import type { BankGuaranteeHolderType } from "../types/bank-guarantee.types";
import { useTranslation } from "react-i18next";
import { todayLocal } from "../../../shared/utils/date";

export function BankGuaranteeForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const boqVersionsQuery = useBOQVersions(projectId);
  const agreementsQuery = useAgreements(projectId);
  const createGuarantee = useCreateBankGuarantee(projectId);
  const { showToast } = useToast();

  const [holderType, setHolderType] = useState<BankGuaranteeHolderType>("CLIENT");
  const [boqVersionId, setBoqVersionId] = useState("");
  const [agreementId, setAgreementId] = useState("");
  const [guaranteeNumber, setGuaranteeNumber] = useState("");
  const [issuingBank, setIssuingBank] = useState("");
  const [amount, setAmount] = useState("");
  const [issueDate, setIssueDate] = useState(() => todayLocal()
);
  const [expiryDate, setExpiryDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createGuarantee.mutate(
      {
        holder_type: holderType,
        boq_version_id: holderType === "CLIENT" ? boqVersionId : null,
        agreement_id: holderType === "SUBCONTRACTOR" ? agreementId : null,
        guarantee_number: guaranteeNumber.trim(), issuing_bank: issuingBank.trim(),
        amount: Number(amount), issue_date: issueDate, expiry_date: expiryDate,
      },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: t("bankGuarantees.form.savedToast") }); },
        onError: (e) => setError(getApiErrorMessage(e, t("bankGuarantees.form.saveErrorFallback"))),
      },
    );
  }

  return (
    <Modal title={t("bankGuarantees.form.title")} description={t("bankGuarantees.form.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="flex gap-2">
          <button type="button" onClick={() => setHolderType("CLIENT")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${holderType === "CLIENT" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>{t("bankGuarantees.form.holderClient")}</button>
          <button type="button" onClick={() => setHolderType("SUBCONTRACTOR")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${holderType === "SUBCONTRACTOR" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>{t("bankGuarantees.form.holderSubcontractor")}</button>
        </div>

        {holderType === "CLIENT" ? (
          <Field label={t("bankGuarantees.form.boqVersion")}>
            <select required className={inputClass} value={boqVersionId} onChange={(e) => setBoqVersionId(e.target.value)}>
              <option value="">{t("bankGuarantees.form.selectBoq")}</option>
              {(boqVersionsQuery.data ?? []).map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
            </select>
          </Field>
        ) : (
          <Field label={t("bankGuarantees.form.agreement")}>
            <select required className={inputClass} value={agreementId} onChange={(e) => setAgreementId(e.target.value)}>
              <option value="">{t("bankGuarantees.form.selectAgreement")}</option>
              {(agreementsQuery.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.scope_description}</option>)}
            </select>
          </Field>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("bankGuarantees.form.guaranteeNumber")}><input required className={inputClass} value={guaranteeNumber} onChange={(e) => setGuaranteeNumber(e.target.value)} /></Field>
          <Field label={t("bankGuarantees.form.issuingBank")}><input required className={inputClass} value={issuingBank} onChange={(e) => setIssuingBank(e.target.value)} placeholder={t("bankGuarantees.form.issuingBankPlaceholder")} /></Field>
        </div>

        <Field label={t("bankGuarantees.form.amount")}><input type="number" min="0.01" step="any" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("bankGuarantees.form.issueDate")}><input type="date" required className={inputClass} value={issueDate} onChange={(e) => setIssueDate(e.target.value)} /></Field>
          <Field label={t("bankGuarantees.form.expiryDate")}><input type="date" required className={inputClass} value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} /></Field>
        </div>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createGuarantee.isPending}>{t("bankGuarantees.form.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createGuarantee.isPending || !guaranteeNumber.trim() || !issuingBank.trim() || !amount || !expiryDate}>{createGuarantee.isPending ? t("bankGuarantees.form.saving") : t("bankGuarantees.form.save")}</Button>
        </div>
      </form>
    </Modal>
  );
}
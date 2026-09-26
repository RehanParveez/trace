import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useBOQVersions } from "../../drawings_boq";
import { useAgreements } from "../../subcontractors";
import { useCreateRetentionRelease } from "../hooks";
import type { RetentionHolderType } from "../types/retention.types";
import { useTranslation } from "react-i18next";

export function RetentionReleaseForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const boqVersionsQuery = useBOQVersions(projectId);
  const agreementsQuery = useAgreements(projectId);
  const createRelease = useCreateRetentionRelease();
  const { showToast } = useToast();

  const [holderType, setHolderType] = useState<RetentionHolderType>("CLIENT");
  const [boqVersionId, setBoqVersionId] = useState("");
  const [agreementId, setAgreementId] = useState("");
  const [amount, setAmount] = useState("");
  const [releaseDate, setReleaseDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isFinalRelease, setIsFinalRelease] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createRelease.mutate(
      {
        holder_type: holderType, project_id: projectId,
        boq_version_id: holderType === "CLIENT" ? boqVersionId : null,
        agreement_id: holderType === "SUBCONTRACTOR" ? agreementId : null,
        amount: Number(amount), is_final_release: isFinalRelease, release_date: releaseDate, notes: notes.trim() || null,
      },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: t("retention.release.successToast") }); },
        onError: (e) => setError(getApiErrorMessage(e, t("retention.release.errorFallback"))),
      },
    );
  }

  return (
    <Modal title={t("retention.release.title")} description={t("retention.release.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="flex gap-2">
          <button type="button" onClick={() => setHolderType("CLIENT")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${holderType === "CLIENT" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>{t("retention.release.clientHeld")}</button>
          <button type="button" onClick={() => setHolderType("SUBCONTRACTOR")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${holderType === "SUBCONTRACTOR" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>{t("retention.release.subcontractorHeld")}</button>
        </div>

        {holderType === "CLIENT" ? (
          <Field label={t("retention.release.boqVersion")}>
            <select required className={inputClass} value={boqVersionId} onChange={(e) => setBoqVersionId(e.target.value)}>
              <option value="">{t("retention.release.selectBoq")}</option>
              {(boqVersionsQuery.data ?? []).map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
            </select>
          </Field>
        ) : (
          <Field label={t("retention.release.agreement")}>
            <select required className={inputClass} value={agreementId} onChange={(e) => setAgreementId(e.target.value)}>
              <option value="">{t("retention.release.selectAgreement")}</option>
              {(agreementsQuery.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.scope_description}</option>)}
            </select>
          </Field>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("retention.release.amount")}><input type="number" min="0.01" step="any" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
          <Field label={t("retention.release.releaseDate")}><input type="date" required className={inputClass} value={releaseDate} onChange={(e) => setReleaseDate(e.target.value)} /></Field>
        </div>
        <Field label={t("retention.release.notes")}><textarea className={`${inputClass} resize-y`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>

        <label className="flex items-start gap-2.5 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
          <input type="checkbox" checked={isFinalRelease} onChange={(e) => setIsFinalRelease(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[var(--color-trace-gold)]" />
          <span className="text-[12.5px] text-[var(--color-text-primary)]">
            This is the <strong>final</strong> retention release
            <span className="mt-1 block text-[11.5px] text-[var(--color-text-secondary)]">
              {holderType === "CLIENT"
                ? "Requires every punch list for this project to be closed."
                : "Requires every punch list item assigned to this subcontractor to be resolved or waived."}
            </span>
          </span>
        </label>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createRelease.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createRelease.isPending || !amount || (holderType === "CLIENT" ? !boqVersionId : !agreementId)}>{createRelease.isPending ? t("common.saving") : t("retention.release.submit")}</Button>
        </div>
      </form>
    </Modal>
  );
}

import { useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, inputClass, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useBOQVersions } from "../../drawings_boq";
import { useCreateRunningBill } from "../hooks";
import { useTranslation } from "react-i18next";
import type { SalesTaxAuthority } from "../../salex_tax";
import { formatSalesTaxAuthority, formatSalesTaxMoney } from "../../salex_tax";

interface RunningBillFormProps {
  projectId: string;
  onClose: () => void;
}

export function RunningBillForm({ projectId, onClose }: RunningBillFormProps) {
  const { t } = useTranslation();
  const boqVersionsQuery = useBOQVersions(projectId);
  const createBill = useCreateRunningBill();
  const { showToast } = useToast();

  const boqVersions = boqVersionsQuery.data ?? [];

  const [boqVersionId, setBoqVersionId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState(() =>
    new Date().toISOString().slice(0, 10),
  );
  const [salesTaxAuthority, setSalesTaxAuthority] = useState<SalesTaxAuthority | "">("");
  const [retentionPercentage, setRetentionPercentage] = useState("10");
  const [retentionCapPercentage, setRetentionCapPercentage] = useState("");
  const [advanceRecovery, setAdvanceRecovery] = useState("0");
  const [otherDeductions, setOtherDeductions] = useState("0");
  const [otherDeductionsNote, setOtherDeductionsNote] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const activeBoqVersionId = boqVersionId || boqVersions[0]?.id || "";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createBill.mutate(
      {
        project_id: projectId,
        boq_version_id: activeBoqVersionId,
        period_start: periodStart,
        period_end: periodEnd,
        retention_percentage: Number(retentionPercentage),
        retention_cap_percentage:
          retentionCapPercentage === ""
            ? null
            : Number(retentionCapPercentage),
        sales_tax_authority: salesTaxAuthority || undefined,
        advance_recovery_amount: Number(advanceRecovery),
        other_deductions_amount: Number(otherDeductions),
        other_deductions_note: otherDeductionsNote.trim() || null,
        notes: notes.trim() || null,
      },
      {
        onSuccess: () => {
          onClose();
          showToast({
            tone: "success",
            title: t("runningBills.form.createdDraftToast"),
          });
        },
        onError: (mutationError) =>
          setError(
            getApiErrorMessage(
              mutationError,
              t("runningBills.form.createErrorFallback"),
            ),
          ),
      },
    );
  }

  return (
    <Modal
      title={t("runningBills.form.modalTitle")}
      description={t("runningBills.form.modalDescription")}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("runningBills.form.boqVersion")}>
          <select
            className={inputClass}
            value={activeBoqVersionId}
            onChange={(e) => setBoqVersionId(e.target.value)}
          >
            {boqVersions.length === 0 ? (
              <option value="">No BOQ versions available</option>
            ) : null}
            {boqVersions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.label}
              </option>
            ))}
          </select>
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
           <Field label={t("runningBills.form.periodStart")}>
            <input
              type="date"
              required
              className={inputClass}
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
            />
          </Field>
          <Field label={t("runningBills.form.periodEnd")}>
            <input
              type="date"
              required
              className={inputClass}
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("runningBills.form.retentionLabel")} hint={t("runningBills.form.retentionHint")}>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              required
              className={inputClass}
              value={retentionPercentage}
              onChange={(e) => setRetentionPercentage(e.target.value)}
            />
          </Field>
          <Field
            label={t("runningBills.form.retentionCapLabel")}
            hint={t("runningBills.form.retentionCapHint")}
          >
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              className={inputClass}
              value={retentionCapPercentage}
              onChange={(e) => setRetentionCapPercentage(e.target.value)}
              placeholder="No cap"
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("runningBills.form.advanceRecoveryLabel")}>
            <input
              type="number"
              step="any"
              min="0"
              className={inputClass}
              value={advanceRecovery}
              onChange={(e) => setAdvanceRecovery(e.target.value)}
            />
          </Field>
          <Field label={t("runningBills.form.otherDeductionsLabel")}>
            <input
              type="number"
              step="any"
              min="0"
              className={inputClass}
              value={otherDeductions}
              onChange={(e) => setOtherDeductions(e.target.value)}
            />
          </Field>
        </div>

        <Field label="Provincial sales tax on services (optional)">
          <select
            className={inputClass}
            value={salesTaxAuthority}
            onChange={(e) =>
              setSalesTaxAuthority(e.target.value as SalesTaxAuthority | "")
            }
          >
            <option value="">Not applicable</option>
            <option value="PRA">Punjab (PRA)</option>
            <option value="SRB">Sindh (SRB)</option>
            <option value="KPRA">Khyber Pakhtunkhwa (KPRA)</option>
            <option value="BRA">Balochistan (BRA)</option>
            <option value="ICT">Islamabad Capital Territory (ICT)</option>
          </select>
        </Field>

        {salesTaxAuthority ? (
          <RunningBillSalesTaxPreview authority={salesTaxAuthority} />
        ) : null}

        <Field label={t("runningBills.form.notesLabel")}>
          <textarea
            className={`${inputClass} resize-y`}
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </Field>

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={createBill.isPending}
          >
            {t("runningBills.form.cancel")}
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={
              createBill.isPending ||
              !activeBoqVersionId ||
              !periodStart ||
              !periodEnd
            }
          >
            {createBill.isPending ? t("runningBills.form.generating") : t("runningBills.form.generateDraft")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RunningBillSalesTaxPreview({
  authority,
}: {
  authority: SalesTaxAuthority;
}) {
  return (
    <div className="rounded-[8px] border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] px-3 py-2.5 text-[12px] text-[var(--color-info)]">
      Sales tax for {formatSalesTaxAuthority(authority)} will be calculated on
      this period's actual gross value once the draft is generated, and
      finalized against the rate active when the bill is issued.
    </div>
  );
}
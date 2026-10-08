import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button, Field, inputClass, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { WORK_ITEM_SUGGESTIONS } from "../../utils/drawings-boq.utils";
import { useCreateOverride } from "../hooks";
import { emptyToNull, parseNonNegative } from "../utils/pricing.utils";
import { FormError } from "./FormError";

interface OverrideFormDialogProps {
  projectId: string;
  defaults?: { work_item_code?: string | null; unit?: string | null; rate?: number | string | null };
  onClose: () => void;
}

export function OverrideFormDialog({ projectId, defaults, onClose }: OverrideFormDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const createOverride = useCreateOverride(projectId);

  const [code, setCode] = useState(defaults?.work_item_code ?? "");
  const [unit, setUnit] = useState(defaults?.unit ?? "");
  const [rate, setRate] = useState(defaults?.rate !== null && defaults?.rate !== undefined ? String(Number(defaults.rate)) : "");
  const [reason, setReason] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [error, setError] = useState<string | null>(null);

  const rateValue = parseNonNegative(rate);
  const rangeInvalid = Boolean(effectiveFrom && effectiveTo && effectiveTo < effectiveFrom);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (rateValue === null || rangeInvalid) return;
    createOverride.mutate(
      {
        work_item_code: code.trim().toUpperCase(),
        unit: unit.trim(),
        rate: rateValue,
        reason: reason.trim(),
        effective_from: emptyToNull(effectiveFrom),
        effective_to: emptyToNull(effectiveTo),
      },
      {
        onSuccess: () => {
          showToast({
            tone: "success",
            title: t("pricing.override.createdToast", "Rate override added"),
            description: t("pricing.override.createdDesc", "Run “Price BOQ” again to apply it to the lines."),
          });
          onClose();
        },
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.override.createError", "Couldn't add this override."))),
      },
    );
  }

  return (
    <Modal
      title={t("pricing.override.title", "Override a rate for this project")}
      description={t(
        "pricing.override.desc",
        "A project override beats every rate book when this project is priced. It needs a reason, and it can be revoked but never edited, so the history stays honest.",
      )}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("pricing.override.code", "Work item code")}>
            <input required list="pricing-override-codes" className={inputClass} value={code} maxLength={50} onChange={(e) => setCode(e.target.value)} />
            <datalist id="pricing-override-codes">
              {WORK_ITEM_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
            </datalist>
          </Field>
          <Field label={t("pricing.override.unit", "Unit")}>
            <input required className={inputClass} value={unit} maxLength={20} onChange={(e) => setUnit(e.target.value)} />
          </Field>
          <Field label={t("pricing.override.rate", "Rate")}>
            <input required type="number" min="0" step="0.01" className={inputClass} value={rate} onChange={(e) => setRate(e.target.value)} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("pricing.override.from", "Effective from (optional)")}>
            <input type="date" className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </Field>
          <Field
            label={t("pricing.override.to", "Effective to (optional)")}
            error={rangeInvalid ? t("pricing.form.rangeInvalid", "The end date is before the start date.") : undefined}
          >
            <input type="date" className={inputClass} value={effectiveTo} min={effectiveFrom || undefined} onChange={(e) => setEffectiveTo(e.target.value)} />
          </Field>
        </div>
        <Field label={t("pricing.override.reason", "Reason")} hint={t("pricing.override.reasonHint", "e.g. Negotiated supplier quote, contract rate.")}>
          <textarea required className={`${inputClass} min-h-[80px]`} value={reason} maxLength={1000} onChange={(e) => setReason(e.target.value)} />
        </Field>

        <FormError message={error} />

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createOverride.isPending}>{t("common.cancel", "Cancel")}</Button>
          <Button
            type="submit"
            variant="primary"
            disabled={createOverride.isPending || !code.trim() || !unit.trim() || rateValue === null || !reason.trim() || rangeInvalid}
          >
            {createOverride.isPending ? t("common.saving", "Saving…") : t("pricing.override.save", "Add override")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

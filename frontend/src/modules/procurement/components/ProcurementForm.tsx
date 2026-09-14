import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { useCreateProcurementRequest } from "../hooks";
import { useTranslation } from "react-i18next";

interface ProcurementFormProps {
  projectId: string;
  onClose: () => void;
}

export function ProcurementForm({ projectId, onClose }: ProcurementFormProps) {
  const { t } = useTranslation();
  const createRequest = useCreateProcurementRequest();
  const { showToast } = useToast();

  const [materialName, setMaterialName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [estimatedAmount, setEstimatedAmount] = useState("");
  const [neededByDate, setNeededByDate] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createRequest.mutate(
      {
        project_id: projectId,
        material_name: materialName.trim(),
        quantity: Number(quantity),
        unit: unit.trim(),
        estimated_amount: estimatedAmount === "" ? null : Number(estimatedAmount),
        needed_by_date: neededByDate || null,
        notes: notes.trim() || null,
      },
      {
        onSuccess: () => {
          onClose();
          showToast({ tone: "success", title: t("procurement.form.submitted") });
        },
        onError: () => setError(t("procurement.form.createError")),
      },
    );
  }

  return (
    <Modal title={t("procurement.form.title")} description={t("procurement.form.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("procurement.form.material")}>
          <input required className={inputClass} value={materialName} onChange={(e) => setMaterialName(e.target.value)} placeholder={t("procurement.form.materialPlaceholder")} />
        </Field>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("procurement.form.quantity")}>
            <input type="number" step="any" min="0.01" required className={inputClass} value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          <Field label={t("procurement.form.unit")}>
            <input required className={inputClass} value={unit} onChange={(e) => setUnit(e.target.value)} placeholder={t("procurement.form.unitPlaceholder")} />
          </Field>
           <Field label={t("procurement.form.estimatedCost")}>
            <input type="number" step="any" min="0" className={inputClass} value={estimatedAmount} onChange={(e) => setEstimatedAmount(e.target.value)} />
          </Field>
        </div>

        <Field label={t("procurement.form.neededBy")}>
          <input type="date" className={inputClass} value={neededByDate} onChange={(e) => setNeededByDate(e.target.value)} />
        </Field>

        <Field label={t("procurement.form.notes")}>
          <textarea className={`${inputClass} resize-y`} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t("procurement.form.notesPlaceholder")} />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createRequest.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createRequest.isPending || !materialName.trim() || !quantity || !unit.trim()}>
            {createRequest.isPending ? t("common.saving") : t("procurement.form.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
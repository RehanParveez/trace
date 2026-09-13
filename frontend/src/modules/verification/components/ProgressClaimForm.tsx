import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, Modal, inputClass } from "../../organizations/components/OrganizationUi";
import { useBOQVersions, useBOQItems } from "../../drawings_boq";
import { useCreateProgressClaim } from "../hooks";
import { formatClaimQuantity } from "../utils/verification.utils";
import { useTranslation } from "react-i18next";

interface ProgressClaimFormProps {
  projectId: string;
  onClose: () => void;
}

export function ProgressClaimForm({ projectId, onClose }: ProgressClaimFormProps) {
  const { t } = useTranslation();
  const boqVersionsQuery = useBOQVersions(projectId);
  const latestVersionId = boqVersionsQuery.data?.[0]?.id;
  const boqItemsQuery = useBOQItems(latestVersionId);
  const createClaim = useCreateProgressClaim();

  const approvedItems = (boqItemsQuery.data ?? []).filter((item) => item.status === "APPROVED");

  const [boqItemId, setBoqItemId] = useState("");
  const [claimDate, setClaimDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [claimedQuantity, setClaimedQuantity] = useState("");
  const [claimedPercentage, setClaimedPercentage] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const selectedItem = approvedItems.find((item) => item.id === boqItemId);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createClaim.mutate(
      {
        project_id: projectId,
        boq_item_id: boqItemId,
        claim_date: claimDate,
        claimed_quantity: Number(claimedQuantity),
        claimed_percentage: Number(claimedPercentage),
        notes: notes.trim() || null,
      },
      { onSuccess: onClose, onError: () => setError(t("verification.form.createError")) },
    );
  }

  return (
    <Modal title={t("verification.form.title")} description={t("verification.form.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("verification.form.boqItem")} hint={t("verification.form.boqItemHint")}>
          <select className={inputClass} required value={boqItemId} onChange={(e) => setBoqItemId(e.target.value)}>
            <option value="" disabled>
              {boqItemsQuery.isLoading ? t("verification.form.loadingItems") : approvedItems.length === 0 ? t("verification.form.noApprovedItems") : t("verification.form.selectItem")}
            </option>
            {approvedItems.map((item) => (
              <option key={item.id} value={item.id}>{item.material_name} ({item.unit})</option>
            ))}
          </select>
        </Field>

        {selectedItem ? (
          <div className="rounded-[8px] border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] px-3.5 py-2.5 text-[12px] text-[var(--color-info)]">
            {t("verification.form.contractedQuantity")}: {formatClaimQuantity(selectedItem.quantity, selectedItem.unit)}
          </div>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("verification.form.claimDate")}>
            <input type="date" className={inputClass} required value={claimDate} onChange={(e) => setClaimDate(e.target.value)} />
          </Field>
          <Field label={t("verification.form.claimedQuantity")}>
            <input type="number" step="any" min="0" className={inputClass} required value={claimedQuantity} onChange={(e) => setClaimedQuantity(e.target.value)} />
          </Field>
        </div>

        <Field label={t("verification.form.claimedPercentage")} hint={t("verification.form.claimedPercentageHint")}>
          <input type="number" step="any" min="0" max="100" className={inputClass} required value={claimedPercentage} onChange={(e) => setClaimedPercentage(e.target.value)} />
        </Field>

        <Field label={t("verification.form.notes")}>
          <textarea className={`${inputClass} resize-y`} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t("verification.form.notesPlaceholder")}/>
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createClaim.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createClaim.isPending || !boqItemId || !claimedQuantity || !claimedPercentage}>
            {createClaim.isPending ? t("common.saving") : t("verification.form.create")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
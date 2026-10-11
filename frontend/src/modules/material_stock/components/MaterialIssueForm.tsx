import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useMaterialReconciliation, useRecordMaterialIssue } from "../hooks";
import { getApiErrorCode } from "../../../shared/utils/apiError";
import type { MaterialIssueType } from "../types/material-stock.types";
import { useTranslation } from "react-i18next";
import { todayLocal } from "../../../shared/utils/date";

export function MaterialIssueForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const recordIssue = useRecordMaterialIssue(projectId);
  const { showToast } = useToast();
  const [materialName, setMaterialName] = useState("");
  const [unit, setUnit] = useState("");
  const [quantity, setQuantity] = useState("");
  const [issueType, setIssueType] = useState<MaterialIssueType>("ISSUED");
  const [issuedTo, setIssuedTo] = useState("");
  const [issueDate, setIssueDate] = useState(() => todayLocal());
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [shortStock, setShortStock] = useState(false);
  const stockQuery = useMaterialReconciliation(projectId);
  const stockLines = stockQuery.data?.lines ?? [];
  const knownLine = stockLines.find((line) => line.material_name.trim().toLowerCase() === materialName.trim().toLowerCase());
  const effectiveUnit = knownLine ? knownLine.unit : unit;

  function submit(event?: FormEvent<HTMLFormElement>, allowNegative = false) {
    event?.preventDefault();
    setError(null);
    recordIssue.mutate(
      { material_name: materialName.trim(), unit: effectiveUnit.trim(), quantity: Number(quantity), issue_type: issueType, issued_to: issuedTo.trim() || null, issue_date: issueDate, notes: notes.trim() || null, allow_negative_stock: allowNegative },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: issueType === "WASTAGE" ? t("materialStock.issueForm.wastageToast") : t("materialStock.issueForm.issueToast") }); },
        onError: (e) => {
          setShortStock(getApiErrorCode(e) === "INSUFFICIENT_STOCK");
          setError(getApiErrorMessage(e, t("materialStock.issueForm.saveErrorFallback")));
        },
      },
    );
  }

  return (
    <Modal title={t("materialStock.issueForm.title")} description={t("materialStock.issueForm.description")} onClose={onClose} wide>
      <form onSubmit={(event) => submit(event, false)} className="space-y-4">
        <div className="flex gap-2">
          <button type="button" onClick={() => setIssueType("ISSUED")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${issueType === "ISSUED" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>{t("materialStock.issueForm.issuedToWork")}</button>
          <button type="button" onClick={() => setIssueType("WASTAGE")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${issueType === "WASTAGE" ? "border-[var(--color-danger)] bg-[var(--color-danger-bg)]" : "border-[var(--color-border)]"}`}>{t("materialStock.issueForm.wastageLoss")}</button>
        </div>

        <Field label={t("materialStock.issueForm.materialName")}>
          <input required list="stock-materials" className={inputClass} value={materialName} onChange={(e) => { setMaterialName(e.target.value); setShortStock(false); }} placeholder={t("materialStock.issueForm.materialNamePlaceholder")} />
          <datalist id="stock-materials">{stockLines.map((line) => <option key={line.material_name} value={line.material_name} />)}</datalist>
        </Field>
        {knownLine ? (
          <div className="rounded-[8px] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">
            {t("materialStock.issueForm.inStock", { balance: Number(knownLine.balance).toFixed(2), unit: knownLine.unit })}
          </div>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("materialStock.issueForm.unit")}><input required className={inputClass} value={effectiveUnit} readOnly={Boolean(knownLine)} onChange={(e) => setUnit(e.target.value)} placeholder={t("materialStock.issueForm.unitPlaceholder")}/></Field>
          <Field label={t("materialStock.issueForm.quantity")}><input type="number" min="0.001" step="any" required className={inputClass} value={quantity} onChange={(e) => { setQuantity(e.target.value); setShortStock(false); }} /></Field>
        </div>

        {issueType === "ISSUED" ? (
          <Field label={t("materialStock.issueForm.issuedTo")} hint={t("materialStock.issueForm.issuedToHint")}><input className={inputClass} value={issuedTo} onChange={(e) => setIssuedTo(e.target.value)} /></Field>
        ) : null}

        <Field label={t("materialStock.issueForm.date")}><input type="date" required max={todayLocal()} className={inputClass} value={issueDate} onChange={(e) => setIssueDate(e.target.value)} /></Field>
        <Field label={t("materialStock.issueForm.notes")}><textarea className={`${inputClass} resize-y`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={recordIssue.isPending}>{t("common.cancel")}</Button>
          {shortStock ? (
            <Button type="button" variant="danger" disabled={recordIssue.isPending} onClick={() => submit(undefined, true)}>{t("materialStock.issueForm.issueAnyway")}</Button>
          ) : (
            <Button type="submit" variant="primary" disabled={recordIssue.isPending || !materialName.trim() || !effectiveUnit.trim() || !quantity}>{recordIssue.isPending ? t("common.saving") : t("common.save")}</Button>
          )}
        </div>
      </form>
    </Modal>
  );
}
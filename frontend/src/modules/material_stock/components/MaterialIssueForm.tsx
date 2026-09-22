import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useRecordMaterialIssue } from "../hooks";
import type { MaterialIssueType } from "../types/material-stock.types";

export function MaterialIssueForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const recordIssue = useRecordMaterialIssue(projectId);
  const { showToast } = useToast();
  const [materialName, setMaterialName] = useState("");
  const [unit, setUnit] = useState("");
  const [quantity, setQuantity] = useState("");
  const [issueType, setIssueType] = useState<MaterialIssueType>("ISSUED");
  const [issuedTo, setIssuedTo] = useState("");
  const [issueDate, setIssueDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    recordIssue.mutate(
      { material_name: materialName.trim(), unit: unit.trim(), quantity: Number(quantity), issue_type: issueType, issued_to: issuedTo.trim() || null, issue_date: issueDate, notes: notes.trim() || null },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: issueType === "WASTAGE" ? "Wastage recorded" : "Material issue recorded" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't record this entry.")),
      },
    );
  }

  return (
    <Modal title="Record material movement" description="Material issued to work, or lost to wastage/theft on site." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="flex gap-2">
          <button type="button" onClick={() => setIssueType("ISSUED")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${issueType === "ISSUED" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>Issued to work</button>
          <button type="button" onClick={() => setIssueType("WASTAGE")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${issueType === "WASTAGE" ? "border-[var(--color-danger)] bg-[var(--color-danger-bg)]" : "border-[var(--color-border)]"}`}>Wastage / loss</button>
        </div>

        <Field label="Material name"><input required className={inputClass} value={materialName} onChange={(e) => setMaterialName(e.target.value)} placeholder="e.g. Cement OPC 43" /></Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Unit"><input required className={inputClass} value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="bags" /></Field>
          <Field label="Quantity"><input type="number" min="0.001" step="any" required className={inputClass} value={quantity} onChange={(e) => setQuantity(e.target.value)} /></Field>
        </div>

        {issueType === "ISSUED" ? (
          <Field label="Issued to" hint="Optional — e.g. the crew or trade this was issued to"><input className={inputClass} value={issuedTo} onChange={(e) => setIssuedTo(e.target.value)} /></Field>
        ) : null}

        <Field label="Date"><input type="date" required className={inputClass} value={issueDate} onChange={(e) => setIssueDate(e.target.value)} /></Field>
        <Field label="Notes"><textarea className={`${inputClass} resize-y`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={recordIssue.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={recordIssue.isPending || !materialName.trim() || !unit.trim() || !quantity}>{recordIssue.isPending ? "Saving…" : "Save"}</Button>
        </div>
      </form>
    </Modal>
  );
}
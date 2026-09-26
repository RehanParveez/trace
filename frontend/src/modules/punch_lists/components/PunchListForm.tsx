import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreatePunchList } from "../hooks";

export function PunchListForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const createPunchList = useCreatePunchList(projectId);
  const { showToast } = useToast();
  const [title, setTitle] = useState("");
  const [inspectionDate, setInspectionDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createPunchList.mutate(
      { title: title.trim(), inspection_date: inspectionDate, notes: notes.trim() || null },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "Punch list created" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't create this punch list.")),
      },
    );
  }

  return (
    <Modal title="New punch list" description="A formal inspection round — e.g. Practical Completion, or the Defects Liability Period final inspection." onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Title"><input required className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Practical Completion Snag List" /></Field>
        <Field label="Inspection date"><input type="date" required className={inputClass} value={inspectionDate} onChange={(e) => setInspectionDate(e.target.value)} /></Field>
        <Field label="Notes"><textarea className={`${inputClass} resize-y`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createPunchList.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createPunchList.isPending || !title.trim()}>{createPunchList.isPending ? "Creating…" : "Create punch list"}</Button>
        </div>
      </form>
    </Modal>
  );
}
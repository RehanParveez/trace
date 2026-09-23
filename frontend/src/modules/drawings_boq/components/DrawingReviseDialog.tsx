import { useRef, useState } from "react";
import { Button, Field, Icon, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useReviseDrawing } from "../hooks";
import type { Drawing } from "../types/drawings-boq.types";

interface DrawingReviseDialogProps {
  projectId: string;
  previousDrawing: Drawing;
  onClose: () => void;
}

export function DrawingReviseDialog({ projectId, previousDrawing, onClose }: DrawingReviseDialogProps) {
  const revise = useReviseDrawing(projectId);
  const { showToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [revisionLabel, setRevisionLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    const lowerName = selected?.name.toLowerCase() ?? "";
    if (selected && !lowerName.endsWith(".ifc") && !lowerName.endsWith(".pdf")) {
      setError("Only .ifc and .pdf files are supported.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(selected);
  }

  function submit() {
    if (!file) return;
    revise.mutate(
      { drawingId: previousDrawing.id, file, revisionLabel: revisionLabel.trim() || null },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "New revision uploaded" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't upload this revision.")),
      },
    );
  }

  return (
    <Modal
      title="Upload new revision"
      description={`Replaces "${previousDrawing.original_filename}" as the current revision. The previous file stays accessible in the revision history.`}
      onClose={onClose}
    >
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-8 text-center transition hover:border-[var(--color-trace-gold-dark)]"
        >
          <Icon name="download" size={20} className="text-[var(--color-text-muted)]" />
          <span className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{file ? file.name : "Choose an IFC or PDF file"}</span>
        </button>
        <input ref={inputRef} type="file" accept=".ifc,.pdf" onChange={handleFileChange} className="hidden" />

        <Field label="Revision label" hint='e.g. "Rev B" or a date — whatever your team already uses'>
          <input className={inputClass} value={revisionLabel} onChange={(e) => setRevisionLabel(e.target.value)} placeholder="Rev B" />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={revise.isPending}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!file || revise.isPending}>{revise.isPending ? "Uploading…" : "Upload revision"}</Button>
        </div>
      </div>
    </Modal>
  );
}
import { useState } from "react";
import { Button, Icon, Modal } from "../../organizations/components/OrganizationUi";
import { useDrawingRevisions, useViewDrawingFile } from "../hooks";
import { formatFileSize } from "../utils/drawings-boq.utils";
import type { Drawing } from "../types/drawings-boq.types";
import { DrawingReviseDialog } from "./DrawingReviseDialog";

interface DrawingRevisionDialogProps {
  drawingId: string;
  projectId: string;
  canUpload: boolean;
  onClose: () => void;
  onViewElements: (drawing: Drawing) => void;
}

export function DrawingRevisionDialog({ drawingId, projectId, canUpload, onClose, onViewElements }: DrawingRevisionDialogProps) {
  const revisionsQuery = useDrawingRevisions(drawingId);
  const viewFile = useViewDrawingFile();
  const [selectedId, setSelectedId] = useState(drawingId);
  const [reviseOpen, setReviseOpen] = useState(false);

  const revisions = revisionsQuery.data ?? [];
  const selected = revisions.find((r) => r.id === selectedId) ?? revisions[revisions.length - 1];
  const currentRevision = revisions.find((r) => r.is_current_revision);

  return (
    <Modal title="Drawing revision history" description="All revisions of this drawing, oldest to newest." onClose={onClose} wide>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 border-b border-[var(--color-border)] pb-4">
          {revisions.map((revision, index) => (
            <button
              key={revision.id}
              type="button"
              onClick={() => setSelectedId(revision.id)}
              className={`rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${
                selectedId === revision.id
                  ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                  : !revision.is_current_revision
                    ? "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"
              }`}
            >
              {revision.revision_label || `Revision ${index + 1}`}
              {!revision.is_current_revision ? <span className="ml-1.5 text-[10px] font-normal italic">superseded</span> : null}
            </button>
          ))}
        </div>

        {selected ? (
          <div className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="min-w-0">
              <div className="truncate text-[13.5px] font-semibold text-[var(--color-text-primary)]">{selected.original_filename}</div>
              <div className="mt-0.5 text-[12px] text-[var(--color-text-secondary)]">
                {formatFileSize(selected.file_size_bytes)} · {selected.format}
                {!selected.is_current_revision && selected.superseded_at ? ` · Superseded ${selected.superseded_at.slice(0, 10)}` : ""}
              </div>
            </div>
            <div className="flex shrink-0 gap-2">
              <Button variant="ghost" size="sm" disabled={viewFile.isPending} onClick={() => viewFile.mutate(selected.id)}>
                {selected.format === "PDF" ? "View PDF" : "Download"}
              </Button>
              {selected.format !== "PDF" && selected.status === "PARSED" ? (
                <Button variant="ghost" size="sm" onClick={() => onViewElements(selected)}>View elements</Button>
              ) : null}
            </div>
          </div>
        ) : null}

        {canUpload && currentRevision ? (
          <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
            <Button variant="primary" onClick={() => setReviseOpen(true)}>Upload new revision</Button>
          </div>
        ) : null}
      </div>

      {reviseOpen && currentRevision ? (
        <DrawingReviseDialog projectId={projectId} previousDrawing={currentRevision} onClose={() => setReviseOpen(false)} />
      ) : null}
    </Modal>
  );
}
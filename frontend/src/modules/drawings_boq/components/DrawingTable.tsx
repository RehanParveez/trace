import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import type { Drawing } from "../types/drawings-boq.types";
import { formatDrawingStatus, formatFileSize, getDrawingStatusTone, isDrawingInProgress } from "../utils/drawings-boq.utils";

interface DrawingTableProps {
  drawings: Drawing[];
  canUpload: boolean;
  onUpload: () => void;
  onView: (drawing: Drawing) => void;
}

export function DrawingTable({ drawings, canUpload, onUpload, onView }: DrawingTableProps) {
  return (
    <Panel>
      <PanelHeader
        eyebrow="BIM INGESTION"
        title="Drawings"
        description="IFC drawings uploaded for this project and their parsing status."
        action={canUpload ? <Button variant="primary" size="sm" onClick={onUpload}><Icon name="plus" size={13} />Upload drawing</Button> : null}
      />

      {drawings.length === 0 ? (
        <EmptyState
          icon="building"
          title="No drawings yet"
          description="Upload an IFC file to generate a draft bill of quantities for this project."
          action={canUpload ? <Button variant="primary" size="sm" onClick={onUpload}>Upload drawing</Button> : undefined}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[640px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">File</th>
                <th className="px-4 py-3">Format</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {drawings.map((drawing) => (
                <tr key={drawing.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-3.5">
                    <button type="button" onClick={() => onView(drawing)} className="text-left">
                      <span className="block truncate text-[14px] font-semibold text-[var(--color-text-primary)]">{drawing.original_filename}</span>
                      {drawing.error_message ? (
                        <span className="mt-0.5 block max-w-[320px] truncate text-[12px] text-[var(--color-danger)]">{drawing.error_message}</span>
                      ) : null}
                    </button>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-[12px] text-[var(--color-text-secondary)]">{drawing.format}</td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <Badge tone={getDrawingStatusTone(drawing.status)}>{formatDrawingStatus(drawing.status)}</Badge>
                      {isDrawingInProgress(drawing.status) ? (
                        <span className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-trace-gold)]" />
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatFileSize(drawing.file_size_bytes)}</td>
                  <td className="px-4 py-3.5 text-right">
                    <Button variant="ghost" size="sm" disabled={drawing.status !== "PARSED"} onClick={() => onView(drawing)}>
                      View elements
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
import { EmptyState, ErrorState, LoadingState, Modal } from "../../organizations/components/OrganizationUi";
import { useDrawingElements } from "../hooks";
import type { Drawing } from "../types/drawings-boq.types";
import { formatQuantity } from "../utils/drawings-boq.utils";

interface DrawingElementsDialogProps {
  drawing: Drawing;
  onClose: () => void;
}

export function DrawingElementsDialog({ drawing, onClose }: DrawingElementsDialogProps) {
  const elementsQuery = useDrawingElements(drawing.id);

  return (
    <Modal title={drawing.original_filename} description="Elements extracted from this drawing by the IFC parsing pipeline." onClose={onClose} wide>
      {elementsQuery.isLoading ? (
        <LoadingState label="Loading elements…" />
      ) : elementsQuery.isError || !elementsQuery.data ? (
        <ErrorState title="Couldn't load elements" onRetry={() => void elementsQuery.refetch()} />
      ) : elementsQuery.data.length === 0 ? (
        <EmptyState icon="info" title="No elements found" description="This drawing produced no extractable elements." />
      ) : (
        <div className="max-h-[60vh] overflow-y-auto">
          <table className="w-full min-w-[600px] text-left">
            <thead className="sticky top-0 bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-3 py-2.5">Type</th>
                <th className="px-3 py-2.5">Name</th>
                <th className="px-3 py-2.5">Material text</th>
                <th className="px-3 py-2.5 text-right">Quantity</th>
              </tr>
            </thead>
            <tbody>
              {elementsQuery.data.map((element) => (
                <tr key={element.id} className="border-t border-[var(--color-border)]">
                  <td className="px-3 py-2.5 font-mono text-[12px] text-[var(--color-text-secondary)]">{element.ifc_type}</td>
                  <td className="px-3 py-2.5 text-[12.5px] text-[var(--color-text-primary)]">{element.name ?? "—"}</td>
                  <td className="px-3 py-2.5 text-[12.5px] text-[var(--color-text-secondary)]">{element.raw_material_text ?? "—"}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-[12.5px] text-[var(--color-text-primary)]">
                    {formatQuantity(element.quantity)} {element.unit ?? ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}
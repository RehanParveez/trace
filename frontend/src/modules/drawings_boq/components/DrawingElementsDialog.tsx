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
            <thead className="sticky top-0 bg-[#f5efe3]">
              <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                <th className="px-3 py-2.5">Type</th>
                <th className="px-3 py-2.5">Name</th>
                <th className="px-3 py-2.5">Material text</th>
                <th className="px-3 py-2.5 text-right">Quantity</th>
              </tr>
            </thead>
            <tbody>
              {elementsQuery.data.map((element) => (
                <tr key={element.id} className="border-t border-[#e1d5bc]">
                  <td className="px-3 py-2.5 font-mono text-[10.5px] text-[#6b6152]">{element.ifc_type}</td>
                  <td className="px-3 py-2.5 text-[11px] text-[#191410]">{element.name ?? "—"}</td>
                  <td className="px-3 py-2.5 text-[11px] text-[#6b6152]">{element.raw_material_text ?? "—"}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-[11px] text-[#191410]">
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
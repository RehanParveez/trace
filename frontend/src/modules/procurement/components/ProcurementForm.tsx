import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal } from "../../organizations/components/OrganizationUi";
import { useCreateProcurementRequest } from "../hooks";

interface ProcurementFormProps {
  projectId: string;
  onClose: () => void;
}

export function ProcurementForm({ projectId, onClose }: ProcurementFormProps) {
  const createRequest = useCreateProcurementRequest();

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
        onSuccess: onClose,
        onError: () => setError("Couldn't create this request. Please try again."),
      },
    );
  }

  return (
    <Modal title="New material request" description="Request materials for procurement approval." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Material / description">
          <input required className={inputClass} value={materialName} onChange={(e) => setMaterialName(e.target.value)} placeholder="e.g. Cement OPC 43" />
        </Field>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Quantity">
            <input type="number" step="any" min="0.01" required className={inputClass} value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          <Field label="Unit">
            <input required className={inputClass} value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="bags" />
          </Field>
          <Field label="Estimated cost (PKR)">
            <input type="number" step="any" min="0" className={inputClass} value={estimatedAmount} onChange={(e) => setEstimatedAmount(e.target.value)} />
          </Field>
        </div>

        <Field label="Needed by">
          <input type="date" className={inputClass} value={neededByDate} onChange={(e) => setNeededByDate(e.target.value)} />
        </Field>

        <Field label="Notes">
          <textarea className={`${inputClass} resize-y`} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional context for this request" />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createRequest.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createRequest.isPending || !materialName.trim() || !quantity || !unit.trim()}>
            {createRequest.isPending ? "Saving…" : "Submit request"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
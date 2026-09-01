import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Modal } from "../../organizations/components/OrganizationUi";
import { useAddCustomBOQItem } from "../hooks";

interface AddCustomBOQItemDialogProps {
  boqVersionId: string;
  onClose: () => void;
}

export function AddCustomBOQItemDialog({ boqVersionId, onClose }: AddCustomBOQItemDialogProps) {
  const addItem = useAddCustomBOQItem(boqVersionId);

  const [materialName, setMaterialName] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitRate, setUnitRate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const cls = "mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    addItem.mutate(
      {
        material_name: materialName.trim(),
        category: category.trim() || null,
        unit: unit.trim(),
        quantity: Number(quantity),
        unit_rate: unitRate === "" ? null : Number(unitRate),
      },
      {
        onSuccess: onClose,
        onError: () => setError("Couldn't add this line item. Please try again."),
      },
    );
  }

  return (
    <Modal title="Add line item" description="Add scope not covered by the automated categories." onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Description *</span>
          <input className={cls} required value={materialName} onChange={(e) => setMaterialName(e.target.value)} placeholder="Description of work" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Category</span>
            <input className={cls} value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Optional" />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Unit *</span>
            <input className={cls} required value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="Sft" />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Quantity *</span>
            <input className={cls} required type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Rate (PKR)</span>
            <input className={cls} type="number" step="any" value={unitRate} onChange={(e) => setUnitRate(e.target.value)} placeholder="Optional" />
          </label>
        </div>

        {error ? <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={addItem.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={addItem.isPending || !materialName.trim() || !unit.trim() || quantity === ""}>
            {addItem.isPending ? "Adding…" : "Add item"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
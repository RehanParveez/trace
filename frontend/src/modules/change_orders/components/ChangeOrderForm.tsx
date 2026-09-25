import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, Icon, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useBOQVersions, useBOQItems } from "../../drawings_boq";
import { useCreateChangeOrder } from "../hooks";
import type { ChangeOrderType } from "../types/change-order.types";

interface LineDraft {
  mode: "new" | "adjust";
  description: string;
  unit: string;
  boqItemId: string;
  quantity: string;
  unitRate: string;
}

const EMPTY_LINE: LineDraft = { mode: "new", description: "", unit: "", boqItemId: "", quantity: "", unitRate: "" };

export function ChangeOrderForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const boqVersionsQuery = useBOQVersions(projectId);
  const [boqVersionId, setBoqVersionId] = useState("");
  const boqItemsQuery = useBOQItems(boqVersionId || undefined);
  const createChangeOrder = useCreateChangeOrder(projectId);
  const { showToast } = useToast();

  const boqVersions = boqVersionsQuery.data ?? [];
  const activeBoqVersionId = boqVersionId || boqVersions[0]?.id || "";
  const boqItems = boqItemsQuery.data ?? [];

  const [changeType, setChangeType] = useState<ChangeOrderType>("ADDITION");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [clientReference, setClientReference] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([{ ...EMPTY_LINE }]);
  const [error, setError] = useState<string | null>(null);

  function updateLine(index: number, patch: Partial<LineDraft>) {
    setLines((current) => current.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const line_items = lines
      .filter((line) => line.description.trim())
      .map((line) => {
        if (line.mode === "new") {
          return {
            description: line.description.trim(), unit: line.unit.trim(),
            boq_item_id: null, quantity: Number(line.quantity), unit_rate: Number(line.unitRate),
          };
        }
        return {
          description: line.description.trim(), unit: line.unit.trim(),
          boq_item_id: line.boqItemId, quantity: Number(line.quantity),
          unit_rate: line.unitRate === "" ? null : Number(line.unitRate),
        };
      });

    createChangeOrder.mutate(
      {
        boq_version_id: activeBoqVersionId, change_type: changeType, title: title.trim(),
        description: description.trim() || null, client_reference: clientReference.trim() || null, line_items,
      },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "Change order drafted" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't create this change order.")),
      },
    );
  }

  return (
    <Modal title="New change order" description="A formal record of a scope change — additions, omissions, or price/quantity variations against the current BOQ." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label="BOQ version">
          <select required className={inputClass} value={activeBoqVersionId} onChange={(e) => setBoqVersionId(e.target.value)}>
            {boqVersions.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
          </select>
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Type">
            <select className={inputClass} value={changeType} onChange={(e) => setChangeType(e.target.value as ChangeOrderType)}>
              <option value="ADDITION">Addition</option>
              <option value="OMISSION">Omission</option>
              <option value="VARIATION">Variation</option>
            </select>
          </Field>
          <Field label="Client reference (optional)"><input className={inputClass} value={clientReference} onChange={(e) => setClientReference(e.target.value)} placeholder="e.g. Client email dated 20 Sep" /></Field>
        </div>

        <Field label="Title"><input required className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Add extra washroom, 3rd floor" /></Field>
        <Field label="Description"><textarea className={`${inputClass} resize-y`} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[12px] font-semibold uppercase tracking-[0.04em] text-[var(--color-text-secondary)]">Line items</span>
            <button type="button" onClick={() => setLines((cur) => [...cur, { ...EMPTY_LINE }])} className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline">Add line</button>
          </div>

          <div className="space-y-3">
            {lines.map((line, index) => (
              <div key={index} className="rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
                <div className="mb-2 flex gap-2">
                  <button type="button" onClick={() => updateLine(index, { mode: "new", boqItemId: "" })} className={`flex-1 rounded-[6px] border px-2 py-1.5 text-[11.5px] font-semibold ${line.mode === "new" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>New item</button>
                  <button type="button" onClick={() => updateLine(index, { mode: "adjust" })} className={`flex-1 rounded-[6px] border px-2 py-1.5 text-[11.5px] font-semibold ${line.mode === "adjust" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>Adjust existing item</button>
                  <button type="button" onClick={() => setLines((cur) => cur.filter((_, i) => i !== index))} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[6px] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]"><Icon name="x" size={13} /></button>
                </div>

                {line.mode === "adjust" ? (
                  <select className={`${inputClass} mb-2`} value={line.boqItemId} onChange={(e) => {
                    const item = boqItems.find((i) => i.id === e.target.value);
                    updateLine(index, { boqItemId: e.target.value, description: item ? `Adjustment: ${item.material_name}` : line.description, unit: item?.unit ?? line.unit });
                  }}>
                    <option value="">Select an existing BOQ item</option>
                    {boqItems.map((item) => <option key={item.id} value={item.id}>{item.material_name} ({item.unit})</option>)}
                  </select>
                ) : (
                  <input className={`${inputClass} mb-2`} placeholder="Description" value={line.description} onChange={(e) => updateLine(index, { description: e.target.value })} />
                )}

                <div className="grid grid-cols-3 gap-2">
                  <input className={inputClass} placeholder="Unit" value={line.unit} onChange={(e) => updateLine(index, { unit: e.target.value })} />
                  <input type="number" step="any" className={inputClass} placeholder={line.mode === "adjust" ? "Qty delta (± )" : "Quantity"} value={line.quantity} onChange={(e) => updateLine(index, { quantity: e.target.value })} />
                  <input type="number" step="any" className={inputClass} placeholder={line.mode === "adjust" ? "Rate override (optional)" : "Rate"} value={line.unitRate} onChange={(e) => updateLine(index, { unitRate: e.target.value })} />
                </div>
                {line.mode === "adjust" ? (
                  <p className="mt-1.5 text-[11px] text-[var(--color-text-muted)]">Use a negative quantity for an omission. Leave rate blank to keep the item's current rate.</p>
                ) : null}
              </div>
            ))}
          </div>
        </div>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createChangeOrder.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createChangeOrder.isPending || !title.trim() || !activeBoqVersionId}>{createChangeOrder.isPending ? "Creating…" : "Create draft"}</Button>
        </div>
      </form>
    </Modal>
  );
}
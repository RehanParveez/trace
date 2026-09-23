import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, Icon, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateAgreement, useSubcontractors } from "../hooks";
import { useTranslation } from "react-i18next";

export function AgreementForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const subsQuery = useSubcontractors();
  const createAgreement = useCreateAgreement(projectId);
  const { showToast } = useToast();

  const [subcontractorId, setSubcontractorId] = useState("");
  const [scope, setScope] = useState("");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [retention, setRetention] = useState("10");
  const [pricingMode, setPricingMode] = useState<"lump_sum" | "items">("lump_sum");
  const [contractValue, setContractValue] = useState("");
  const [items, setItems] = useState([{ description: "", unit: "", quantity: "", rate: "" }]);
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const payload: any = {
      subcontractor_id: subcontractorId,
      scope_description: scope.trim(),
      start_date: startDate,
      default_retention_percentage: Number(retention),
    };

    if (pricingMode === "lump_sum") {
      payload.contract_value = Number(contractValue);
    } else {
      payload.items = items
        .filter((item) => item.description.trim())
        .map((item) => ({ description: item.description.trim(), unit: item.unit.trim(), quantity: Number(item.quantity), rate: Number(item.rate) }));
    }

    createAgreement.mutate(payload, {
      onSuccess: () => { onClose(); showToast({ tone: "success", title: t("subcontractors.agreementForm.title") }); },
      onError: (mutationError) => setError(getApiErrorMessage(mutationError, "Couldn't create this agreement.")),
    });
  }

  return (
    <Modal title="New subcontract agreement" description="A trade package subcontracted to a specific company for this project." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Subcontractor">
          <select required className={inputClass} value={subcontractorId} onChange={(e) => setSubcontractorId(e.target.value)}>
            <option value="">Select a subcontractor</option>
            {(subsQuery.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.name} ({s.trade_specialization})</option>)}
          </select>
        </Field>

        <Field label="Scope of work"><textarea required className={`${inputClass} resize-y`} rows={2} value={scope} onChange={(e) => setScope(e.target.value)} placeholder="e.g. Complete electrical installation for Blocks A & B" /></Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Start date"><input type="date" required className={inputClass} value={startDate} onChange={(e) => setStartDate(e.target.value)} /></Field>
          <Field label="Retention %"><input type="number" step="0.01" min="0" max="100" required className={inputClass} value={retention} onChange={(e) => setRetention(e.target.value)} /></Field>
        </div>

        <div className="flex gap-2">
          <button type="button" onClick={() => setPricingMode("lump_sum")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${pricingMode === "lump_sum" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>Lump sum</button>
          <button type="button" onClick={() => setPricingMode("items")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${pricingMode === "items" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>Item-rate</button>
        </div>

        {pricingMode === "lump_sum" ? (
          <Field label="Contract value (PKR)"><input type="number" min="0.01" step="any" required className={inputClass} value={contractValue} onChange={(e) => setContractValue(e.target.value)} /></Field>
        ) : (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[12px] font-semibold uppercase tracking-[0.04em] text-[var(--color-text-secondary)]">Items</span>
              <button type="button" onClick={() => setItems((cur) => [...cur, { description: "", unit: "", quantity: "", rate: "" }])} className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline">Add item</button>
            </div>
            <div className="space-y-2">
              {items.map((item, index) => (
                <div key={index} className="flex gap-2">
                  <input className={inputClass} placeholder="Description" value={item.description} onChange={(e) => setItems((cur) => cur.map((it, i) => i === index ? { ...it, description: e.target.value } : it))} />
                  <input className={`${inputClass} w-20`} placeholder="Unit" value={item.unit} onChange={(e) => setItems((cur) => cur.map((it, i) => i === index ? { ...it, unit: e.target.value } : it))} />
                  <input type="number" className={`${inputClass} w-24`} placeholder="Qty" value={item.quantity} onChange={(e) => setItems((cur) => cur.map((it, i) => i === index ? { ...it, quantity: e.target.value } : it))} />
                  <input type="number" className={`${inputClass} w-28`} placeholder="Rate" value={item.rate} onChange={(e) => setItems((cur) => cur.map((it, i) => i === index ? { ...it, rate: e.target.value } : it))} />
                  <button type="button" onClick={() => setItems((cur) => cur.filter((_, i) => i !== index))} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]"><Icon name="x" size={14} /></button>
                </div>
              ))}
            </div>
          </div>
        )}

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createAgreement.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createAgreement.isPending || !subcontractorId || !scope.trim()}>{createAgreement.isPending ? "Creating…" : "Create agreement"}</Button>
        </div>
      </form>
    </Modal>
  );
}
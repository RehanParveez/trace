import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useCreateWorkItem, useFormulas } from "../hooks";
import { CANONICAL_UNITS } from "../utils/standards.utils";

export function WorkItemForm({ onClose }: { onClose: () => void }) {
  const formulasQuery = useFormulas();
  const createWorkItem = useCreateWorkItem();
  const { showToast } = useToast();

  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [unit, setUnit] = useState<string>("m3");
  const [trade, setTrade] = useState("");
  const [wbsCode, setWbsCode] = useState("");
  const [materialClass, setMaterialClass] = useState("");
  const [formulaCode, setFormulaCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const formulas = (formulasQuery.data ?? []).filter((f) => f.output_unit === unit);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createWorkItem.mutate(
      {
        code: code.trim().toUpperCase(), description: description.trim(), unit,
        trade: trade.trim() || null, wbs_code: wbsCode.trim() || null,
        default_formula_code: formulaCode || null,
        extra: materialClass.trim() ? { material_class: materialClass.trim().toUpperCase() } : {},
      },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "Work item created" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't create this work item.")),
      },
    );
  }

  return (
    <Modal title="New work item" description="A catalog entry that mappings and recipes emit, so BOQ lines can be priced and compared consistently." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Code"><input required className={inputClass} value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. FIN-SKIRTING" /></Field>
          <Field label="Unit">
            <select className={inputClass} value={unit} onChange={(e) => { setUnit(e.target.value); setFormulaCode(""); }}>
              {CANONICAL_UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </Field>
        </div>
        <Field label="Description"><input required className={inputClass} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Trade"><input className={inputClass} value={trade} onChange={(e) => setTrade(e.target.value)} /></Field>
          <Field label="WBS code"><input className={inputClass} value={wbsCode} onChange={(e) => setWbsCode(e.target.value)} /></Field>
          <Field label="Material class (for wastage)"><input className={inputClass} value={materialClass} onChange={(e) => setMaterialClass(e.target.value)} placeholder="CONCRETE" /></Field>
        </div>
        <Field label="Default formula (optional)">
          <select className={inputClass} value={formulaCode} onChange={(e) => setFormulaCode(e.target.value)}>
            <option value="">None</option>
            {formulas.map((f) => <option key={f.code} value={f.code}>{f.code}</option>)}
          </select>
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createWorkItem.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createWorkItem.isPending || !code.trim() || !description.trim()}>{createWorkItem.isPending ? "Saving…" : "Create work item"}</Button>
        </div>
      </form>
    </Modal>
  );
}

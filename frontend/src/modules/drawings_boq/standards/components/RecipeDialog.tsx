import { useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Field, Icon, inputClass, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useFormulas, useUpsertRecipe } from "../hooks";
import type { Recipe, RecipeItemType, WorkItem } from "../types/standards.types";

interface ComponentDraft {
  work_item_code: string; description_template: string; formula: string; item_type: RecipeItemType;
  is_optional: boolean; category: string;
}

const blank = (): ComponentDraft => ({ work_item_code: "", description_template: "", formula: "", item_type: "MATERIAL", is_optional: false, category: "" });

export function RecipeDialog({ ruleSetId, recipe, workItems, onClose }: {
  ruleSetId: string; recipe: Recipe | null; workItems: WorkItem[]; onClose: () => void;
}) {
  const formulasQuery = useFormulas();
  const upsert = useUpsertRecipe(ruleSetId);
  const { showToast } = useToast();
  const formulas = formulasQuery.data ?? [];

  const [code, setCode] = useState(recipe?.code ?? "");
  const [name, setName] = useState(recipe?.name ?? "");
  const [triggers, setTriggers] = useState((recipe?.trigger_ifc_types ?? []).join(", "));
  const [components, setComponents] = useState<ComponentDraft[]>(
    recipe
      ? [...recipe.components].sort((a, b) => a.sequence - b.sequence).map((c) => ({
          work_item_code: c.work_item_code ?? "", description_template: c.description_template, formula: c.quantity_formula_code,
          item_type: c.item_type, is_optional: c.is_optional, category: c.category ?? "",
        }))
      : [blank()],
  );
  const [error, setError] = useState<string | null>(null);

  const triggerList = triggers.split(",").map((t) => t.trim()).filter(Boolean);
  const unitFor = (formula: string) => formulas.find((f) => f.code === formula)?.output_unit ?? "";
  const valid = code.trim() && name.trim() && triggerList.length > 0 && components.length > 0
    && components.every((c) => c.formula && c.description_template.trim());

  function patch(index: number, change: Partial<ComponentDraft>) {
    setComponents((current) => current.map((c, i) => (i === index ? { ...c, ...change } : c)));
  }

  function pickWorkItem(index: number, workItemCode: string) {
    const item = workItems.find((w) => w.code === workItemCode);
    setComponents((current) => current.map((c, i) => (i !== index ? c : {
      ...c, work_item_code: workItemCode,
      formula: c.formula || item?.default_formula_code || "",
      description_template: c.description_template || (item ? `${item.description} to {material}` : ""),
      category: c.category || item?.trade || "",
    })));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    upsert.mutate(
      {
        code: code.trim().toUpperCase(), name: name.trim(), trigger_ifc_types: triggerList,
        components: components.map((c, i) => ({
          sequence: i + 1, work_item_code: c.work_item_code || null, description_template: c.description_template.trim(),
          unit: unitFor(c.formula), quantity_formula_code: c.formula, category: c.category.trim() || null,
          item_type: c.item_type, is_optional: c.is_optional,
        })),
      },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "Recipe saved" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't save this recipe.")),
      },
    );
  }

  return (
    <Modal title={recipe ? `Edit recipe ${recipe.code}` : "New recipe"} description="A recipe derives extra work items (formwork, plaster, paint…) from a measured element. Units come from the formula, so they can't be mixed up." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Code"><input required disabled={Boolean(recipe)} className={inputClass} value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. WALL_FINISHES" /></Field>
          <Field label="Name"><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} /></Field>
        </div>
        <Field label="Triggers on IFC types (comma separated)"><input required className={inputClass} value={triggers} onChange={(e) => setTriggers(e.target.value)} placeholder="IfcWall, IfcWallStandardCase" /></Field>

        <div className="space-y-3">
          {components.map((c, i) => {
            const formula = formulas.find((f) => f.code === c.formula);
            return (
              <div key={i} className="space-y-3 rounded-[8px] border border-[var(--color-border)] p-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Work item">
                    <select className={inputClass} value={c.work_item_code} onChange={(e) => pickWorkItem(i, e.target.value)}>
                      <option value="">None</option>
                      {workItems.map((w) => <option key={w.id} value={w.code}>{w.code} — {w.description} ({w.unit})</option>)}
                    </select>
                  </Field>
                  <Field label="Formula">
                    <select required className={inputClass} value={c.formula} onChange={(e) => patch(i, { formula: e.target.value })}>
                      <option value="">Select a formula</option>
                      {formulas.map((f) => <option key={f.code} value={f.code}>{f.code} → {f.output_unit}</option>)}
                    </select>
                  </Field>
                </div>
                <Field label="Description ({material} is replaced by the parent material)"><input required className={inputClass} value={c.description_template} onChange={(e) => patch(i, { description_template: e.target.value })} /></Field>
                <div className="flex flex-wrap items-center gap-3">
                  <select className={`${inputClass} max-w-[160px]`} value={c.item_type} onChange={(e) => patch(i, { item_type: e.target.value as RecipeItemType })}>
                    <option value="MATERIAL">Material</option><option value="LABOUR">Labour</option><option value="CUSTOM">Custom</option>
                  </select>
                  <label className="flex items-center gap-2 text-[12.5px] text-[var(--color-text-primary)]">
                    <input type="checkbox" checked={c.is_optional} onChange={(e) => patch(i, { is_optional: e.target.checked })} className="h-4 w-4 accent-[var(--color-trace-gold)]" />Optional
                  </label>
                  {formula ? <Badge tone="blue">Unit: {formula.output_unit}</Badge> : null}
                  {formula?.needs_kernel ? <Badge tone="gold">Calculated by the measurement engine</Badge> : null}
                  <div className="ml-auto">{components.length > 1 ? <Button type="button" variant="ghost" size="sm" onClick={() => setComponents((cur) => cur.filter((_, x) => x !== i))}>Remove</Button> : null}</div>
                </div>
                {formula ? <p className="text-[11.5px] text-[var(--color-text-secondary)]">{formula.description}</p> : null}
              </div>
            );
          })}
          <Button type="button" variant="secondary" size="sm" onClick={() => setComponents((cur) => [...cur, blank()])}><Icon name="plus" size={13} />Add component</Button>
        </div>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={upsert.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={upsert.isPending || !valid}>{upsert.isPending ? "Saving…" : "Save recipe"}</Button>
        </div>
      </form>
    </Modal>
  );
}

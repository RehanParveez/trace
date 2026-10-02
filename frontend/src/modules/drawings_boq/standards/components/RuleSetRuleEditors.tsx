import { useState } from "react";
import { Badge, Button, Icon, inputClass, TableShell } from "../../../organizations/components/OrganizationUi";
import type {
  DeductionBehavior, ElementMapping, OpeningRule, ReinforcementRule, WastageRule, WorkItem,
} from "../types/standards.types";

interface EditorProps<T> { rows: T[]; editable: boolean; saving: boolean; onSave: (rows: T[]) => void }

const th = "px-3 py-3";
const thead = "bg-[var(--color-surface-muted)] text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const td = "px-3 py-2.5";

function EditorFooter({ editable, dirty, saving, onAdd, onSave }: { editable: boolean; dirty: boolean; saving: boolean; onAdd: () => void; onSave: () => void }) {
  if (!editable) return null;
  return (
    <div className="flex justify-between border-t border-[var(--color-border)] px-3 py-3">
      <Button variant="secondary" size="sm" onClick={onAdd}><Icon name="plus" size={13} />Add row</Button>
      <Button variant="primary" size="sm" onClick={onSave} disabled={!dirty || saving}>{saving ? "Saving…" : "Save changes"}</Button>
    </div>
  );
}

/* ------------------------------------------------------------------ opening rules */
interface OpeningDraft {
  element_scope: string; lower_area_m2: string; upper_area_m2: string; deduction_behavior: DeductionBehavior;
  deduction_fraction: string; edge_behavior: string; extra_config: Record<string, unknown>;
}

export function OpeningRulesEditor({ rows, editable, saving, onSave }: EditorProps<OpeningRule>) {
  const [drafts, setDrafts] = useState<OpeningDraft[]>(() => rows.map((r) => ({
    element_scope: r.element_scope, lower_area_m2: String(r.lower_area_m2), upper_area_m2: r.upper_area_m2 == null ? "" : String(r.upper_area_m2),
    deduction_behavior: r.deduction_behavior, deduction_fraction: r.deduction_fraction == null ? "" : String(r.deduction_fraction),
    edge_behavior: r.edge_behavior ?? "", extra_config: r.extra_config ?? {},
  })));
  const [dirty, setDirty] = useState(false);

  function patch(index: number, change: Partial<OpeningDraft>) {
    setDrafts((current) => current.map((d, i) => (i === index ? { ...d, ...change } : d)));
    setDirty(true);
  }

  function save() {
    onSave(drafts.map((d) => ({
      element_scope: d.element_scope.trim() || "ALL", lower_area_m2: Number(d.lower_area_m2 || 0),
      upper_area_m2: d.upper_area_m2 === "" ? null : Number(d.upper_area_m2),
      deduction_behavior: d.deduction_behavior,
      deduction_fraction: d.deduction_behavior === "PARTIAL" && d.deduction_fraction !== "" ? Number(d.deduction_fraction) : null,
      edge_behavior: d.edge_behavior.trim() || null, extra_config: d.extra_config,
    })));
    setDirty(false);
  }

  return (
    <TableShell>
      <table className="w-full min-w-[760px] text-left">
        <thead className={thead}><tr><th className={th}>Scope</th><th className={th}>From (m²)</th><th className={th}>Up to, excl. (m²)</th><th className={th}>Behaviour</th><th className={th}>Fraction</th><th className={th} /></tr></thead>
        <tbody>
          {drafts.map((d, i) => (
            <tr key={i} className="border-t border-[var(--color-border)]">
              <td className={td}><input disabled={!editable} className={inputClass} value={d.element_scope} onChange={(e) => patch(i, { element_scope: e.target.value })} /></td>
              <td className={td}><input disabled={!editable} type="number" min="0" step="any" className={inputClass} value={d.lower_area_m2} onChange={(e) => patch(i, { lower_area_m2: e.target.value })} /></td>
              <td className={td}><input disabled={!editable} type="number" min="0" step="any" className={inputClass} value={d.upper_area_m2} onChange={(e) => patch(i, { upper_area_m2: e.target.value })} placeholder="open-ended" /></td>
              <td className={td}>
                <select disabled={!editable} className={inputClass} value={d.deduction_behavior} onChange={(e) => patch(i, { deduction_behavior: e.target.value as DeductionBehavior })}>
                  <option value="DEDUCT">Deduct</option><option value="IGNORE">Ignore</option><option value="PARTIAL">Partial</option>
                </select>
              </td>
              <td className={td}><input disabled={!editable || d.deduction_behavior !== "PARTIAL"} type="number" min="0" max="1" step="any" className={inputClass} value={d.deduction_fraction} onChange={(e) => patch(i, { deduction_fraction: e.target.value })} /></td>
              <td className={`${td} text-right`}>{editable ? <Button variant="ghost" size="sm" onClick={() => { setDrafts((c) => c.filter((_, x) => x !== i)); setDirty(true); }}>Remove</Button> : null}</td>
            </tr>
          ))}
          {drafts.length === 0 ? <tr><td colSpan={6} className="px-3 py-6 text-center text-[12.5px] text-[var(--color-text-muted)]">No opening rules — every opening is fully deducted.</td></tr> : null}
        </tbody>
      </table>
      <EditorFooter editable={editable} dirty={dirty} saving={saving} onSave={save}
        onAdd={() => { setDrafts((c) => [...c, { element_scope: "ALL", lower_area_m2: "0", upper_area_m2: "", deduction_behavior: "DEDUCT", deduction_fraction: "", edge_behavior: "", extra_config: {} }]); setDirty(true); }} />
    </TableShell>
  );
}

/* ------------------------------------------------------------------ wastage */
interface WastageDraft { material_class: string; procurement_stage: string; factor: string; unit: string; justification: string }

export function WastageRulesEditor({ rows, editable, saving, onSave }: EditorProps<WastageRule>) {
  const [drafts, setDrafts] = useState<WastageDraft[]>(() => rows.map((r) => ({
    material_class: r.material_class, procurement_stage: r.procurement_stage, factor: String(r.factor),
    unit: r.unit ?? "", justification: r.justification ?? "",
  })));
  const [dirty, setDirty] = useState(false);

  function patch(index: number, change: Partial<WastageDraft>) {
    setDrafts((current) => current.map((d, i) => (i === index ? { ...d, ...change } : d)));
    setDirty(true);
  }

  function save() {
    onSave(drafts.map((d) => ({
      material_class: d.material_class.trim().toUpperCase(), procurement_stage: d.procurement_stage.trim() || "SITE",
      factor: Number(d.factor || 1), unit: d.unit.trim() || null, justification: d.justification.trim() || null,
    })));
    setDirty(false);
  }

  return (
    <TableShell>
      <table className="w-full min-w-[760px] text-left">
        <thead className={thead}><tr><th className={th}>Material class</th><th className={th}>Stage</th><th className={th}>Factor (1.03 = 3 % extra)</th><th className={th}>Justification</th><th className={th} /></tr></thead>
        <tbody>
          {drafts.map((d, i) => (
            <tr key={i} className="border-t border-[var(--color-border)]">
              <td className={td}><input disabled={!editable} className={inputClass} value={d.material_class} onChange={(e) => patch(i, { material_class: e.target.value })} placeholder="CONCRETE, DEFAULT…" /></td>
              <td className={td}><input disabled={!editable} className={inputClass} value={d.procurement_stage} onChange={(e) => patch(i, { procurement_stage: e.target.value })} /></td>
              <td className={td}><input disabled={!editable} type="number" min="1" max="2" step="any" className={inputClass} value={d.factor} onChange={(e) => patch(i, { factor: e.target.value })} /></td>
              <td className={td}><input disabled={!editable} className={inputClass} value={d.justification} onChange={(e) => patch(i, { justification: e.target.value })} /></td>
              <td className={`${td} text-right`}>{editable ? <Button variant="ghost" size="sm" onClick={() => { setDrafts((c) => c.filter((_, x) => x !== i)); setDirty(true); }}>Remove</Button> : null}</td>
            </tr>
          ))}
          {drafts.length === 0 ? <tr><td colSpan={5} className="px-3 py-6 text-center text-[12.5px] text-[var(--color-text-muted)]">No wastage rules — no extra is added to any material.</td></tr> : null}
        </tbody>
      </table>
      <EditorFooter editable={editable} dirty={dirty} saving={saving} onSave={save}
        onAdd={() => { setDrafts((c) => [...c, { material_class: "", procurement_stage: "SITE", factor: "1.00", unit: "", justification: "" }]); setDirty(true); }} />
    </TableShell>
  );
}

/* ------------------------------------------------------------------ element mappings */
interface MappingDraft {
  ifc_type: string; work_item_code: string; default_category: string; unit_override: string;
  confidence_base: string; material_class: string; quantity_source_preference: string; extra_mapping: Record<string, unknown>;
}

export function MappingsEditor({ rows, editable, saving, workItems, onSave }: EditorProps<ElementMapping> & { workItems: WorkItem[] }) {
  const [drafts, setDrafts] = useState<MappingDraft[]>(() => rows.map((r) => ({
    ifc_type: r.ifc_type, work_item_code: r.work_item_code ?? "", default_category: r.default_category ?? "",
    unit_override: r.unit_override ?? "", confidence_base: String(r.confidence_base),
    material_class: typeof r.extra_mapping?.material_class === "string" ? r.extra_mapping.material_class : "",
    quantity_source_preference: r.quantity_source_preference, extra_mapping: r.extra_mapping ?? {},
  })));
  const [dirty, setDirty] = useState(false);

  function patch(index: number, change: Partial<MappingDraft>) {
    setDrafts((current) => current.map((d, i) => (i === index ? { ...d, ...change } : d)));
    setDirty(true);
  }

  function save() {
    onSave(drafts.map((d) => {
      const extra = { ...d.extra_mapping };
      if (d.material_class.trim()) extra.material_class = d.material_class.trim().toUpperCase(); else delete extra.material_class;
      return {
        ifc_type: d.ifc_type.trim(), work_item_code: d.work_item_code || null, default_category: d.default_category.trim() || null,
        quantity_source_preference: d.quantity_source_preference, unit_override: d.unit_override.trim() || null,
        confidence_base: Number(d.confidence_base || 0.85), extra_mapping: extra,
      };
    }));
    setDirty(false);
  }

  return (
    <TableShell>
      <table className="w-full min-w-[900px] text-left">
        <thead className={thead}><tr><th className={th}>IFC type</th><th className={th}>Work item</th><th className={th}>Category</th><th className={th}>Material class</th><th className={th}>Confidence</th><th className={th} /></tr></thead>
        <tbody>
          {drafts.map((d, i) => (
            <tr key={i} className="border-t border-[var(--color-border)]">
              <td className={td}><input disabled={!editable} className={inputClass} value={d.ifc_type} onChange={(e) => patch(i, { ifc_type: e.target.value })} placeholder="IfcColumn" /></td>
              <td className={td}>
                <select disabled={!editable} className={inputClass} value={d.work_item_code} onChange={(e) => patch(i, { work_item_code: e.target.value })}>
                  <option value="">None</option>
                  {workItems.map((w) => <option key={w.id} value={w.code}>{w.code} ({w.unit})</option>)}
                </select>
              </td>
              <td className={td}><input disabled={!editable} className={inputClass} value={d.default_category} onChange={(e) => patch(i, { default_category: e.target.value })} /></td>
              <td className={td}><input disabled={!editable} className={inputClass} value={d.material_class} onChange={(e) => patch(i, { material_class: e.target.value })} placeholder="CONCRETE" /></td>
              <td className={td}><input disabled={!editable} type="number" min="0" max="1" step="any" className={inputClass} value={d.confidence_base} onChange={(e) => patch(i, { confidence_base: e.target.value })} /></td>
              <td className={`${td} text-right`}>{editable ? <Button variant="ghost" size="sm" onClick={() => { setDrafts((c) => c.filter((_, x) => x !== i)); setDirty(true); }}>Remove</Button> : null}</td>
            </tr>
          ))}
          {drafts.length === 0 ? <tr><td colSpan={6} className="px-3 py-6 text-center text-[12.5px] text-[var(--color-text-muted)]">No mappings — base items get no work-item code.</td></tr> : null}
        </tbody>
      </table>
      <EditorFooter editable={editable} dirty={dirty} saving={saving} onSave={save}
        onAdd={() => { setDrafts((c) => [...c, { ifc_type: "", work_item_code: "", default_category: "", unit_override: "", confidence_base: "0.85", material_class: "", quantity_source_preference: "qto_first", extra_mapping: {} }]); setDirty(true); }} />
    </TableShell>
  );
}

export function ReinforcementRulesView({ rows }: { rows: ReinforcementRule[] }) {
  return (
    <TableShell>
      <table className="w-full min-w-[760px] text-left">
        <thead className={thead}><tr><th className={th}>Scope</th><th className={th}>Bar role</th><th className={th}>Lap</th><th className={th}>Hooks</th><th className={th}>Bends</th><th className={th}>Status</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.element_scope}:${r.bar_role}`} className="border-t border-[var(--color-border)] align-top text-[12.5px] text-[var(--color-text-secondary)]">
              <td className={td}>{r.element_scope}</td>
              <td className={`${td} font-semibold text-[var(--color-text-primary)]`}>{r.bar_role}</td>
              <td className={td}>{r.lap_basis ? `${r.lap_coefficient ?? "—"} × ${r.lap_basis.replace("_", " ")}` : "—"}</td>
              <td className={`${td} font-mono text-[11px]`}>{JSON.stringify(r.hook_rules)}</td>
              <td className={`${td} font-mono text-[11px]`}>{JSON.stringify(r.bend_rules)}</td>
              <td className={td}>{r.extra_config?.status === "CANDIDATE_UNCONFIRMED" ? <Badge tone="gold">Unconfirmed</Badge> : <Badge tone="green">Confirmed</Badge>}</td>
            </tr>
          ))}
          {rows.length === 0 ? <tr><td colSpan={6} className="px-3 py-6 text-center text-[12.5px] text-[var(--color-text-muted)]">No reinforcement rules.</td></tr> : null}
        </tbody>
      </table>
      <div className="border-t border-[var(--color-border)] px-3 py-3 text-[11.5px] text-[var(--color-text-secondary)]">Reinforcement values must be confirmed by a structural engineer. Editing arrives with the reinforcement phase; until then change them through the API.</div>
    </TableShell>
  );
}

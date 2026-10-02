import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass } from "../../../organizations/components/OrganizationUi";
import { useConventions } from "../hooks";
import type { RuleSet, RuleSetDraftUpdatePayload } from "../types/standards.types";

export function RuleSetSettingsForm({ ruleSet, editable, saving, onSave }: {
  ruleSet: RuleSet; editable: boolean; saving: boolean; onSave: (payload: RuleSetDraftUpdatePayload) => void;
}) {
  const conventionsQuery = useConventions();
  const [name, setName] = useState(ruleSet.name);
  const [description, setDescription] = useState(ruleSet.description ?? "");
  const [standardEdition, setStandardEdition] = useState(ruleSet.standard_edition ?? "");
  const [effectiveFrom, setEffectiveFrom] = useState(ruleSet.effective_from ?? "");
  const [effectiveTo, setEffectiveTo] = useState(ruleSet.effective_to ?? "");
  const [conventionCode, setConventionCode] = useState(ruleSet.convention_code ?? "");
  const [netVsGross, setNetVsGross] = useState<"net" | "gross">(ruleSet.net_vs_gross_preference === "gross" ? "gross" : "net");
  const [wallMethod, setWallMethod] = useState(ruleSet.wall_measurement_method);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: RuleSetDraftUpdatePayload = { name: name.trim(), net_vs_gross_preference: netVsGross, wall_measurement_method: wallMethod.trim() };
    if (description.trim()) payload.description = description.trim();
    if (standardEdition.trim()) payload.standard_edition = standardEdition.trim();
    if (effectiveFrom) payload.effective_from = effectiveFrom;
    if (effectiveTo) payload.effective_to = effectiveTo;
    if (conventionCode) payload.convention_code = conventionCode;
    onSave(payload);
  }

  return (
    <form onSubmit={submit} className="space-y-4 p-4">
      <Field label="Name"><input disabled={!editable} required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} /></Field>
      <Field label="Description"><input disabled={!editable} className={inputClass} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Standard edition"><input disabled={!editable} className={inputClass} value={standardEdition} onChange={(e) => setStandardEdition(e.target.value)} /></Field>
        <Field label="Measurement convention">
          <select disabled={!editable} className={inputClass} value={conventionCode} onChange={(e) => setConventionCode(e.target.value)}>
            <option value="">Not set</option>
            {(conventionsQuery.data ?? []).map((c) => <option key={c.code} value={c.code}>{c.name} ({c.code})</option>)}
          </select>
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Effective from"><input disabled={!editable} type="date" className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></Field>
        <Field label="Effective to"><input disabled={!editable} type="date" className={inputClass} value={effectiveTo} onChange={(e) => setEffectiveTo(e.target.value)} /></Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Contract quantity basis">
          <select disabled={!editable} className={inputClass} value={netVsGross} onChange={(e) => setNetVsGross(e.target.value as "net" | "gross")}>
            <option value="net">Net (waste shown separately)</option><option value="gross">Gross</option>
          </select>
        </Field>
        <Field label="Wall measurement method"><input disabled={!editable} className={inputClass} value={wallMethod} onChange={(e) => setWallMethod(e.target.value)} /></Field>
      </div>
      {editable ? (
        <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
          <Button type="submit" variant="primary" disabled={saving || !name.trim()}>{saving ? "Saving…" : "Save settings"}</Button>
        </div>
      ) : null}
    </form>
  );
}

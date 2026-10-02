import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useConventions, useCreateRuleSetDraft } from "../hooks";

export function RuleSetCreateForm({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const conventionsQuery = useConventions();
  const createDraft = useCreateRuleSetDraft();
  const { showToast } = useToast();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [jurisdiction, setJurisdiction] = useState("PK");
  const [province, setProvince] = useState("");
  const [standardName, setStandardName] = useState("");
  const [standardEdition, setStandardEdition] = useState("");
  const [conventionCode, setConventionCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createDraft.mutate(
      {
        code: code.trim().toUpperCase(), name: name.trim(),
        jurisdiction: jurisdiction.trim() || null, province: province.trim() || null,
        standard_name: standardName.trim() || null, standard_edition: standardEdition.trim() || null,
        convention_code: conventionCode || null,
      },
      {
        onSuccess: (detail) => { onClose(); onCreated(detail.rule_set.id); showToast({ tone: "success", title: "Draft rule set created" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't create this rule set.")),
      },
    );
  }

  return (
    <Modal title="New rule set" description="Starts as a draft. Add opening rules, wastage and mappings, then publish to freeze it. If the code already exists, this creates the next version." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Code"><input required className={inputClass} value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. LAHORE_CLIENT_A" /></Field>
          <Field label="Name"><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} /></Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Jurisdiction"><input className={inputClass} value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} /></Field>
          <Field label="Province"><input className={inputClass} value={province} onChange={(e) => setProvince(e.target.value)} placeholder="e.g. Punjab" /></Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Standard"><input className={inputClass} value={standardName} onChange={(e) => setStandardName(e.target.value)} placeholder="e.g. CSR" /></Field>
          <Field label="Edition"><input className={inputClass} value={standardEdition} onChange={(e) => setStandardEdition(e.target.value)} /></Field>
        </div>
        <Field label="Measurement convention">
          <select className={inputClass} value={conventionCode} onChange={(e) => setConventionCode(e.target.value)}>
            <option value="">Select later (required before publishing)</option>
            {(conventionsQuery.data ?? []).map((c) => <option key={c.code} value={c.code}>{c.name} ({c.code})</option>)}
          </select>
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createDraft.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createDraft.isPending || !code.trim() || !name.trim()}>{createDraft.isPending ? "Creating…" : "Create draft"}</Button>
        </div>
      </form>
    </Modal>
  );
}

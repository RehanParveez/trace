import { useState } from "react";
import { Badge, Button, ErrorState, Field, inputClass, LoadingState, Panel, PanelHeader, StatCard, TableShell } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useResolvedProfile } from "../hooks";
import { formatAreaRange, formatFactor, shortHash } from "../utils/standards.utils";

export function ResolvedProfilePanel() {
  const [codeInput, setCodeInput] = useState("");
  const [asOfInput, setAsOfInput] = useState("");
  const [query, setQuery] = useState({ code: "", asOf: "" });
  const profileQuery = useResolvedProfile(query.code, query.asOf);
  const profile = profileQuery.data;

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader eyebrow="WHAT THE ENGINE USES" title="Active profile" description="The exact rules a new calculation would use right now: your organisation's active rule set if you have one, otherwise the system profile." />
        <form className="grid gap-4 border-t border-[var(--color-border)] p-4 sm:grid-cols-3" onSubmit={(e) => { e.preventDefault(); setQuery({ code: codeInput.trim().toUpperCase(), asOf: asOfInput }); }}>
          <Field label="Rule set code (blank = default)"><input className={inputClass} value={codeInput} onChange={(e) => setCodeInput(e.target.value)} placeholder="PUNJAB_CSR" /></Field>
          <Field label="As of date"><input type="date" className={inputClass} value={asOfInput} onChange={(e) => setAsOfInput(e.target.value)} /></Field>
          <div className="flex items-end"><Button type="submit" variant="primary">Resolve</Button></div>
        </form>
      </Panel>

      {profileQuery.isLoading ? <LoadingState label="Resolving rules…" /> : null}
      {profileQuery.isError ? <ErrorState title="No active rule set found" description={getApiErrorMessage(profileQuery.error, "Run the standards seed or publish a rule set.")} onRetry={() => void profileQuery.refetch()} /> : null}

      {profile ? (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <StatCard label="Rule set" value={`${profile.code} v${profile.immutable_version}`} note={profile.convention_code ?? "No convention"} icon="check" tone="green" />
            <StatCard label="Opening rules" value={profile.opening_rules.length} note="Thresholds and behaviour" icon="budget" tone="blue" />
            <StatCard label="Wastage rules" value={profile.wastage_rules.length} note="By material class" icon="budget" tone="blue" />
            <StatCard label="Recipes" value={profile.recipes.length} note={`${profile.mappings.length} element mappings`} icon="budget" tone="blue" />
          </div>

          <Panel>
            <PanelHeader eyebrow="THRESHOLDS" title="Openings" description={`Content hash ${shortHash(profile.content_hash)}`} />
            <TableShell>
              <table className="w-full text-left">
                <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Scope</th><th className="px-4 py-3">Area</th><th className="px-4 py-3">Behaviour</th></tr></thead>
                <tbody>
                  {profile.opening_rules.map((r, i) => (
                    <tr key={i} className="border-t border-[var(--color-border)] text-[12.5px] text-[var(--color-text-secondary)]">
                      <td className="px-4 py-3">{r.element_scope}</td>
                      <td className="px-4 py-3">{formatAreaRange(r.lower_area_m2, r.upper_area_m2)}</td>
                      <td className="px-4 py-3"><Badge tone={r.behavior === "DEDUCT" ? "green" : r.behavior === "IGNORE" ? "slate" : "gold"}>{r.behavior}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="PROCUREMENT" title="Wastage" description="Applied to a separate gross quantity — contract quantities never carry waste." />
            <TableShell>
              <table className="w-full text-left">
                <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Material class</th><th className="px-4 py-3">Stage</th><th className="px-4 py-3">Extra</th></tr></thead>
                <tbody>
                  {profile.wastage_rules.map((r) => (
                    <tr key={`${r.material_class}:${r.procurement_stage}`} className="border-t border-[var(--color-border)] text-[12.5px] text-[var(--color-text-secondary)]">
                      <td className="px-4 py-3 font-semibold text-[var(--color-text-primary)]">{r.material_class}</td><td className="px-4 py-3">{r.procurement_stage}</td><td className="px-4 py-3 font-mono">{formatFactor(r.factor)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="DERIVED ITEMS" title="Recipes" />
            <div className="space-y-3 p-4">
              {profile.recipes.map((r) => (
                <div key={r.id} className="rounded-[8px] border border-[var(--color-border)] p-3">
                  <div className="text-[13px] font-semibold text-[var(--color-text-primary)]">{r.name} <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{r.code}</span></div>
                  <div className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">Triggers: {r.trigger_ifc_types.join(", ")}</div>
                  <div className="mt-2 flex flex-wrap gap-2">{r.components.map((c) => <Badge key={c.sequence} tone="slate">{c.formula_code} → {c.unit}</Badge>)}</div>
                </div>
              ))}
              {profile.recipes.length === 0 ? <p className="text-[12.5px] text-[var(--color-text-muted)]">No recipes in this profile.</p> : null}
            </div>
          </Panel>

          <details className="rounded-[8px] border border-[var(--color-border)] p-3">
            <summary className="cursor-pointer text-[12.5px] font-semibold text-[var(--color-text-primary)]">Full resolved profile (JSON)</summary>
            <pre className="mt-3 max-h-[420px] overflow-auto text-[11px] text-[var(--color-text-secondary)]">{JSON.stringify(profile, null, 2)}</pre>
          </details>
        </>
      ) : null}
    </div>
  );
}

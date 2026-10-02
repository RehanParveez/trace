import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, StatCard, TableShell, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useCloneRuleSet } from "../hooks";
import type { RuleSet } from "../types/standards.types";
import { formatRuleSetDate, formatRuleSetStatus, getRuleSetStatusTone } from "../utils/standards.utils";

export function RuleSetTable({ ruleSets, canManage, canPublish, onCreate, onOpen, onPublish }: {
  ruleSets: RuleSet[]; canManage: boolean; canPublish: boolean;
  onCreate: () => void; onOpen: (id: string) => void; onPublish: (ruleSet: RuleSet) => void;
}) {
  const cloneRuleSet = useCloneRuleSet();
  const { showToast } = useToast();

  const activeCount = ruleSets.filter((r) => r.status === "ACTIVE").length;
  const draftCount = ruleSets.filter((r) => r.status === "DRAFT").length;
  const systemCount = ruleSets.filter((r) => r.is_system && r.status === "ACTIVE").length;

  function clone(ruleSet: RuleSet) {
    cloneRuleSet.mutate(ruleSet.id, {
      onSuccess: (created) => { showToast({ tone: "success", title: "Draft version created" }); onOpen(created.rule_set.id); },
      onError: (e) => showToast({ tone: "error", title: "Couldn't clone this rule set", description: getApiErrorMessage(e, "Please try again.") }),
    });
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Active rule sets" value={activeCount} note="Used for new calculations" icon="check" tone="green" />
        <StatCard label="Drafts" value={draftCount} note="Editable, not yet published" icon="alert" tone={draftCount > 0 ? "gold" : "blue"} />
        <StatCard label="System profiles" value={systemCount} note="Read-only, clone to customise" icon="budget" tone="blue" />
      </div>

      <Panel>
        <PanelHeader eyebrow="STANDARDS" title="Rule sets" description="Versioned measurement rules. Published versions are frozen so past BOQs always trace back to the exact rules used." action={canManage ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />New rule set</Button> : null} />

        {ruleSets.length === 0 ? (
          <EmptyState icon="budget" title="No rule sets yet" description="Run the standards seed, or create a draft rule set." action={canManage ? <Button variant="primary" size="sm" onClick={onCreate}>New rule set</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[820px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Rule set</th><th className="px-4 py-3">Version</th><th className="px-4 py-3">Jurisdiction</th><th className="px-4 py-3">Published</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
              <tbody>
                {ruleSets.map((r) => (
                  <tr key={r.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5">
                      <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{r.name}</div>
                      <div className="font-mono text-[11px] text-[var(--color-text-muted)]">{r.code}{r.is_system ? " · system" : ""}</div>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[12.5px] text-[var(--color-text-secondary)]">v{r.immutable_version}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{[r.province, r.standard_name, r.standard_edition].filter(Boolean).join(" · ") || r.jurisdiction || "—"}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatRuleSetDate(r.published_at)}</td>
                    <td className="px-4 py-3.5"><Badge tone={getRuleSetStatusTone(r.status)}>{formatRuleSetStatus(r.status)}</Badge></td>
                    <td className="px-4 py-3.5 text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" size="sm" onClick={() => onOpen(r.id)}>Open</Button>
                        {canManage && r.status !== "ARCHIVED" ? <Button variant="ghost" size="sm" onClick={() => clone(r)} disabled={cloneRuleSet.isPending}>Clone</Button> : null}
                        {canPublish && r.status === "DRAFT" && !r.is_system ? <Button variant="primary" size="sm" onClick={() => onPublish(r)}>Publish</Button> : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>
    </div>
  );
}

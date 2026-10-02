import { useState } from "react";
import { Badge, Button, EmptyState, ErrorState, Icon, LoadingState, Panel, PanelHeader, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useCloneRuleSet, useDeleteRecipe, useRuleSet, useUpdateRuleSetDraft, useWorkItems } from "../hooks";
import type { Recipe, RuleSet, RuleSetDraftUpdatePayload } from "../types/standards.types";
import { formatRuleSetDate, formatRuleSetStatus, getRuleSetStatusTone, ruleSetLabel, shortHash } from "../utils/standards.utils";
import { RecipeDialog } from "./RecipeDialog";
import { MappingsEditor, OpeningRulesEditor, ReinforcementRulesView, WastageRulesEditor } from "./RuleSetRuleEditors";
import { RuleSetSettingsForm } from "./RuleSetSettingsForm";

type Tab = "openings" | "wastage" | "reinforcement" | "mappings" | "recipes" | "settings";
const TABS: Array<{ id: Tab; label: string }> = [
  { id: "openings", label: "Openings" }, { id: "wastage", label: "Wastage" }, { id: "reinforcement", label: "Reinforcement" },
  { id: "mappings", label: "Mappings" }, { id: "recipes", label: "Recipes" }, { id: "settings", label: "Settings" },
];

export function RuleSetDetailPanel({ ruleSetId, canManage, canPublish, onBack, onOpen, onPublish }: {
  ruleSetId: string; canManage: boolean; canPublish: boolean;
  onBack: () => void; onOpen: (id: string) => void; onPublish: (ruleSet: RuleSet) => void;
}) {
  const detailQuery = useRuleSet(ruleSetId);
  const workItemsQuery = useWorkItems();
  const updateDraft = useUpdateRuleSetDraft(ruleSetId);
  const deleteRecipe = useDeleteRecipe(ruleSetId);
  const cloneRuleSet = useCloneRuleSet();
  const { showToast } = useToast();
  const [tab, setTab] = useState<Tab>("openings");
  const [recipeDialog, setRecipeDialog] = useState<{ recipe: Recipe | null } | null>(null);

  if (detailQuery.isLoading) return <LoadingState label="Loading rule set…" />;
  if (detailQuery.isError || !detailQuery.data) return <ErrorState title="We couldn't load this rule set" onRetry={() => void detailQuery.refetch()} />;

  const detail = detailQuery.data;
  const rs = detail.rule_set;
  const workItems = (workItemsQuery.data ?? []).filter((w) => w.is_active);
  const editable = canManage && rs.status === "DRAFT" && !rs.is_system && rs.organization_id !== null;
  const mountKey = `${rs.id}:${rs.published_at ?? "draft"}`;

  function save(payload: RuleSetDraftUpdatePayload, title: string) {
    updateDraft.mutate(payload, {
      onSuccess: () => showToast({ tone: "success", title }),
      onError: (e) => showToast({ tone: "error", title: "Couldn't save changes", description: getApiErrorMessage(e, "Please check the values and try again.") }),
    });
  }

  function clone() {
    cloneRuleSet.mutate(rs.id, {
      onSuccess: (created) => { showToast({ tone: "success", title: "Draft version created" }); onOpen(created.rule_set.id); },
      onError: (e) => showToast({ tone: "error", title: "Couldn't clone this rule set", description: getApiErrorMessage(e, "Please try again.") }),
    });
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>← All rule sets</Button>
        <div className="flex gap-2">
          {canManage ? <Button variant="secondary" size="sm" onClick={clone} disabled={cloneRuleSet.isPending}>{cloneRuleSet.isPending ? "Cloning…" : rs.is_system ? "Clone to my organisation" : "Clone as new version"}</Button> : null}
          {canPublish && rs.status === "DRAFT" && !rs.is_system ? <Button variant="primary" size="sm" onClick={() => onPublish(rs)}>Validate &amp; publish</Button> : null}
        </div>
      </div>

      <Panel>
        <PanelHeader
          eyebrow={rs.is_system ? "SYSTEM RULE SET" : "RULE SET"}
          title={`${ruleSetLabel(rs.code, rs.immutable_version)} — ${rs.name}`}
          description={rs.status === "DRAFT" ? "Draft — editable until published." : "Published and frozen. Clone it to make changes."}
          action={<Badge tone={getRuleSetStatusTone(rs.status)}>{formatRuleSetStatus(rs.status)}</Badge>}
        />
        <dl className="grid gap-4 border-t border-[var(--color-border)] p-4 text-[12.5px] sm:grid-cols-4">
          <div><dt className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">Standard</dt><dd className="mt-1 text-[var(--color-text-primary)]">{[rs.standard_name, rs.standard_edition].filter(Boolean).join(" ") || "—"}</dd></div>
          <div><dt className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">Convention</dt><dd className="mt-1 font-mono text-[var(--color-text-primary)]">{rs.convention_code ?? "Not set"}</dd></div>
          <div><dt className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">Published</dt><dd className="mt-1 text-[var(--color-text-primary)]">{formatRuleSetDate(rs.published_at)}</dd></div>
          <div><dt className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">Content hash</dt><dd className="mt-1 font-mono text-[var(--color-text-primary)]">{shortHash(rs.content_hash)}</dd></div>
        </dl>
      </Panel>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t.id} type="button" onClick={() => setTab(t.id)}
            className={`rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${tab === t.id ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "openings" ? (
        <OpeningRulesEditor key={`o:${mountKey}`} rows={detail.opening_rules} editable={editable} saving={updateDraft.isPending} onSave={(rows) => save({ opening_rules: rows }, "Opening rules saved")} />
      ) : null}
      {tab === "wastage" ? (
        <WastageRulesEditor key={`w:${mountKey}`} rows={detail.wastage_rules} editable={editable} saving={updateDraft.isPending} onSave={(rows) => save({ wastage_rules: rows }, "Wastage rules saved")} />
      ) : null}
      {tab === "reinforcement" ? <ReinforcementRulesView rows={detail.reinforcement_rules} /> : null}
      {tab === "mappings" ? (
        <MappingsEditor key={`m:${mountKey}`} rows={detail.mappings} workItems={workItems} editable={editable} saving={updateDraft.isPending} onSave={(rows) => save({ mappings: rows }, "Mappings saved")} />
      ) : null}

      {tab === "recipes" ? (
        <Panel>
          <PanelHeader eyebrow="DERIVED WORK ITEMS" title="Assembly recipes" description="Extra items derived from a measured element. Units are fixed by the formula." action={editable ? <Button variant="primary" size="sm" onClick={() => setRecipeDialog({ recipe: null })}><Icon name="plus" size={13} />New recipe</Button> : null} />
          {detail.recipes.length === 0 ? (
            <EmptyState icon="budget" title="No recipes" description="This rule set derives no extra work items." />
          ) : (
            <div className="space-y-3 p-4">
              {detail.recipes.map((r) => (
                <div key={r.id} className="rounded-[8px] border border-[var(--color-border)] p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{r.name} <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{r.code}</span></div>
                      <div className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">Triggers: {r.trigger_ifc_types.join(", ")}</div>
                    </div>
                    {editable ? (
                      <div className="flex gap-2">
                        <Button variant="secondary" size="sm" onClick={() => setRecipeDialog({ recipe: r })}>Edit</Button>
                        <Button variant="danger" size="sm" onClick={() => { if (window.confirm(`Delete recipe ${r.code}?`)) deleteRecipe.mutate(r.id, { onError: (e) => showToast({ tone: "error", title: "Couldn't delete this recipe", description: getApiErrorMessage(e, "Please try again.") }) }); }}>Delete</Button>
                      </div>
                    ) : null}
                  </div>
                  <ul className="mt-2 space-y-1">
                    {[...r.components].sort((a, b) => a.sequence - b.sequence).map((c) => (
                      <li key={c.sequence} className="flex flex-wrap items-center gap-2 text-[12px] text-[var(--color-text-secondary)]">
                        <span className="font-mono text-[var(--color-text-muted)]">{c.sequence}.</span>
                        <span>{c.description_template}</span>
                        <Badge tone="slate">{c.quantity_formula_code}</Badge>
                        <Badge tone="blue">{c.output_unit}</Badge>
                        {c.is_optional ? <Badge tone="gold">optional</Badge> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Panel>
      ) : null}

      {tab === "settings" ? (
        <Panel>
          <RuleSetSettingsForm key={`s:${mountKey}`} ruleSet={rs} editable={editable} saving={updateDraft.isPending} onSave={(payload) => save(payload, "Settings saved")} />
        </Panel>
      ) : null}

      {recipeDialog ? <RecipeDialog ruleSetId={rs.id} recipe={recipeDialog.recipe} workItems={workItems} onClose={() => setRecipeDialog(null)} /> : null}
    </div>
  );
}

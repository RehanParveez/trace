import { useState } from "react";
import { ErrorState, LoadingState, PageHeader } from "../../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../../identity";
import { STANDARDS_PERMISSIONS } from "../permissions";
import { useRuleSets, useWorkItems } from "../hooks";
import type { RuleSet } from "../types/standards.types";
import { ResolvedProfilePanel } from "../components/ResolvedProfilePanel";
import { RuleSetCreateForm } from "../components/RuleSetCreateForm";
import { RuleSetDetailPanel } from "../components/RuleSetDetailPanel";
import { RuleSetPublishDialog } from "../components/RuleSetPublishDialog";
import { RuleSetTable } from "../components/RuleSetTable";
import { WorkItemForm } from "../components/WorkItemForm";
import { WorkItemTable } from "../components/WorkItemTable";

type Tab = "rule-sets" | "work-items" | "active";
const TABS: Array<{ id: Tab; label: string }> = [
  { id: "rule-sets", label: "Rule sets" }, { id: "work-items", label: "Work items" }, { id: "active", label: "Active profile" },
];

export function StandardsPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(STANDARDS_PERMISSIONS.DRAWING_READ);
  const canManage = permissions.includes(STANDARDS_PERMISSIONS.RULESET_MANAGE);
  const canPublish = permissions.includes(STANDARDS_PERMISSIONS.RULESET_PUBLISH);

  const ruleSetsQuery = useRuleSets();
  const workItemsQuery = useWorkItems();
  const [tab, setTab] = useState<Tab>("rule-sets");
  const [openId, setOpenId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [workItemFormOpen, setWorkItemFormOpen] = useState(false);
  const [publishing, setPublishing] = useState<RuleSet | null>(null);

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Standards unavailable" description="You don't have permission to view this." />;
  }
  if (ruleSetsQuery.isLoading) return <LoadingState label="Loading standards…" />;
  if (ruleSetsQuery.isError || !ruleSetsQuery.data) return <ErrorState title="We couldn't load standards" onRetry={() => void ruleSetsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title="Standards" description="Versioned measurement rules, the work-item catalog and recipes used to generate quantities." />

      {openId ? (
        <RuleSetDetailPanel
          ruleSetId={openId} canManage={canManage} canPublish={canPublish}
          onBack={() => setOpenId(null)} onOpen={setOpenId} onPublish={setPublishing}
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {TABS.map((t) => (
              <button key={t.id} type="button" onClick={() => setTab(t.id)}
                className={`rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${tab === t.id ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>
                {t.label}
              </button>
            ))}
          </div>

          {tab === "rule-sets" ? (
            <RuleSetTable ruleSets={ruleSetsQuery.data} canManage={canManage} canPublish={canPublish} onCreate={() => setCreateOpen(true)} onOpen={setOpenId} onPublish={setPublishing} />
          ) : null}
          {tab === "work-items" ? (
            workItemsQuery.isLoading ? <LoadingState label="Loading work items…" /> : (
              <WorkItemTable workItems={workItemsQuery.data ?? []} canManage={canManage} onCreate={() => setWorkItemFormOpen(true)} />
            )
          ) : null}
          {tab === "active" ? <ResolvedProfilePanel /> : null}
        </>
      )}

      {createOpen ? <RuleSetCreateForm onClose={() => setCreateOpen(false)} onCreated={(id) => { setTab("rule-sets"); setOpenId(id); }} /> : null}
      {workItemFormOpen ? <WorkItemForm onClose={() => setWorkItemFormOpen(false)} /> : null}
      {publishing ? <RuleSetPublishDialog ruleSet={publishing} onClose={() => setPublishing(null)} /> : null}
    </div>
  );
}

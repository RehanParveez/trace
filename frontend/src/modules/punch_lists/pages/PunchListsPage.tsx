import { useState } from "react";
import { ErrorState, Field, inputClass, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { PUNCH_LIST_PERMISSIONS } from "../permissions";
import { usePunchLists, usePunchListSummary } from "../hooks";
import { PunchListForm } from "../components/PunchListForm";
import { PunchListTable } from "../components/PunchListTable";
import { PunchListDetailPanel } from "../components/PunchListDetailPanel";

export function PunchListsPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(PUNCH_LIST_PERMISSIONS.PUNCH_LIST_READ);
  const canManage = permissions.includes(PUNCH_LIST_PERMISSIONS.PUNCH_LIST_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [viewingId, setViewingId] = useState<string | null>(null);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const punchListsQuery = usePunchLists(activeProjectId);
  const summaryQuery = usePunchListSummary(activeProjectId, { enabled: Boolean(activeProjectId) });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Punch lists unavailable" description="You don't have permission to view punch lists." />;
  }
  if (projectsQuery.isLoading) return <LoadingState label="Loading projects…" />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title="Punch lists" description="Formal snag / defect inspections at handover and at the end of the Defects Liability Period." />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first." />
      ) : (
        <>
          <Field label="Project">
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>

          {viewingId ? (
            <PunchListDetailPanel projectId={activeProjectId} punchListId={viewingId} canManage={canManage} />
          ) : punchListsQuery.isLoading ? (
            <LoadingState label="Loading punch lists…" />
          ) : (
            <PunchListTable
              punchLists={punchListsQuery.data ?? []}
              summary={summaryQuery.data}
              canCreate={canManage}
              onCreate={() => setFormOpen(true)}
              onView={setViewingId}
            />
          )}

          {viewingId ? (
            <button type="button" onClick={() => setViewingId(null)} className="text-[12.5px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline">← Back to all punch lists</button>
          ) : null}

          {formOpen && activeProjectId ? <PunchListForm projectId={activeProjectId} onClose={() => setFormOpen(false)} /> : null}
        </>
      )}
    </div>
  );
}
import { useState } from "react";
import { Button, ErrorState, Field, inputClass, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { MATERIAL_STOCK_PERMISSIONS } from "../permissions";
import { useMaterialReconciliation } from "../hooks";
import { MaterialIssueForm } from "../components/MaterialIssueForm";
import { MaterialReconciliationTable } from "../components/MaterialReconciliationTable";

export function MaterialStockPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(MATERIAL_STOCK_PERMISSIONS.MATERIAL_STOCK_READ);
  const canManage = permissions.includes(MATERIAL_STOCK_PERMISSIONS.MATERIAL_STOCK_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";
  const reconciliationQuery = useMaterialReconciliation(activeProjectId);

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Material stock unavailable" description="You don't have permission to view material stock." />;
  }
  if (projectsQuery.isLoading) return <LoadingState label="Loading projects…" />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title="Material stock" description="Track what's been received, issued to work, and lost to wastage — per project, per material." />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first." />
      ) : (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <Field label="Project">
              <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
            {canManage ? <Button variant="primary" onClick={() => setFormOpen(true)}>Record movement</Button> : null}
          </div>

          {reconciliationQuery.isLoading ? (
            <LoadingState label="Loading reconciliation…" />
          ) : reconciliationQuery.isError ? (
            <ErrorState title="Couldn't load reconciliation" onRetry={() => void reconciliationQuery.refetch()} />
          ) : (
            <MaterialReconciliationTable lines={reconciliationQuery.data?.lines ?? []} currency={reconciliationQuery.data?.currency ?? "PKR"} />
          )}

          {formOpen && activeProjectId ? <MaterialIssueForm projectId={activeProjectId} onClose={() => setFormOpen(false)} /> : null}
        </>
      )}
    </div>
  );
}
import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { RUNNING_BILL_PERMISSIONS } from "../permissions";
import { useRunningBills } from "../hooks";
import { RunningBillTable } from "../components/RunningBillTable";
import { RunningBillForm } from "../components/RunningBillForm";
import { RunningBillDetailDialog } from "../components/RunningBillDetailDialog";
import type { RunningBill } from "../types/running-bill.types";

export function RunningBillsPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(
    RUNNING_BILL_PERMISSIONS.RUNNING_BILL_READ,
  );
  const canCreate = permissions.includes(
    RUNNING_BILL_PERMISSIONS.RUNNING_BILL_CREATE,
  );
  const canIssue = permissions.includes(
    RUNNING_BILL_PERMISSIONS.RUNNING_BILL_ISSUE,
  );

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [viewingBill, setViewingBill] = useState<RunningBill | null>(null);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const billsQuery = useRunningBills(activeProjectId || undefined);

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title="Running bills unavailable"
        description="You don't have permission to view running bills."
      />
    );
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label="Loading projects…" />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return (
      <ErrorState
        title="We couldn't load projects"
        onRetry={() => void projectsQuery.refetch()}
      />
    );
  }

  return (
    <div className="space-y-7">
      <PageHeader
        title="Running bills"
        description="Client billing generated from approved progress claims — measured work, retention and net payable per project."
      />

      {projects.length === 0 ? (
        <ErrorState
          title="No projects yet"
          description="Create a project first to start billing against it."
        />
      ) : (
        <>
          <Field label="Project">
            <select
              className={inputClass}
              value={activeProjectId}
              onChange={(e) => setProjectId(e.target.value)}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </Field>

          {billsQuery.isLoading ? (
            <LoadingState label="Loading running bills…" />
          ) : billsQuery.isError ? (
            <ErrorState
              title="Couldn't load running bills"
              onRetry={() => void billsQuery.refetch()}
            />
          ) : (
            <RunningBillTable
              bills={billsQuery.data ?? []}
              canCreate={canCreate}
              onCreate={() => setFormOpen(true)}
              onView={setViewingBill}
            />
          )}

          {formOpen && activeProjectId ? (
            <RunningBillForm
              projectId={activeProjectId}
              onClose={() => setFormOpen(false)}
            />
          ) : null}

          {viewingBill ? (
            <RunningBillDetailDialog
              billId={viewingBill.id}
              canIssue={canIssue}
              onClose={() => setViewingBill(null)}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
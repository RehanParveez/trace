import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { PROCUREMENT_PERMISSIONS } from "../permissions";
import { useProcurementRequests } from "../hooks";
import { ProcurementTable } from "../components/ProcurementTable";
import { ProcurementForm } from "../components/ProcurementForm";

export function ProcurementPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_READ);
  const canCreate = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_CREATE);
  const canManage = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const requestsQuery = useProcurementRequests({ projectId: activeProjectId || undefined });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Procurement unavailable" description="You don't have permission to view procurement requests." />;
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label="Loading projects…" />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;
  }

  const requests = requestsQuery.data ?? [];
  const pendingCount = requests.filter((r) => r.status === "REQUESTED").length;
  const inFlightCount = requests.filter((r) => r.status === "APPROVED" || r.status === "ORDERED").length;
  const receivedCount = requests.filter((r) => r.status === "RECEIVED").length;

  return (
    <div className="space-y-7">
      <PageHeader title="Procurement" description="Material requests, approvals and receipts for each project." />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first to start requesting materials." />
      ) : (
        <>
          <Field label="Project">
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </Field>

          <section>
            <SectionDivider title="Procurement pulse" description="Current request pipeline for this project." />
            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard label="Awaiting approval" value={pendingCount} note="Requested, not yet approved" icon="mail" tone="gold" />
              <StatCard label="In progress" value={inFlightCount} note="Approved or ordered" icon="procurement" tone="blue" />
              <StatCard label="Received" value={receivedCount} note="Delivered to site" icon="check" tone="green" />
            </div>
          </section>

          <SectionDivider title="Requests" description={`${requests.length} request${requests.length === 1 ? "" : "s"} for this project.`} />

          {requestsQuery.isLoading ? (
            <LoadingState label="Loading procurement requests…" />
          ) : requestsQuery.isError ? (
            <ErrorState title="Couldn't load procurement requests" onRetry={() => void requestsQuery.refetch()} />
          ) : (
            <ProcurementTable
              requests={requests}
              canCreate={canCreate}
              canManage={canManage}
              onCreate={() => setFormOpen(true)}
            />
          )}

          {formOpen && activeProjectId ? (
            <ProcurementForm projectId={activeProjectId} onClose={() => setFormOpen(false)} />
          ) : null}
        </>
      )}
    </div>
  );
}
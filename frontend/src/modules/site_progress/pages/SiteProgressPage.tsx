import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { SITE_PROGRESS_PERMISSIONS } from "../permissions";
import { useSiteLogs } from "../hooks";
import { SiteLogTable } from "../components/SiteLogTable";
import { SiteLogForm } from "../components/SiteLogForm";

export function SiteProgressPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(SITE_PROGRESS_PERMISSIONS.SITE_LOG_READ);
  const canCreate = permissions.includes(SITE_PROGRESS_PERMISSIONS.SITE_LOG_CREATE);
  const canManage = permissions.includes(SITE_PROGRESS_PERMISSIONS.SITE_LOG_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const logsQuery = useSiteLogs({ projectId: activeProjectId || undefined });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Site progress unavailable" description="You don't have permission to view site progress logs." />;
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label="Loading projects…" />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;
  }

  const logs = logsQuery.data ?? [];
  const latestWorkforce = logs[0]?.workforce_count ?? null;

  return (
    <div className="space-y-7">
      <PageHeader title="Site progress" description="Daily field reports capturing workforce, weather and blockers for each project." />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first to start logging site progress." />
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
            <SectionDivider title="Latest snapshot" description="Most recent reported figures for this project." />
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <StatCard label="Logs recorded" value={logs.length} note="Total site logs" icon="site" tone="blue" />
              <StatCard label="Latest workforce" value={latestWorkforce ?? "—"} note="Reported on last log" icon="users" tone="gold" />
              <StatCard
                label="Latest report"
                value={logs[0] ? "Filed" : "None yet"}
                note={logs[0] ? "Most recent log entry" : "No logs recorded yet"}
                icon="clock"
                tone={logs[0] ? "green" : "gold"}
              />
            </div>
          </section>

          <SectionDivider title="Site log history" description={`${logs.length} log${logs.length === 1 ? "" : "s"} recorded for this project.`} />

          {logsQuery.isLoading ? (
            <LoadingState label="Loading site logs…" />
          ) : logsQuery.isError ? (
            <ErrorState title="Couldn't load site logs" onRetry={() => void logsQuery.refetch()} />
          ) : (
            <SiteLogTable
              logs={logs}
              canCreate={canCreate}
              canManage={canManage}
              onCreate={() => setFormOpen(true)}
            />
          )}

          {formOpen && activeProjectId ? (
            <SiteLogForm projectId={activeProjectId} onClose={() => setFormOpen(false)} />
          ) : null}
        </>
      )}
    </div>
  );
}
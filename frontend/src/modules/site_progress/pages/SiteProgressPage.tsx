import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { SITE_PROGRESS_PERMISSIONS } from "../permissions";
import { useSiteLogs } from "../hooks";
import { SiteLogTable } from "../components/SiteLogTable";
import { SiteLogForm } from "../components/SiteLogForm";
import { useTranslation } from "react-i18next";

export function SiteProgressPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(SITE_PROGRESS_PERMISSIONS.SITE_LOG_READ);
  const { t } = useTranslation();
  const canCreate = permissions.includes(SITE_PROGRESS_PERMISSIONS.SITE_LOG_CREATE);
  const canManage = permissions.includes(SITE_PROGRESS_PERMISSIONS.SITE_LOG_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const logsQuery = useSiteLogs({ projectId: activeProjectId || undefined });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("siteProgress.page.accessUnavailable")} description={t("siteProgress.page.accessUnavailableDesc")} />;
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label={t("common.loading")} />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title={t("projects.page.loadError")} onRetry={() => void projectsQuery.refetch()} />;
  }

  const logs = logsQuery.data ?? [];
  const latestWorkforce = logs[0]?.workforce_count ?? null;

  return (
    <div className="space-y-7">
      <PageHeader title={t("siteProgress.page.title")} description={t("siteProgress.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("siteProgress.page.noProjects")} description={t("siteProgress.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("siteProgress.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </Field>

          <section>
            <SectionDivider title={t("siteProgress.page.snapshotTitle")} description={t("siteProgress.page.snapshotDesc")} />
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <StatCard label={t("siteProgress.page.logsRecorded")} value={logs.length} note={t("siteProgress.page.logsRecordedNote")} icon="site" tone="blue" />
              <StatCard label={t("siteProgress.page.latestWorkforce")} value={latestWorkforce ?? "—"} note={t("siteProgress.page.latestWorkforceNote")} icon="users" tone="gold" />
              <StatCard
                label={t("siteProgress.page.latestReport")}
                value={logs[0] ? t("siteProgress.page.filed") : t("siteProgress.page.noneYet")}
                note={logs[0] ? "Most recent log entry" : t("siteProgress.page.noneYet")}
                icon="clock"
                tone={logs[0] ? "green" : "gold"}
              />
            </div>
          </section>

          <SectionDivider title={t("siteProgress.page.historyTitle")} description={t("siteProgress.page.historyDesc", { count: logs.length })} />

          {logsQuery.isLoading ? (
            <LoadingState label={t("siteProgress.page.loadingLogs")} />
          ) : logsQuery.isError ? (
            <ErrorState title={t("siteProgress.page.loadError")} onRetry={() => void logsQuery.refetch()} />
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
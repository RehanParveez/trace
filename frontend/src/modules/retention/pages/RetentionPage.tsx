import { useState } from "react";
import { ErrorState, Field, inputClass, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { RETENTION_PERMISSIONS } from "../permissions";
import { ProjectRetentionPanel } from "../components/ProjectRetentionPanel";
import { useTranslation } from "react-i18next";

export function RetentionPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(RETENTION_PERMISSIONS.RETENTION_READ);
  const canManage = permissions.includes(RETENTION_PERMISSIONS.RETENTION_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("retention.page.accessUnavailable")} description={t("retention.page.accessUnavailableDesc")} />;
  }
  if (projectsQuery.isLoading) return <LoadingState label={t("retention.page.loadingProjects")} />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title={t("retention.page.loadProjectsError")} onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title={t("retention.page.title")} description={t("retention.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("retention.page.noProjects")} description={t("retention.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("retention.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>

          <ProjectRetentionPanel projectId={activeProjectId} canManage={canManage} />
        </>
      )}
    </div>
  );
}
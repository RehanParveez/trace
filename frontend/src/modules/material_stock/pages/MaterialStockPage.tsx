import { useState } from "react";
import { Button, ErrorState, Field, inputClass, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { MATERIAL_STOCK_PERMISSIONS } from "../permissions";
import { useMaterialReconciliation } from "../hooks";
import { MaterialIssueForm } from "../components/MaterialIssueForm";
import { MaterialReconciliationTable } from "../components/MaterialReconciliationTable";
import { useTranslation } from "react-i18next";

export function MaterialStockPage() {
  const { t } = useTranslation();
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
    return <ErrorState title={t("materialStock.page.accessUnavailable")} description={t("materialStock.page.accessUnavailableDesc")} />;
  }
  if (projectsQuery.isLoading) return <LoadingState label={t("materialStock.page.loadingProjects")} />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title={t("materialStock.page.loadProjectsError")} onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title={t("materialStock.page.title")} description={t("materialStock.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("materialStock.page.noProjects")} description={t("materialStock.page.noProjectsDesc")} />
      ) : (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <Field label={t("materialStock.page.project")}>
              <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
            {canManage ? <Button variant="primary" onClick={() => setFormOpen(true)}>{t("materialStock.page.recordMovement")}</Button> : null}
          </div>

          {reconciliationQuery.isLoading ? (
            <LoadingState label={t("materialStock.page.loadingRecon")} />
          ) : reconciliationQuery.isError ? (
            <ErrorState title={t("materialStock.page.loadReconError")} onRetry={() => void reconciliationQuery.refetch()} />
          ) : (
            <MaterialReconciliationTable lines={reconciliationQuery.data?.lines ?? []} currency={reconciliationQuery.data?.currency ?? "PKR"} />
          )}

          {formOpen && activeProjectId ? <MaterialIssueForm projectId={activeProjectId} onClose={() => setFormOpen(false)} /> : null}
        </>
      )}
    </div>
  );
}
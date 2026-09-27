import { useState } from "react";
import { ErrorState, Field, inputClass, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { BANK_GUARANTEE_PERMISSIONS } from "../permissions";
import { useBankGuarantees, useBankGuaranteeSummary } from "../hooks/index.ts";
import { BankGuaranteeForm } from "../components/BankGuaranteeForm";
import { BankGuaranteeTable } from "../components/BankGuaranteeTable";
import { useTranslation } from "react-i18next";

export function BankGuaranteesPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(BANK_GUARANTEE_PERMISSIONS.BANK_GUARANTEE_READ);
  const canManage = permissions.includes(BANK_GUARANTEE_PERMISSIONS.BANK_GUARANTEE_MANAGE);
  const canRelease = permissions.includes(BANK_GUARANTEE_PERMISSIONS.BANK_GUARANTEE_RELEASE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const guaranteesQuery = useBankGuarantees(activeProjectId);
  const summaryQuery = useBankGuaranteeSummary(activeProjectId, { enabled: Boolean(activeProjectId) });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("bankGuarantees.page.accessUnavailable")} description={t("bankGuarantees.page.accessUnavailableDesc")}/>;
  }
  if (projectsQuery.isLoading) return <LoadingState label={t("bankGuarantees.page.loadingProjects")} />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title={t("bankGuarantees.page.loadProjectsError")} onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title={t("bankGuarantees.page.title")} description={t("bankGuarantees.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("bankGuarantees.page.noProjects")} description={t("bankGuarantees.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("bankGuarantees.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>

          {guaranteesQuery.isLoading ? (
            <LoadingState label={t("bankGuarantees.page.loadingGuarantees")} />
          ) : (
            <BankGuaranteeTable
              projectId={activeProjectId}
              guarantees={guaranteesQuery.data ?? []}
              summary={summaryQuery.data}
              canManage={canManage}
              canRelease={canRelease}
              onCreate={() => setFormOpen(true)}
            />
          )}

          {formOpen && activeProjectId ? <BankGuaranteeForm projectId={activeProjectId} onClose={() => setFormOpen(false)} /> : null}
        </>
      )}
    </div>
  );
}
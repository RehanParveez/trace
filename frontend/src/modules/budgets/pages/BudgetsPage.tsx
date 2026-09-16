import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader,
} from "../../organizations/components/OrganizationUi";
import { useProjects, ProjectCombobox, } from "../../projects";
import { usePermissionKeys, IDENTITY_PERMISSIONS } from "../../identity";
import { useProjectBudget } from "../hooks";
import { BudgetOverview } from "../components/BudgetOverview";
import { BudgetForm } from "../components/BudgetForm";
import { useTranslation } from "react-i18next";

export function BudgetsPage() {
  const permissions = usePermissionKeys();
  const { t } = useTranslation();
  const canRead = permissions.includes(IDENTITY_PERMISSIONS.BUDGET_READ);
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.BUDGET_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const budgetQuery = useProjectBudget(activeProjectId || undefined);

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title={t("budgets.page.accessUnavailable")}
        description={t("budgets.page.accessUnavailableDesc")}
      />
    );
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label={t("common.loading")} />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title={t("projects.page.loadError")} onRetry={() => void projectsQuery.refetch()} />;
  }

  return (
    <div className="space-y-7">
      <PageHeader title={t("budgets.page.title")} description={t("budgets.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("budgets.page.noProjects")} description={t("budgets.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("budgets.page.project")}>
            <ProjectCombobox
              projects={projects}
              value={activeProjectId}
              onChange={setProjectId}
            />
          </Field>

          {budgetQuery.isLoading ? (
            <LoadingState label={t("budgets.page.loadingBudget")} />
          ) : budgetQuery.isError ? (
            <ErrorState title={t("budgets.page.loadError")} onRetry={() => void budgetQuery.refetch()} />
          ) : (
            <BudgetOverview
              budget={budgetQuery.data ?? null}
              canManage={canManage}
              onEdit={() => setFormOpen(true)}
            />
          )}

          {formOpen && activeProjectId ? (
            <BudgetForm
              projectId={activeProjectId}
              budget={budgetQuery.data ?? null}
              onClose={() => setFormOpen(false)}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
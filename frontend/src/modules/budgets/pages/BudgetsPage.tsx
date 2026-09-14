import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { BUDGET_PERMISSIONS } from "../permissions";
import { useProjectBudget } from "../hooks";
import { BudgetOverview } from "../components/BudgetOverview";
import { BudgetForm } from "../components/BudgetForm";
import { useTranslation } from "react-i18next";

export function BudgetsPage() {
  const permissions = usePermissionKeys();
  const { t } = useTranslation();
  const canRead = permissions.includes(BUDGET_PERMISSIONS.BUDGET_READ);
  const canManage = permissions.includes(BUDGET_PERMISSIONS.BUDGET_MANAGE);

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
            <select
              className={inputClass}
              value={activeProjectId}
              onChange={(event) => setProjectId(event.target.value)}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
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
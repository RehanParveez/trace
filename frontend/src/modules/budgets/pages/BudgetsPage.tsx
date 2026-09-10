import { useState } from "react";
import {
  ErrorState, Field, inputClass, LoadingState, PageHeader,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { BUDGET_PERMISSIONS } from "../permissions";
import { useProjectBudget } from "../hooks";
import { BudgetOverview } from "../components/BudgetOverview";
import { BudgetForm } from "../components/BudgetForm";

export function BudgetsPage() {
  const permissions = usePermissionKeys();
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
        title="Budget access unavailable"
        description="You don't have permission to view project budgets."
      />
    );
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label="Loading projects…" />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;
  }

  return (
    <div className="space-y-7">
      <PageHeader title="Budgets" description="Approved budget and category allocation for each project." />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first to set its approved budget." />
      ) : (
        <>
          <Field label="Project">
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
            <LoadingState label="Loading budget…" />
          ) : budgetQuery.isError ? (
            <ErrorState title="Couldn't load this project's budget" onRetry={() => void budgetQuery.refetch()} />
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
import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { EXPENSE_PERMISSIONS } from "../permissions";
import { useExpenses } from "../hooks";
import { ExpenseTable } from "../components/ExpenseTable";
import { ExpenseForm } from "../components/ExpenseForm";
import { formatExpenseAmount } from "../utils/expense.utils";
import { useTranslation } from "react-i18next";

export function ExpensesPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_READ);
  const canCreate = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_CREATE);
  const canApprove = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_APPROVE);
  const { t } = useTranslation();


  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const expensesQuery = useExpenses({ projectId: activeProjectId || undefined });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("expenses.page.accessUnavailable")} description={t("expenses.page.accessUnavailableDesc")} />;
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label={t("common.loading")} />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title={t("projects.page.loadError")} onRetry={() => void projectsQuery.refetch()} />;
  }

  const expenses = expensesQuery.data ?? [];
  const pendingTotal = expenses.filter((e) => e.status === "PENDING").reduce((sum, e) => sum + Number(e.amount), 0);
  const approvedTotal = expenses.filter((e) => e.status === "APPROVED").reduce((sum, e) => sum + Number(e.amount), 0);

  return (
    <div className="space-y-7">
      <PageHeader title={t("expenses.page.title")} description={t("expenses.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("expenses.page.noProjects")} description={t("expenses.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("expenses.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </Field>

          <section>
            <SectionDivider title={t("expenses.page.pulseTitle")} description={t("expenses.page.pulseDesc")} />
            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard label={t("expenses.page.recorded")} value={expenses.length} note={t("expenses.page.recordedNote")} icon="expenses" tone="blue" />
              <StatCard label={t("expenses.page.pending")} value={formatExpenseAmount(pendingTotal)} note={t("expenses.page.pendingNote")} icon="mail" tone="gold" />
              <StatCard label={t("expenses.page.approved")} value={formatExpenseAmount(approvedTotal)} note={t("expenses.page.approvedNote")} icon="check" tone="green" />
            </div>
          </section>

          <SectionDivider title={t("expenses.page.entriesTitle")} description={t("expenses.page.entriesDesc", { count: expenses.length })} />

          {expensesQuery.isLoading ? (
            <LoadingState label={t("expenses.page.loading")} />
          ) : expensesQuery.isError ? (
            <ErrorState title={t("expenses.page.loadError")} onRetry={() => void expensesQuery.refetch()} />
          ) : (
            <ExpenseTable
              expenses={expenses}
              canCreate={canCreate}
              canApprove={canApprove}
              onCreate={() => setFormOpen(true)}
            />
          )}

          {formOpen && activeProjectId ? (
            <ExpenseForm projectId={activeProjectId} onClose={() => setFormOpen(false)} />
          ) : null}
        </>
      )}
    </div>
  );
}
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

export function ExpensesPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_READ);
  const canCreate = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_CREATE);
  const canApprove = permissions.includes(EXPENSE_PERMISSIONS.EXPENSE_APPROVE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const expensesQuery = useExpenses({ projectId: activeProjectId || undefined });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Expenses unavailable" description="You don't have permission to view project expenses." />;
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label="Loading projects…" />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;
  }

  const expenses = expensesQuery.data ?? [];
  const pendingTotal = expenses.filter((e) => e.status === "PENDING").reduce((sum, e) => sum + Number(e.amount), 0);
  const approvedTotal = expenses.filter((e) => e.status === "APPROVED").reduce((sum, e) => sum + Number(e.amount), 0);

  return (
    <div className="space-y-7">
      <PageHeader title="Expenses" description="Costs logged and approved against each project." />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first to start recording expenses." />
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
            <SectionDivider title="Expense pulse" description="Current spend for this project." />
            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard label="Recorded" value={expenses.length} note="Total expense entries" icon="expenses" tone="blue" />
              <StatCard label="Pending" value={formatExpenseAmount(pendingTotal)} note="Awaiting approval" icon="mail" tone="gold" />
              <StatCard label="Approved" value={formatExpenseAmount(approvedTotal)} note="Confirmed project spend" icon="check" tone="green" />
            </div>
          </section>

          <SectionDivider title="Expense entries" description={`${expenses.length} entr${expenses.length === 1 ? "y" : "ies"} for this project.`} />

          {expensesQuery.isLoading ? (
            <LoadingState label="Loading expenses…" />
          ) : expensesQuery.isError ? (
            <ErrorState title="Couldn't load expenses" onRetry={() => void expensesQuery.refetch()} />
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
import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { RUNNING_BILL_PERMISSIONS } from "../permissions";
import { useRunningBills } from "../hooks";
import { RunningBillTable } from "../components/RunningBillTable";
import { RunningBillForm } from "../components/RunningBillForm";
import { RunningBillDetailDialog } from "../components/RunningBillDetailDialog";
import type { RunningBill } from "../types/running-bill.types";
import { useTranslation } from "react-i18next";

export function RunningBillsPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(
    RUNNING_BILL_PERMISSIONS.RUNNING_BILL_READ,
  );
  const canCreate = permissions.includes(
    RUNNING_BILL_PERMISSIONS.RUNNING_BILL_CREATE,
  );
  const canIssue = permissions.includes(
    RUNNING_BILL_PERMISSIONS.RUNNING_BILL_ISSUE,
  );

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [viewingBill, setViewingBill] = useState<RunningBill | null>(null);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const billsQuery = useRunningBills(activeProjectId || undefined);

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title={t("runningBills.page.accessUnavailable")}
        description={t("runningBills.page.accessUnavailableDesc")}
      />
    );
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label={t("runningBills.page.loadingProjects")} />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return (
      <ErrorState
        title={t("runningBills.page.loadProjectsError")}
        onRetry={() => void projectsQuery.refetch()}
      />
    );
  }

  return (
    <div className="space-y-7">
      <PageHeader
        title={t("runningBills.page.title")}
        description={t("runningBills.page.description")}
      />

      {projects.length === 0 ? (
        <ErrorState
          title={t("runningBills.page.noProjects")}
          description={t("runningBills.page.noProjectsDesc")}
        />
      ) : (
        <>
          <Field label={t("runningBills.page.project")}>
            <select
              className={inputClass}
              value={activeProjectId}
              onChange={(e) => setProjectId(e.target.value)}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </Field>

          {billsQuery.isLoading ? (
            <LoadingState label={t("runningBills.page.loadingBills")} />
          ) : billsQuery.isError ? (
            <ErrorState
              title={t("runningBills.page.loadBillsError")}
              onRetry={() => void billsQuery.refetch()}
            />
          ) : (
            <RunningBillTable
              bills={billsQuery.data ?? []}
              canCreate={canCreate}
              onCreate={() => setFormOpen(true)}
              onView={setViewingBill}
            />
          )}

          {formOpen && activeProjectId ? (
            <RunningBillForm
              projectId={activeProjectId}
              onClose={() => setFormOpen(false)}
            />
          ) : null}

          {viewingBill ? (
            <RunningBillDetailDialog
              billId={viewingBill.id}
              canIssue={canIssue}
              onClose={() => setViewingBill(null)}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
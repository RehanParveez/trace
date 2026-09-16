import { useState } from "react";
import {ErrorState, Field, inputClass, LoadingState, PageHeader, SectionDivider, StatCard, Pager,
} from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { PROCUREMENT_PERMISSIONS } from "../permissions";
import { useProcurementRequests, useProcurementStatusSummary } from "../hooks";
import { ProcurementTable } from "../components/ProcurementTable";
import { ProcurementForm } from "../components/ProcurementForm";
import { useTranslation } from "react-i18next";

const PROCUREMENT_PAGE_SIZE = 20;

export function ProcurementPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_READ);
  const canCreate = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_CREATE);
  const canManage = permissions.includes(PROCUREMENT_PERMISSIONS.PROCUREMENT_MANAGE);

  const projectsQuery = useProjects();
  const { t } = useTranslation();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [page, setPage] = useState(0);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const requestsQuery = useProcurementRequests({
    projectId: activeProjectId || undefined,
    page: page + 1,
    pageSize: PROCUREMENT_PAGE_SIZE,
  });
  const statusSummaryQuery = useProcurementStatusSummary(
    activeProjectId || undefined);

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("procurement.page.accessUnavailable")} description={t("procurement.page.accessUnavailableDesc")} />;
  }

  if (projectsQuery.isLoading) {
    return <LoadingState label={t("common.loading")} />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <ErrorState title={t("projects.page.loadError")} onRetry={() => void projectsQuery.refetch()} />;
  }

  const requests = requestsQuery.data?.items ?? [];
  const totalRequests = requestsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalRequests / PROCUREMENT_PAGE_SIZE));
  const statusCounts = statusSummaryQuery.data?.counts ?? {};
  const pendingCount = statusCounts.REQUESTED ?? 0;
  const inFlightCount = (statusCounts.APPROVED ?? 0) + (statusCounts.ORDERED ?? 0);
  const receivedCount = statusCounts.RECEIVED ?? 0;

  return (
    <div className="space-y-7">
      <PageHeader title={t("procurement.page.title")} description={t("procurement.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("procurement.page.noProjects")} description={t("procurement.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("procurement.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => {setProjectId(e.target.value); setPage(0);}}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </Field>

          <section>
            <SectionDivider title={t("procurement.page.pulseTitle")} description={t("procurement.page.pulseDesc")} />
            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard label={t("procurement.page.awaiting")} value={pendingCount} note={t("procurement.page.awaitingNote")} icon="mail" tone="gold" />
              <StatCard label={t("procurement.page.inProgress")} value={inFlightCount} note={t("procurement.page.inProgressNote")} icon="procurement" tone="blue" />
              <StatCard label={t("procurement.page.received")} value={receivedCount} note={t("procurement.page.receivedNote")} icon="check" tone="green" />
            </div>
          </section>

          <SectionDivider title={t("procurement.page.requestsTitle")} description={t("procurement.page.requestsDesc", { count: totalRequests })} />

          {requestsQuery.isLoading ? (
            <LoadingState label="Loading procurement requests…" />
          ) : requestsQuery.isError ? (
            <ErrorState title={t("procurement.page.loadError")} onRetry={() => void requestsQuery.refetch()} />
          ) : (
           <>
           <ProcurementTable
              requests={requests}
              canCreate={canCreate}
              canManage={canManage}
              onCreate={() => setFormOpen(true)}
            />

            {totalRequests > 0 ? (
             <Pager
              page={page}
              totalPages={totalPages}
              totalItems={totalRequests}
              onPrevious={() => setPage((current) => Math.max(0, current - 1))}
              onNext={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
             />
            ) : null}
           </>
          )}
          {formOpen && activeProjectId ? (
            <ProcurementForm projectId={activeProjectId} onClose={() => setFormOpen(false)} />
          ) : null}
        </>
      )}
    </div>
  );
}
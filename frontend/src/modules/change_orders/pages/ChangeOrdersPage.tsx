import { useState } from "react";
import { ErrorState, Field, inputClass, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { CHANGE_ORDER_PERMISSIONS } from "../permissions";
import { useChangeOrders, useChangeOrderSummary } from "../hooks";
import { ChangeOrderForm } from "../components/ChangeOrderForm";
import { ChangeOrderTable } from "../components/ChangeOrderTable";
import { ChangeOrderDetailDialog } from "../components/ChangeOrderDetailDialog";
import type { ChangeOrder } from "../types/change-order.types";
import { useTranslation } from "react-i18next";

export function ChangeOrdersPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(CHANGE_ORDER_PERMISSIONS.CHANGE_ORDER_READ);
  const canCreate = permissions.includes(CHANGE_ORDER_PERMISSIONS.CHANGE_ORDER_CREATE);
  const canApprove = permissions.includes(CHANGE_ORDER_PERMISSIONS.CHANGE_ORDER_APPROVE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [viewingId, setViewingId] = useState<string | null>(null);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const changeOrdersQuery = useChangeOrders(activeProjectId);
  const summaryQuery = useChangeOrderSummary(activeProjectId, { enabled: Boolean(activeProjectId) });

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("changeOrders.page.accessUnavailable")} description={t("changeOrders.page.accessUnavailableDesc")} />;
  }
  if (projectsQuery.isLoading) return <LoadingState label={t("changeOrders.page.loadingProjects")} />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title={t("changeOrders.page.loadProjectsError")} onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title={t("changeOrders.page.title")} description={t("changeOrders.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("changeOrders.page.noProjects")} description={t("changeOrders.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("changeOrders.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>

          {changeOrdersQuery.isLoading ? (
            <LoadingState label={t("changeOrders.page.loading")} />
          ) : (
            <ChangeOrderTable
              changeOrders={changeOrdersQuery.data ?? []}
              summary={summaryQuery.data}
              canCreate={canCreate}
              onCreate={() => setFormOpen(true)}
              onView={(co: ChangeOrder) => setViewingId(co.id)}
            />
          )}

          {formOpen && activeProjectId ? <ChangeOrderForm projectId={activeProjectId} onClose={() => setFormOpen(false)} /> : null}
          {viewingId ? <ChangeOrderDetailDialog projectId={activeProjectId} changeOrderId={viewingId} canApprove={canApprove} onClose={() => setViewingId(null)} /> : null}
        </>
      )}
    </div>
  );
}
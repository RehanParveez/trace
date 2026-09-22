import { useState } from "react";
import { ErrorState, Field, inputClass, LoadingState, PageHeader, StatCard } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { LABOUR_PERMISSIONS } from "../permissions";
import { useLabourSummary } from "../hooks";
import { LabourRosterPanel } from "../components/LabourRosterPanel";
import { LabourAttendanceSheet } from "../components/LabourAttendanceSheet";
import { LabourDeploymentDialog } from "../components/LabourDeploymentDialog";
import { LabourFinancePanel } from "../components/LabourFinancePanel";
import { formatLabourMoney } from "../utils/labour.utils";
import { useTranslation } from "react-i18next";

const TABS = ["Roster", "Attendance", "Finance"] as const;

export function LabourPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(LABOUR_PERMISSIONS.LABOUR_READ);
  const canManage = permissions.includes(LABOUR_PERMISSIONS.LABOUR_MANAGE);
  const canManagePayments = permissions.includes(LABOUR_PERMISSIONS.LABOUR_PAYMENT_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [tab, setTab] = useState<typeof TABS[number]>("Attendance");
  const [deployOpen, setDeployOpen] = useState(false);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";

  const monthStart = new Date();
  monthStart.setDate(1);
  const periodStart = monthStart.toISOString().slice(0, 10);
  const periodEnd = new Date().toISOString().slice(0, 10);
  const summaryQuery = useLabourSummary(activeProjectId, periodStart, periodEnd, { enabled: canRead && Boolean(activeProjectId) });

  if (!canRead && permissions.length > 0) {
    return <ErrorState  title={t("labour.page.accessUnavailable")} description={t("labour.page.accessUnavailableDescription")} />;
  }

  if (projectsQuery.isLoading) return <LoadingState label={t("labour.page.loadingProjects")} />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title={t("labour.page.projectsLoadError")} onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title={t("labour.page.title")} description={t("labour.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("labour.page.noProjectsTitle")} description={t("labour.page.noProjectsDescription")} />
      ) : (
        <>
          <Field label={t("labour.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
            </select>
          </Field>

          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label={t("labour.page.costThisMonth")} value={summaryQuery.data ? formatLabourMoney(summaryQuery.data.total_accrued_cost, summaryQuery.data.currency) : "…"} note={t("labour.page.accruedFromAttendance")} icon="budget" tone="gold" />
            <StatCard label={t("labour.page.advancesGiven")} value={summaryQuery.data ? formatLabourMoney(summaryQuery.data.total_advances_given, summaryQuery.data.currency) : "…"} note={t("labour.page.totalThisProject")} icon="expenses" tone="blue" />
            <StatCard label={t("labour.page.outstandingBalance")} value={summaryQuery.data ? formatLabourMoney(summaryQuery.data.outstanding_advance_balance, summaryQuery.data.currency) : "…"} note={t("labour.page.advancesNotRecovered")} icon="alert" tone={Number(summaryQuery.data?.outstanding_advance_balance ?? 0) > 0 ? "gold" : "green"} />
          </div>

          <div className="flex gap-2 border-b border-[var(--color-border)]">
            {TABS.map((t) => (
              <button key={t} type="button" onClick={() => setTab(t)} className={`px-3 py-2 text-[13px] font-semibold ${tab === t ? "border-b-2 border-[var(--color-trace-gold)] text-[var(--color-text-primary)]" : "text-[var(--color-text-secondary)]"}`}>
                {t}
              </button>
            ))}
          </div>

          {tab === "Roster" ? <LabourRosterPanel canManage={canManage} /> : null}
          {tab === "Attendance" ? <LabourAttendanceSheet projectId={activeProjectId} canManage={canManage} onDeploy={() => setDeployOpen(true)} /> : null}
          {tab === "Finance" ? <LabourFinancePanel projectId={activeProjectId} canManagePayments={canManagePayments} /> : null}

          {deployOpen ? <LabourDeploymentDialog projectId={activeProjectId} onClose={() => setDeployOpen(false)} /> : null}
        </>
      )}
    </div>
  );
}
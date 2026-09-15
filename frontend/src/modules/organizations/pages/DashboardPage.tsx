import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useOrganization, useMembers } from "../hooks";
import { useDashboardAttention } from "../hooks/useDashboardAttention";
import { useClients, useMilestonesSummary, useProjects } from "../../projects";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { DashboardGreeting } from "../components/DashboardGreeting";
import { DashboardProjectHealth } from "../components/DashboardProjectHealth";
import { DashboardAttentionFeed } from "../components/DashboardAttentionFeed";
import { DashboardActivityFeed } from "../components/DashboardActivityFeed";
import { DashboardSitePhotos } from "../components/DashboardSitePhotos";
import { DashboardFinancialSummary } from "../components/DashboardFinancialSummary";
import {ErrorState, LoadingState, SectionDivider, StatCard,
} from "../components/OrganizationUi";

export function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const permissions = usePermissionKeys();

  const organizationQuery = useOrganization();
  const projectsQuery = useProjects();
  const clientsQuery = useClients();
  const membersQuery = useMembers(0, 100);
  const milestonesSummaryQuery = useMilestonesSummary();
  const attention = useDashboardAttention();

  const canManageMembers = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MEMBERS_MANAGE,
  );

  if (organizationQuery.isLoading || projectsQuery.isLoading || clientsQuery.isLoading) {
    return <LoadingState label={t("dashboard.loading")} />;
  }

  if (
    organizationQuery.isError ||
    projectsQuery.isError ||
    clientsQuery.isError ||
    !organizationQuery.data ||
    !projectsQuery.data ||
    !clientsQuery.data
  ) {
    return (
      <ErrorState
        title={t("dashboard.loadError")}
        onRetry={() => {
          void organizationQuery.refetch();
          void projectsQuery.refetch();
          void clientsQuery.refetch();
        }}
      />
    );
  }

  const organization = organizationQuery.data;
  const projects = projectsQuery.data;
  const clients = clientsQuery.data;

  const clientNameById = new Map(clients.map((client) => [client.id, client.name]));

  const milestoneSummaryByProject = new Map(
    (milestonesSummaryQuery.data ?? []).map((row) => [
      row.project_id,
      { total: row.milestone_total, completed: row.milestone_completed },
    ]),
  );

  const activeProjectCount = projects.filter((project) => project.status === "ACTIVE").length;
  const memberCount = membersQuery.data?.total ?? 0;
  const attentionCount = attention.items.length;

  return (
    <div className="space-y-7">
      <DashboardGreeting organizationName={organization.name} />

      <section>
        <SectionDivider
          title={t("dashboard.pulse.title")}
          description={t("dashboard.pulse.description")}
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label={t("dashboard.stat.activeProjects")}
            value={activeProjectCount}
            note={t("dashboard.stat.totalProjects", { count: projects.length })}
            icon="projects"
            tone="blue"
            actionLabel={t("dashboard.stat.viewProjects")}
            onAction={() => navigate("/app/projects")}
          />

          <StatCard
            label={t("dashboard.stat.team")}
            value={memberCount}
            note={t("dashboard.stat.organizationMembers")}
            icon="users"
            tone="blue"
            actionLabel={canManageMembers ? t("dashboard.stat.manageMembers") : undefined}
            onAction={
              canManageMembers
                ? () => navigate("/app/organization/members")
                : undefined
            }
          />

          <StatCard
            label={t("dashboard.stat.needsAttention")}
            value={attention.isLoading ? "…" : attentionCount}
            note={
              attentionCount > 0
                ? t("dashboard.stat.openItems")
                : t("dashboard.stat.allCaughtUp")
            }
            icon="alert"
            tone={attentionCount > 0 ? "gold" : "green"}
            actionLabel={attentionCount > 0 ? t("dashboard.stat.review") : undefined}
            onAction={
              attentionCount > 0
                ? () => navigate(attention.items[0].to)
                : undefined
            }
          />

          <StatCard
            label={t("dashboard.stat.ai")}
            value={organization.ai_enabled ? t("org.aiOn") : t("org.aiOff")}
            note={t("org.aiNote")}
            icon="spark"
            tone={organization.ai_enabled ? "green" : "gold"}
          />
        </div>
      </section>

      <section>
        <SectionDivider
          title={t("dashboard.financialSection.title")}
          description={t("dashboard.financialSection.description")}
        />
        <DashboardFinancialSummary />
      </section>

      <section>
        <DashboardSitePhotos />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
        <div className="space-y-5">
          <DashboardProjectHealth
            projects={projects}
            clientNameById={clientNameById}
            milestoneSummaryByProject={milestoneSummaryByProject}
          />
          <DashboardActivityFeed />
        </div>

        <div className="space-y-5">
          <DashboardAttentionFeed
            items={attention.items}
            isLoading={attention.isLoading}
          />
        </div>
      </section>
    </div>
  );
}
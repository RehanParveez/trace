import { useNavigate } from "react-router-dom";
import { useOrganization, useMembers } from "../hooks";
import { useDashboardAttention } from "../hooks/useDashboardAttention";
import { useClients, useProjects } from "../../projects";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { DashboardGreeting } from "../components/DashboardGreeting";
import { DashboardProjectHealth } from "../components/DashboardProjectHealth";
import { DashboardAttentionFeed } from "../components/DashboardAttentionFeed";
import { DashboardActivityFeed } from "../components/DashboardActivityFeed";
import {ErrorState, LoadingState, SectionDivider, StatCard,
} from "../components/OrganizationUi";

export function DashboardPage() {
  const navigate = useNavigate();
  const permissions = usePermissionKeys();

  const organizationQuery = useOrganization();
  const projectsQuery = useProjects();
  const clientsQuery = useClients();
  const membersQuery = useMembers(0, 100);
  const attention = useDashboardAttention();

  const canManageMembers = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MEMBERS_MANAGE,
  );

  if (organizationQuery.isLoading || projectsQuery.isLoading || clientsQuery.isLoading) {
    return <LoadingState label="Loading your workspace…" />;
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
        title="We couldn't load your dashboard"
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

  const activeProjectCount = projects.filter((project) => project.status === "ACTIVE").length;
  const memberCount = membersQuery.data?.total ?? 0;
  const attentionCount = attention.items.length;

  return (
    <div className="space-y-7">
      <DashboardGreeting organizationName={organization.name} />

      <section>
        <SectionDivider
          title="Workspace pulse"
          description="Where things stand across your organization right now."
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Active projects"
            value={activeProjectCount}
            note={`${projects.length} total projects`}
            icon="projects"
            tone="blue"
            actionLabel="View projects"
            onAction={() => navigate("/app/projects")}
          />

          <StatCard
            label="Team"
            value={memberCount}
            note="Organization members"
            icon="users"
            tone="blue"
            actionLabel={canManageMembers ? "Manage members" : undefined}
            onAction={canManageMembers ? () => navigate("/app/organization/members") : undefined}
          />

          <StatCard
            label="Needs attention"
            value={attention.isLoading ? "…" : attentionCount}
            note={attentionCount > 0 ? "Open items across your workspace" : "You're all caught up"}
            icon="alert"
            tone={attentionCount > 0 ? "gold" : "green"}
            actionLabel={attentionCount > 0 ? "Review" : undefined}
            onAction={attentionCount > 0 ? () => navigate(attention.items[0].to) : undefined}
          />

          <StatCard
            label="AI"
            value={organization.ai_enabled ? "On" : "Off"}
            note="Assistive capability"
            icon="spark"
            tone={organization.ai_enabled ? "green" : "gold"}
          />
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
        <div className="space-y-5">
          <DashboardProjectHealth projects={projects} clientNameById={clientNameById} />
          <DashboardActivityFeed />
        </div>

        <div className="space-y-5">
          <DashboardAttentionFeed items={attention.items} isLoading={attention.isLoading} />
        </div>
      </section>
    </div>
  );
}
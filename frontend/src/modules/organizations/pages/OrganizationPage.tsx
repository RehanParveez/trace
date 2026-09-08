import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {useAISettings, useMembers, useOrganization, useRoles, useUpdateAISettings, useUpdateOrganization,
} from "../hooks";
import { AISettingsCard } from "../components/AISettingsCard";
import { OrganizationForm } from "../components/OrganizationForm";
import { OrganizationHeader } from "../components/OrganizationHeader";
import {ErrorState, LoadingState, PageHeader, Panel, PanelHeader, SectionDivider, StatCard,
} from "../components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";

export function OrganizationPage() {
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const permissions = usePermissionKeys();

  const organizationQuery = useOrganization();
  const aiSettingsQuery = useAISettings();
  const membersQuery = useMembers(0, 100);
  const rolesQuery = useRoles();

  const updateOrganization = useUpdateOrganization();
  const updateAISettings = useUpdateAISettings();

  const canManage = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MANAGE,
  );

  if (organizationQuery.isLoading) {
    return <LoadingState />;
  }

  if (organizationQuery.isError || !organizationQuery.data) {
    return (
      <ErrorState onRetry={() => void organizationQuery.refetch()} />
    );
  }

  const organization = organizationQuery.data;

  const memberCount = membersQuery.data?.total ?? 0;

  const activeMemberCount =
    membersQuery.data?.items.filter((member) => member.is_active).length ?? 0;

  const roleCount = rolesQuery.data?.length ?? 0;

  const aiEnabled =
    aiSettingsQuery.data?.ai_enabled ?? organization.ai_enabled;

  return (
    <div className="space-y-7">

      <PageHeader
        title="Organization control"
        description="Manage workspace identity, access and governance across the Trace operating environment."
      />

      <OrganizationHeader
        organization={organization}
        canManage={canManage}
        onEdit={() => setEditing(true)}
      />

      <section>
        <SectionDivider
          title="Workspace pulse"
          description="Current access and operating status across this organization."
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Members"
            value={memberCount}
            note={`${activeMemberCount} active`}
            icon="users"
            tone="blue"
            actionLabel="Manage members"
            onAction={() => navigate("/app/organization/members")}
          />

          <StatCard
            label="Roles"
            value={roleCount}
            note="System + custom access"
            icon="shield"
            tone="gold"
            actionLabel="Manage roles"
            onAction={() => navigate("/app/organization/roles")}
          />

          <StatCard
            label="Organization"
            value={organization.is_active ? "Live" : "Paused"}
            note={
              organization.is_active
                ? "Workspace operational"
                : "Workspace restricted"
            }
            icon="building"
            tone={organization.is_active ? "green" : "red"}
          />

          <StatCard
            label="AI"
            value={aiEnabled ? "On" : "Off"}
            note="Assistive capability"
            icon="spark"
            tone={aiEnabled ? "green" : "gold"}
          />
        </div>
      </section>

      <section>
        <SectionDivider
          title="AI governance"
          description="Organization-level control for Trace's assistive intelligence."
        />

        <AISettingsCard
          enabled={aiEnabled}
          canManage={canManage}
          isUpdating={updateAISettings.isPending}
          onChange={(enabled) =>
            updateAISettings.mutate({ ai_enabled: enabled })
          }
        />
      </section>

      <section>
        <SectionDivider
          title="Workspace identity"
          description="The tenant identity used throughout the Trace workspace."
        />

        <Panel>
          <PanelHeader
            eyebrow="TENANT DETAILS"
            title="Organization details"
            description="Core workspace identifiers and operating status."
          />

          <div className="grid gap-0 divide-y divide-[var(--color-border)] md:grid-cols-2 md:divide-x md:divide-y-0">
            <div className="min-w-0 p-5 sm:p-6">
              <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
                Organization name
              </div>

              <div className="mt-2 truncate text-[15px] font-semibold text-[var(--color-text-primary)]">
                {organization.name}
              </div>

              <div className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
                Primary workspace identity
              </div>
            </div>

            <div className="min-w-0 p-5 sm:p-6">
              <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
                Workspace slug
              </div>

              <div className="mt-2 min-w-0 truncate font-mono text-[12px] font-semibold text-[var(--color-text-primary)]">
                {organization.slug}
              </div>

              <div className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
                Stable workspace identifier
              </div>
            </div>
          </div>
        </Panel>
      </section>

      {editing ? (
        <OrganizationForm
          organization={organization}
          isSubmitting={updateOrganization.isPending}
          onSubmit={(payload) =>
            updateOrganization.mutate(payload, {
              onSuccess: () => setEditing(false),
            })
          }
          onCancel={() => setEditing(false)}
        />
      ) : null}
    </div>
  );
}
import { useState } from "react";
import {useAISettings, useMembers, useOrganization, useRoles, useUpdateAISettings, useUpdateOrganization,
} from "../hooks";
import { AISettingsCard } from "../components/AISettingsCard";
import { OrganizationForm } from "../components/OrganizationForm";
import { OrganizationHeader } from "../components/OrganizationHeader";
import {ErrorState, LoadingState, PageHeader, Panel, PanelHeader, SectionDivider, StatCard,
} from "../components/OrganizationUi";
import { ORGANIZATION_PERMISSIONS } from "../permissions";

interface OrganizationPageProps {
  permissions?: string[];
}

export function OrganizationPage({
  permissions = [],
}: OrganizationPageProps) {
  const [editing, setEditing] = useState(false);

  const organizationQuery = useOrganization();
  const aiSettingsQuery = useAISettings();
  const membersQuery = useMembers(0, 100);
  const rolesQuery = useRoles();

  const updateOrganization = useUpdateOrganization();
  const updateAISettings = useUpdateAISettings();

  const canManage = permissions.includes(
    ORGANIZATION_PERMISSIONS.ORGANIZATION_MANAGE,
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

  const memberCount = membersQuery.data?.length ?? 0;

  const activeMemberCount =
    membersQuery.data?.filter((member) => member.is_active).length ?? 0;

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
          />

          <StatCard
            label="Roles"
            value={roleCount}
            note="System + custom access"
            icon="shield"
            tone="gold"
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

          <div className="grid gap-0 divide-y divide-[#e1d5bc] md:grid-cols-2 md:divide-x md:divide-y-0">
            <div className="min-w-0 p-5 sm:p-6">
              <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
                Organization name
              </div>

              <div className="mt-2 truncate text-[14px] font-semibold text-[#191410]">
                {organization.name}
              </div>

              <div className="mt-1 text-[11px] text-[#7c7060]">
                Primary workspace identity
              </div>
            </div>

            <div className="min-w-0 p-5 sm:p-6">
              <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
                Workspace slug
              </div>

              <div className="mt-2 min-w-0 truncate font-mono text-[11px] font-semibold text-[#332a21]">
                {organization.slug}
              </div>

              <div className="mt-1 text-[11px] text-[#7c7060]">
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
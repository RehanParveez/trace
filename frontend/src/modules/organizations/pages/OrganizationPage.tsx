import {useState,
} from "react";
import {useAISettings, useMembers, useOrganization, useRoles, useUpdateAISettings, useUpdateOrganization,
} from "../hooks";
import {AISettingsCard,
} from "../components/AISettingsCard";
import {OrganizationForm,
} from "../components/OrganizationForm";
import {OrganizationHeader,
} from "../components/OrganizationHeader";
import {ErrorState, LoadingState, PageHeader, Panel, PanelHeader, StatCard,
} from "../components/OrganizationUi";
import {ORGANIZATION_PERMISSIONS,
} from "../permissions";

interface OrganizationPageProps {
  permissions?: string[];
}

export function OrganizationPage({
  permissions = [],
}: OrganizationPageProps) {
  const [editing, setEditing] =
    useState(false);

  const organizationQuery =
    useOrganization();

  const aiSettingsQuery =
    useAISettings();

  const membersQuery =
    useMembers(0, 100);

  const rolesQuery =
    useRoles();

  const updateOrganization =
    useUpdateOrganization();

  const updateAISettings =
    useUpdateAISettings();

  const canManage =
    permissions.includes(
      ORGANIZATION_PERMISSIONS.ORGANIZATION_MANAGE,
    );

  if (organizationQuery.isLoading) {
    return (
      <LoadingState />
    );
  }

  if (
    organizationQuery.isError ||
    !organizationQuery.data
  ) {
    return (
      <ErrorState
        onRetry={() =>
          void organizationQuery.refetch()
        }
      />
    );
  }

  const organization =
    organizationQuery.data;

  const memberCount =
    membersQuery.data?.length ??
    0;

  const activeMemberCount =
    membersQuery.data?.filter(
      (member) =>
        member.is_active,
    ).length ?? 0;

  const roleCount =
    rolesQuery.data?.length ??
    0;

  return (
    <div>
      <PageHeader
        title="Organization control"
        description="Set the operating identity, access model and AI governance that sit above every project workflow."
      />

      <div className="space-y-5">
        <OrganizationHeader
          organization={
            organization
          }
          canManage={
            canManage
          }
          onEdit={() =>
            setEditing(true)
          }
        />

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
            value={
              organization.is_active
                ? "Live"
                : "Paused"
            }
            note={
              organization.is_active
                ? "Workspace operational"
                : "Workspace restricted"
            }
            icon="building"
            tone={
              organization.is_active
                ? "green"
                : "red"
            }
          />

          <StatCard
            label="AI"
            value={
              organization.ai_enabled
                ? "On"
                : "Off"
            }
            note="Organization-level control"
            icon="spark"
            tone={
              organization.ai_enabled
                ? "green"
                : "gold"
            }
          />
        </div>

        <AISettingsCard
          enabled={
            aiSettingsQuery.data
              ?.ai_enabled ??
            organization.ai_enabled
          }
          canManage={
            canManage
          }
          isUpdating={
            updateAISettings.isPending
          }
          onChange={(enabled) =>
            updateAISettings.mutate({
              ai_enabled:
                enabled,
            })
          }
        />

        <Panel>
          <PanelHeader
            eyebrow="WORKSPACE IDENTITY"
            title="Organization details"
            description="These values define the tenant identity used throughout Trace."
          />

          <div className="grid gap-0 divide-y divide-[#e1d5bc] md:grid-cols-2 md:divide-x md:divide-y-0">
            <div className="p-5">
              <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
                Name
              </div>

              <div className="mt-1.5 text-[13px] font-semibold text-[#191410]">
                {
                  organization.name
                }
              </div>
            </div>

            <div className="p-5">
              <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
                Slug
              </div>

              <div className="mt-1.5 font-mono text-[11px] font-semibold text-[#332a21]">
                {
                  organization.slug
                }
              </div>
            </div>
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="GOVERNANCE"
            title="Why this layer matters"
            description="Trace is organized around a connected construction workflow rather than disconnected CRUD screens."
          />

          <div className="grid gap-3 p-5 md:grid-cols-3">
            {[
              [
                "Access",
                "Roles and permissions define who can act on organization and project workflows.",
              ],
              [
                "Traceability",
                "Operational changes remain attributable to authenticated users and explicit actions.",
              ],
              [
                "AI boundary",
                "AI can assist, but humans remain responsible for approvals and official state.",
              ],
            ].map(
              ([title, body]) => (
                <div
                  key={title}
                  className="rounded-[10px] border border-[#e1d5bc] bg-white p-4"
                >
                  <div className="text-[12px] font-bold text-[#191410]">
                    {title}
                  </div>

                  <p className="mt-1.5 text-[11px] leading-5 text-[#6b6152]">
                    {body}
                  </p>
                </div>
              ),
            )}
          </div>
        </Panel>
      </div>

      {editing ? (
        <OrganizationForm
          organization={
            organization
          }
          isSubmitting={
            updateOrganization.isPending
          }
          onSubmit={(payload) =>
            updateOrganization.mutate(
              payload,
              {
                onSuccess: () =>
                  setEditing(false),
              },
            )
          }
          onCancel={() =>
            setEditing(false)
          }
        />
      ) : null}
    </div>
  );
}
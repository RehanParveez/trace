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
import { useTranslation } from "react-i18next";

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

  const { t } = useTranslation();

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
        title={t("org.pageTitle")}
        description={t("org.pageDescription")}
      />

      <OrganizationHeader
        organization={organization}
        canManage={canManage}
        onEdit={() => setEditing(true)}
      />

      <section>
        <SectionDivider
          title={t("org.workspacePulse")}
          description={t("org.workspacePulseDesc")}
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label={t("org.members")}
            value={memberCount}
            note={t("org.membersActive", { count: activeMemberCount })}
            icon="users"
            tone="blue"
            actionLabel={t("org.manageMembers")}
            onAction={() => navigate("/app/organization/members")}
          />

          <StatCard
            label={t("org.roles")}
            value={roleCount}
            note={t("org.rolesNote")}
            icon="shield"
            tone="gold"
            actionLabel={t("org.manageRoles")}
            onAction={() => navigate("/app/organization/roles")}
          />

          <StatCard
            label={t("org.organization")}
            value={organization.is_active ? t("org.live") : t("org.paused")}
            note={organization.is_active ? t("org.workspaceOperational") : t("org.workspaceRestricted")}
            icon="building"
            tone={organization.is_active ? "green" : "red"}
          />

          <StatCard
            label={t("org.ai")}
            value={aiEnabled ? t("org.aiOn") : t("org.aiOff")}
            note={t("org.aiNote")}
            icon="spark"
            tone={aiEnabled ? "green" : "gold"}
          />
        </div>
      </section>

      <section>
        <SectionDivider
          title={t("org.aiGovernance")}
          description={t("org.aiGovernanceDesc")}
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
          title={t("org.workspaceIdentity")}
          description={t("org.workspaceIdentityDesc")}
        />

        <Panel>
          <PanelHeader
            eyebrow={t("org.tenantDetails")}
            title={t("org.organizationDetails")}
            description={t("org.organizationDetailsDesc")}
          />

          <div className="grid gap-0 divide-y divide-[var(--color-border)] md:grid-cols-2 md:divide-x md:divide-y-0">
            <div className="min-w-0 p-5 sm:p-6">
              <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
                {t("org.organizationName")}
              </div>

              <div className="mt-2 truncate text-[15px] font-semibold text-[var(--color-text-primary)]">
                {organization.name}
              </div>

              <div className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
                {t("org.primaryIdentity")}
              </div>
            </div>

            <div className="min-w-0 p-5 sm:p-6">
              <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
                {t("org.workspaceSlug")}
              </div>

              <div className="mt-2 min-w-0 truncate font-mono text-[12px] font-semibold text-[var(--color-text-primary)]">
                {organization.slug}
              </div>

              <div className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
                {t("org.stableIdentifier")}
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
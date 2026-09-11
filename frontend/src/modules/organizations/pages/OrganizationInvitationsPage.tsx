import { useState } from "react";
import {useCreateInvitation, useInvitations, useRevokeInvitation, useRoles,
} from "../hooks";
import type { Invitation } from "../types/organization.types";
import { InvitationForm } from "../components/InvitationForm";
import { InvitationTable } from "../components/InvitationTable";
import { RevokeInvitationDialog } from "../components/RevokeInvitationDialog";
import {Button, ErrorState, Icon, PageHeader, Pager, SectionDivider, StatCard,
} from "../components/OrganizationUi";
import { getInvitationStatus } from "../utils/organization.utils";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useTranslation } from "react-i18next";

const PAGE_SIZE = 20;

export function OrganizationInvitationsPage() {
  const permissions = usePermissionKeys();

  const [showForm, setShowForm] = useState(false);
  const [revokeInvitation, setRevokeInvitation] =
    useState<Invitation | null>(null);
  const [page, setPage] = useState(0);

  const { t } = useTranslation();

  const invitationsQuery = useInvitations(page * PAGE_SIZE, PAGE_SIZE);
  const rolesQuery = useRoles();

  const createInvitation = useCreateInvitation();
  const revoke = useRevokeInvitation();

  const canManage = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MEMBERS_MANAGE,
  );

  const invitations = invitationsQuery.data?.items ?? [];
  const totalInvitations = invitationsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalInvitations / PAGE_SIZE));
  const roles = rolesQuery.data ?? [];

  const pending = invitations.filter(
    (item) => getInvitationStatus(item) === "pending",
  ).length;

  const accepted = invitations.filter(
    (item) => getInvitationStatus(item) === "accepted",
  ).length;

  const expired = invitations.filter(
    (item) => getInvitationStatus(item) === "expired",
  ).length;

  if (invitationsQuery.isError || rolesQuery.isError) {
    return (
      <ErrorState
        title={t("invitations.loadError")}
        onRetry={() => {
          void invitationsQuery.refetch();
          void rolesQuery.refetch();
        }}
      />
    );
  }

  return (
    <div>
      <PageHeader
        title={t("invitations.pageTitle")}
        description={t("invitations.pageDescription")}
        actions={
          canManage ? (
            <Button
              variant={showForm ? "secondary" : "primary"}
              onClick={() => setShowForm((current) => !current)}
            >
              <Icon name={showForm ? "x" : "plus"} size={13} />
              {showForm ? t("invitations.close") : t("invitations.invite")}
            </Button>
          ) : null
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label={t("invitations.pending")}
          value={pending}
          note={t("invitations.pendingNote")}
          icon="mail"
          tone="gold"
        />

        <StatCard
          label={t("invitations.accepted")}
          value={accepted}
          note="Successfully joined"
          icon="check"
          tone="green"
        />

        <StatCard
          label={t("invitations.expired")}
          value={expired}
          note={t("invitations.acceptedNote")}
          icon="lock"
          tone="blue"
        />
      </div>

      {showForm ? (
        <>
          <SectionDivider title={t("invitations.inviteSection")} />

          <InvitationForm
            roles={roles}
            isSubmitting={createInvitation.isPending}
            onSubmit={(email, roleId) =>
              createInvitation.mutate(
                { email, role_id: roleId },
                { onSuccess: () => setShowForm(false) },
              )
            }
            onCancel={() => setShowForm(false)}
          />
        </>
      ) : null}

      <SectionDivider
        title={t("invitations.sectionTitle")}
        description={t("invitations.sectionDesc", { count: invitations.length })}
      />

      <InvitationTable
        invitations={invitations}
        roles={roles}
        canManage={canManage}
        onRevoke={setRevokeInvitation}
      />

      <Pager
        page={page}
        totalPages={totalPages}
        totalItems={totalInvitations}
        onPrevious={() => setPage((current) => Math.max(0, current - 1))}
        onNext={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
      />

      {revokeInvitation ? (
        <RevokeInvitationDialog
          invitation={revokeInvitation}
          isSubmitting={revoke.isPending}
          onClose={() => setRevokeInvitation(null)}
          onConfirm={() =>
            revoke.mutate(revokeInvitation.id, {
              onSuccess: () => setRevokeInvitation(null),
            })
          }
        />
      ) : null}
    </div>
  );
}

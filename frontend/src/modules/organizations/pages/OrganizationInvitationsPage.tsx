import {useState,
} from "react";
import {useCreateInvitation, useInvitations, useRevokeInvitation, useRoles,
} from "../hooks";
import type {Invitation,
} from "../types/organization.types";
import {InvitationForm,
} from "../components/InvitationForm";
import {InvitationTable,
} from "../components/InvitationTable";
import {RevokeInvitationDialog,
} from "../components/RevokeInvitationDialog";
import {Button, ErrorState, Icon, PageHeader, Panel, PanelHeader, StatCard,
} from "../components/OrganizationUi";
import {getInvitationStatus,
} from "../utils/organization.utils";

interface OrganizationInvitationsPageProps {
  permissions?: string[];
}

export function OrganizationInvitationsPage({
  permissions = [],
}: OrganizationInvitationsPageProps) {
  const [
    showForm,
    setShowForm,
  ] = useState(false);

  const [
    revokeInvitation,
    setRevokeInvitation,
  ] = useState<Invitation | null>(
    null,
  );

  const invitationsQuery =
    useInvitations();

  const rolesQuery =
    useRoles();

  const createInvitation =
    useCreateInvitation();

  const revoke =
    useRevokeInvitation();

  const canManage =
    permissions.includes(
      "organization:members_manage",
    );

  const invitations =
    invitationsQuery.data ??
    [];

  const pending =
    invitations.filter(
      (item) =>
        getInvitationStatus(
          item,
        ) === "pending",
    ).length;

  const accepted =
    invitations.filter(
      (item) =>
        getInvitationStatus(
          item,
        ) === "accepted",
    ).length;

  const expired =
    invitations.filter(
      (item) =>
        getInvitationStatus(
          item,
        ) === "expired",
    ).length;

  if (
    invitationsQuery.isError ||
    rolesQuery.isError
  ) {
    return (
      <ErrorState
        title="We couldn't load invitations"
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
        title="Invitations"
        description="Control who is entering the organization workspace, which role they receive and which pending access requests remain outstanding."
        actions={
          canManage ? (
            <Button
              variant={
                showForm
                  ? "secondary"
                  : "primary"
              }
              onClick={() =>
                setShowForm(
                  (current) =>
                    !current,
                )
              }
            >
              <Icon
                name={
                  showForm
                    ? "x"
                    : "plus"
                }
                size={13}
              />

              {showForm
                ? "Close"
                : "Invite member"}
            </Button>
          ) : null
        }
      />

      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Pending"
            value={pending}
            note="Awaiting acceptance"
            icon="mail"
            tone="gold"
          />

          <StatCard
            label="Accepted"
            value={accepted}
            note="Successfully joined"
            icon="check"
            tone="green"
          />

          <StatCard
            label="Expired"
            value={expired}
            note="No longer usable"
            icon="lock"
            tone="blue"
          />
        </div>

        {showForm ? (
          <InvitationForm
            roles={
              rolesQuery.data ??
              []
            }
            isSubmitting={
              createInvitation.isPending
            }
            onSubmit={(
              email,
              roleId,
            ) =>
              createInvitation.mutate(
                {
                  email,
                  role_id:
                    roleId,
                },
                {
                  onSuccess:
                    () =>
                      setShowForm(
                        false,
                      ),
                },
              )
            }
            onCancel={() =>
              setShowForm(
                false,
              )
            }
          />
        ) : null}

        <Panel>
          <PanelHeader
            eyebrow="ACCESS HISTORY"
            title="Organization invitations"
            description={`${invitations.length} invitation${invitations.length === 1 ? "" : "s"} returned by the organization API.`}
          />

          <InvitationTable
            invitations={
              invitations
            }
            canManage={
              canManage
            }
            onRevoke={
              setRevokeInvitation
            }
          />
        </Panel>
      </div>

      {revokeInvitation ? (
        <RevokeInvitationDialog
          invitation={
            revokeInvitation
          }
          isSubmitting={
            revoke.isPending
          }
          onClose={() =>
            setRevokeInvitation(
              null,
            )
          }
          onConfirm={() =>
            revoke.mutate(
              revokeInvitation.id,
              {
                onSuccess:
                  () =>
                    setRevokeInvitation(
                      null,
                    ),
              },
            )
          }
        />
      ) : null}
    </div>
  );
}
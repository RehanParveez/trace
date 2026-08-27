import {useMemo, useState,
} from "react";
import {useNavigate,
} from "react-router-dom";
import {useMembers, useRoles, useUpdateMemberRole, useUpdateMemberStatus,
} from "../hooks";
import type {Member,
} from "../types/organization.types";
import {MemberRoleDialog,
} from "../components/MemberRoleDialog";
import {MemberStatusDialog,
} from "../components/MemberStatusDialog";
import {MemberTable,
} from "../components/MemberTable";
import {ErrorState, Panel, PanelHeader, PageHeader, StatCard,
} from "../components/OrganizationUi";

interface OrganizationMembersPageProps {
  permissions?: string[];
}

export function OrganizationMembersPage({
  permissions = [],
}: OrganizationMembersPageProps) {
  const navigate =
    useNavigate();

  const [
    roleMember,
    setRoleMember,
  ] = useState<Member | null>(
    null,
  );

  const [
    statusMember,
    setStatusMember,
  ] = useState<Member | null>(
    null,
  );

  const [
    query,
    setQuery,
  ] = useState("");

  const membersQuery =
    useMembers();

  const rolesQuery =
    useRoles();

  const updateRole =
    useUpdateMemberRole();

  const updateStatus =
    useUpdateMemberStatus();

  const canManage =
    permissions.includes(
      "organization:members_manage",
    );

  const members =
    membersQuery.data ?? [];

  const filteredMembers =
    useMemo(() => {
      const normalized =
        query.trim().toLowerCase();

      if (!normalized) {
        return members;
      }

      return members.filter(
        (member) =>
          `${member.first_name} ${member.last_name} ${member.email} ${member.role.name}`
            .toLowerCase()
            .includes(
              normalized,
            ),
      );
    }, [
      members,
      query,
    ]);

  if (
    membersQuery.isError ||
    rolesQuery.isError
  ) {
    return (
      <ErrorState
        title="We couldn't load organization members"
        onRetry={() => {
          void membersQuery.refetch();
          void rolesQuery.refetch();
        }}
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="Members"
        description="Manage the people who operate this organization and control their access without leaving the main workspace."
      />

      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Total members"
            value={members.length}
            note="Organization users"
            icon="users"
            tone="blue"
          />

          <StatCard
            label="Active"
            value={
              members.filter(
                (member) =>
                  member.is_active,
              ).length
            }
            note="Can access workspace"
            icon="check"
            tone="green"
          />

          <StatCard
            label="Verified"
            value={
              members.filter(
                (member) =>
                  member.is_verified,
              ).length
            }
            note="Identity verified"
            icon="shield"
            tone="gold"
          />
        </div>

        <Panel>
          <PanelHeader
            eyebrow="ACCESS DIRECTORY"
            title="Organization members"
            description={`${filteredMembers.length} visible member${filteredMembers.length === 1 ? "" : "s"}.`}
            action={
              <div className="flex h-8 items-center gap-2 rounded-[8px] border border-[#e1d5bc] bg-white px-2.5">
                <IconSearch />

                <input
                  value={query}
                  onChange={(event) =>
                    setQuery(
                      event.target.value,
                    )
                  }
                  className="w-[150px] bg-transparent text-[11px] outline-none placeholder:text-[#a2957c]"
                  placeholder="Filter members"
                />
              </div>
            }
          />

          <MemberTable
            members={
              filteredMembers
            }
            canManage={
              canManage
            }
            onView={(member) =>
              navigate(
                `/app/organization/members/${member.id}`,
              )
            }
            onRoleChange={
              setRoleMember
            }
            onStatusChange={
              setStatusMember
            }
          />
        </Panel>
      </div>

      {roleMember ? (
        <MemberRoleDialog
          member={
            roleMember
          }
          roles={
            rolesQuery.data ??
            []
          }
          isSubmitting={
            updateRole.isPending
          }
          onClose={() =>
            setRoleMember(null)
          }
          onSubmit={(roleId) =>
            updateRole.mutate(
              {
                userId:
                  roleMember.id,
                payload: {
                  role_id:
                    roleId,
                },
              },
              {
                onSuccess: () =>
                  setRoleMember(
                    null,
                  ),
              },
            )
          }
        />
      ) : null}

      {statusMember ? (
        <MemberStatusDialog
          member={
            statusMember
          }
          isSubmitting={
            updateStatus.isPending
          }
          onClose={() =>
            setStatusMember(
              null,
            )
          }
          onConfirm={() =>
            updateStatus.mutate(
              {
                userId:
                  statusMember.id,
                payload: {
                  is_active:
                    !statusMember.is_active,
                },
              },
              {
                onSuccess: () =>
                  setStatusMember(
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

function IconSearch() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-[#a2957c]"
      aria-hidden="true"
    >
      <circle
        cx="11"
        cy="11"
        r="7"
      />
      <path d="m20 20-4-4" />
    </svg>
  );
}
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {useMembers, useRoles, useUpdateMemberRole, useUpdateMemberStatus,
} from "../hooks";
import type { Member } from "../types/organization.types";
import { MemberRoleDialog } from "../components/MemberRoleDialog";
import { MemberStatusDialog } from "../components/MemberStatusDialog";
import { MemberTable } from "../components/MemberTable";
import {ErrorState, Icon, PageHeader, Pager, SectionDivider, StatCard,
} from "../components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys, useAuthStore } from "../../identity";

const PAGE_SIZE = 20;

export function OrganizationMembersPage() {
  const navigate = useNavigate();
  const permissions = usePermissionKeys();
  const currentUser = useAuthStore((state) => state.user);

  const [roleMember, setRoleMember] = useState<Member | null>(null);
  const [statusMember, setStatusMember] = useState<Member | null>(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const membersQuery = useMembers(page * PAGE_SIZE, PAGE_SIZE);
  const rolesQuery = useRoles();

  const updateRole = useUpdateMemberRole();
  const updateStatus = useUpdateMemberStatus();

  const canManage = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MEMBERS_MANAGE,
  );

  const members = membersQuery.data?.items ?? [];
  const totalMembers = membersQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalMembers / PAGE_SIZE));

  const filteredMembers = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      return members;
    }

    return members.filter((member) =>
      `${member.first_name} ${member.last_name} ${member.email} ${member.role.name}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [members, query]);

  if (membersQuery.isError || rolesQuery.isError) {
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
        actions={
          <div className="flex h-9 items-center gap-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3">
            <Icon name="search" size={14} className="text-[var(--color-text-muted)]" />

            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-[170px] bg-transparent text-[13px] outline-none placeholder:text-[var(--color-text-muted)]"
              placeholder="Filter members"
            />
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Total members"
          value={totalMembers}
          note="Organization users"
          icon="users"
          tone="blue"
        />

        <StatCard
          label="Active"
          value={members.filter((member) => member.is_active).length}
          note="On this page"
          icon="check"
          tone="green"
        />

        <StatCard
          label="Verified"
          value={members.filter((member) => member.is_verified).length}
          note="On this page"
          icon="shield"
          tone="gold"
        />
      </div>

      <SectionDivider
        title="Access directory"
        description={`${filteredMembers.length} visible member${filteredMembers.length === 1 ? "" : "s"}.`}
      />

      <MemberTable
        members={filteredMembers}
        canManage={canManage}
        currentUserId={currentUser?.id}
        onView={(member) =>
          navigate(`/app/organization/members/${member.id}`)
        }
        onRoleChange={setRoleMember}
        onStatusChange={setStatusMember}
      />

      <Pager
        page={page}
        totalPages={totalPages}
        totalItems={totalMembers}
        onPrevious={() => setPage((current) => Math.max(0, current - 1))}
        onNext={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
      />

      {roleMember ? (
        <MemberRoleDialog
          member={roleMember}
          roles={rolesQuery.data ?? []}
          isSubmitting={updateRole.isPending}
          error={updateRole.error}
          onClose={() => {
            updateRole.reset();
            setRoleMember(null);
          }}
          onSubmit={(roleId) =>
            updateRole.mutate(
              { userId: roleMember.id, payload: { role_id: roleId } },
              { onSuccess: () => setRoleMember(null) },
            )
          }
        />
      ) : null}

      {statusMember ? (
        <MemberStatusDialog
          member={statusMember}
          isSubmitting={updateStatus.isPending}
          error={updateStatus.error}
          onClose={() => {
            updateStatus.reset();
            setStatusMember(null);
          }}
          onConfirm={() =>
            updateStatus.mutate(
              {
                userId: statusMember.id,
                payload: { is_active: !statusMember.is_active },
              },
              { onSuccess: () => setStatusMember(null) },
            )
          }
        />
      ) : null}
    </div>
  );
}

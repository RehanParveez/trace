import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDeleteRole, useRoles } from "../hooks";
import type { Role } from "../types/organization.types";
import { RoleTable } from "../components/RoleTable";
import {Button, ErrorState, Icon, Modal, PageHeader, SectionDivider, StatCard,
} from "../components/OrganizationUi";
import { ORGANIZATION_PERMISSIONS } from "../permissions";

interface OrganizationRolesPageProps {
  permissions?: string[];
}

export function OrganizationRolesPage({
  permissions = [],
}: OrganizationRolesPageProps) {
  const navigate = useNavigate();

  const rolesQuery = useRoles();
  const deleteRole = useDeleteRole();

  const [deletingRole, setDeletingRole] = useState<Role | null>(null);

  const canManage = permissions.includes(
    ORGANIZATION_PERMISSIONS.ORGANIZATION_MANAGE,
  );

  const roles = rolesQuery.data ?? [];

  if (rolesQuery.isError) {
    return (
      <ErrorState
        title="We couldn't load organization roles"
        onRetry={() => void rolesQuery.refetch()}
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="Roles & access"
        description="Shape organization access around the responsibilities people actually perform inside the construction workflow."
        actions={
          canManage ? (
            <Button
              variant="primary"
              onClick={() => navigate("/app/organization/roles/new")}
            >
              <Icon name="plus" size={13} />
              Create role
            </Button>
          ) : null
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Roles"
          value={roles.length}
          note="Available access profiles"
          icon="shield"
          tone="gold"
        />

        <StatCard
          label="System"
          value={roles.filter((role) => role.is_system).length}
          note="Platform-managed"
          icon="lock"
          tone="blue"
        />

        <StatCard
          label="Custom"
          value={roles.filter((role) => !role.is_system).length}
          note="Organization-managed"
          icon="settings"
          tone="green"
        />
      </div>

      <SectionDivider
        title="Organization roles"
        description="System roles are protected; custom roles can be tailored to your operating model."
      />

      <RoleTable
        roles={roles}
        canManage={canManage}
        onView={(role) => navigate(`/app/organization/roles/${role.id}`)}
        onDelete={setDeletingRole}
      />

      {deletingRole ? (
        <Modal
          title="Delete role"
          description="This removes the custom role definition. System roles cannot be deleted."
          onClose={() => setDeletingRole(null)}
        >
          <div className="rounded-[10px] border border-[#e1d5bc] bg-white p-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
              Role
            </div>

            <div className="mt-1 text-[13px] font-semibold text-[#191410]">
              {deletingRole.name}
            </div>
          </div>

          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDeletingRole(null)}>
              Cancel
            </Button>

            <Button
              variant="danger"
              disabled={deleteRole.isPending}
              onClick={() =>
                deleteRole.mutate(deletingRole.id, {
                  onSuccess: () => setDeletingRole(null),
                })
              }
            >
              {deleteRole.isPending ? "Deleting…" : "Delete role"}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

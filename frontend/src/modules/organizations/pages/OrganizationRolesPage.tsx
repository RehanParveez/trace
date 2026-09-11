import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDeleteRole, useRoles } from "../hooks";
import type { Role } from "../types/organization.types";
import { RoleTable } from "../components/RoleTable";
import {Button, ErrorState, Icon, Modal, PageHeader, SectionDivider, StatCard,
} from "../components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useTranslation } from "react-i18next";

export function OrganizationRolesPage() {
  const navigate = useNavigate();
  const permissions = usePermissionKeys();
  
  const { t } = useTranslation();
  const rolesQuery = useRoles();
  const deleteRole = useDeleteRole();

  const [deletingRole, setDeletingRole] = useState<Role | null>(null);

  const canManage = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MANAGE,
  );

  const roles = rolesQuery.data ?? [];

  if (rolesQuery.isError) {
    return (
      <ErrorState
        title={t("roles.loadError")}
        onRetry={() => void rolesQuery.refetch()}
      />
    );
  }

  return (
    <div>
      <PageHeader
        title={t("roles.pageTitle")}
        description={t("roles.pageDescription")}
        actions={
          canManage ? (
            <Button
              variant="primary"
              onClick={() => navigate("/app/organization/roles/new")}
            >
              <Icon name="plus" size={13} />
              {t("roles.create")}
            </Button>
          ) : null
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label={t("roles.count")}
          value={roles.length}
          note={t("roles.countNote")}
          icon="shield"
          tone="gold"
        />

        <StatCard
          label={t("roles.system")}
          value={roles.filter((role) => role.is_system).length}
          note={t("roles.systemNote")}
          icon="lock"
          tone="blue"
        />

        <StatCard
          label={t("roles.custom")}
          value={roles.filter((role) => !role.is_system).length}
          note={t("roles.customNote")}
          icon="settings"
          tone="green"
        />
      </div>

      <SectionDivider
        title={t("roles.sectionTitle")}
        description={t("roles.sectionDesc")}
      />

      <RoleTable
        roles={roles}
        canManage={canManage}
        onView={(role) => navigate(`/app/organization/roles/${role.id}`)}
        onDelete={setDeletingRole}
      />

      {deletingRole ? (
        <Modal
          title={t("roles.deleteTitle")}
          description={t("roles.deleteDesc")}
          onClose={() => setDeletingRole(null)}
        >
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
              {t("roles.roleLabel")}
            </div>

            <div className="mt-1 text-[14px] font-semibold text-[var(--color-text-primary)]">
              {deletingRole.name}
            </div>
          </div>

          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDeletingRole(null)}>
              {t("roles.cancel")}
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
              {deleteRole.isPending ? t("roles.deleting") : t("roles.deleteConfirm")}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

import type { Role } from "../types/organization.types";
import {Badge, DropdownMenu, EmptyState, type MenuAction, Panel, PanelHeader, TableShell,
} from "./OrganizationUi";
import { useTranslation } from "react-i18next";

interface RoleTableProps {
  roles: Role[];
  canManage?: boolean;
  onView?: (role: Role) => void;
  onDelete?: (role: Role) => void;
}

function RoleActions({
  role,
  canManage,
  onView,
  onDelete,
}: {
  role: Role;
  canManage: boolean;
  onView?: (role: Role) => void;
  onDelete?: (role: Role) => void;
}) {
  const { t } = useTranslation();
  const actions: MenuAction[] = [
    { label: t("roles.viewRole"), icon: "edit", onSelect: () => onView?.(role) },
  ];

  if (canManage && !role.is_system) {
    actions.push({
     label: t("roles.deleteRole"), icon: "x", tone: "danger", onSelect: () => onDelete?.(role),
    });
  }

  return <DropdownMenu items={actions} />;
}

export function RoleTable({
  roles,
  canManage = false,
  onView,
  onDelete,
}: RoleTableProps) {
  const { t } = useTranslation();
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("roles.catalogEyebrow")}
        title={t("roles.tableTitle")}
        description={t("roles.tableDesc")}
        action={
          <span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">
            {roles.length}
          </span>
        }
      />

      {roles.length === 0 ? (
        <EmptyState
         icon="shield"
         title={t("roles.emptyTitle")}
         description={t("roles.emptyDesc")}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("roles.colRole")}</th>
                <th className="px-4 py-3">{t("roles.colType")}</th>
                <th className="px-4 py-3">{t("roles.colAccess")}</th>
                <th className="px-4 py-3 text-right">{t("roles.colActions")}</th>
              </tr>
            </thead>

            <tbody>
              {roles.map((role) => (
                <tr
                  key={role.id}
                  className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]"
                >
                  <td className="px-4 py-3.5">
                    <button
                      type="button"
                      onClick={() => onView?.(role)}
                      className="text-left"
                    >
                      <span className="block text-[14px] font-semibold text-[var(--color-text-primary)]">
                        {role.name}
                      </span>

                      {role.description ? (
                        <span className="mt-0.5 block max-w-[420px] text-[12px] leading-4 text-[var(--color-text-secondary)]">
                          {role.description}
                        </span>
                      ) : null}
                    </button>
                  </td>

                  <td className="px-4 py-3.5">
                    <Badge tone={role.is_system ? "blue" : "slate"}>
                      {role.is_system ? t("roles.system") : t("roles.custom")}
                    </Badge>
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="font-mono text-[12px] font-semibold text-[var(--color-text-primary)]">
                      {t("roles.permissionsCount", { count: role.permissions.length })}
                    </span>
                  </td>

                  <td className="px-4 py-3.5 text-right">
                    <RoleActions
                      role={role}
                      canManage={canManage}
                      onView={onView}
                      onDelete={onDelete}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}

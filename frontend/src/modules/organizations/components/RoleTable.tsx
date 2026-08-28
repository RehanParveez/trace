import type { Role } from "../types/organization.types";
import {Badge, DropdownMenu, EmptyState, type MenuAction, Panel, PanelHeader, TableShell,
} from "./OrganizationUi";

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
  const actions: MenuAction[] = [
    {
      label: "View role",
      icon: "edit",
      onSelect: () => onView?.(role),
    },
  ];

  if (canManage && !role.is_system) {
    actions.push({
      label: "Delete role",
      icon: "x",
      tone: "danger",
      onSelect: () => onDelete?.(role),
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
  return (
    <Panel>
      <PanelHeader
        eyebrow="ACCESS CATALOG"
        title="Roles"
        description="System roles are protected; custom roles can be tailored to your operating model."
        action={
          <span className="rounded-full bg-[#efe6d3] px-2.5 py-1 font-mono text-[11px] font-semibold text-[#6b6152]">
            {roles.length}
          </span>
        }
      />

      {roles.length === 0 ? (
        <EmptyState
          icon="shield"
          title="No roles found"
          description="The organization does not currently expose any role records."
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-[#f5efe3]">
              <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Access</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {roles.map((role) => (
                <tr
                  key={role.id}
                  className="border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]"
                >
                  <td className="px-4 py-3.5">
                    <button
                      type="button"
                      onClick={() => onView?.(role)}
                      className="text-left"
                    >
                      <span className="block text-[12.5px] font-semibold text-[#191410]">
                        {role.name}
                      </span>

                      {role.description ? (
                        <span className="mt-0.5 block max-w-[420px] text-[10.5px] leading-4 text-[#6b6152]">
                          {role.description}
                        </span>
                      ) : null}
                    </button>
                  </td>

                  <td className="px-4 py-3.5">
                    <Badge tone={role.is_system ? "blue" : "slate"}>
                      {role.is_system ? "System" : "Custom"}
                    </Badge>
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="font-mono text-[11px] font-semibold text-[#332a21]">
                      {role.permissions.length} permissions
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

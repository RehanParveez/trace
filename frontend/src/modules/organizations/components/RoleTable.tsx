import type {Role,
} from "../types/organization.types";
import {Badge, Button, EmptyState, Icon, TableShell,
} from "./OrganizationUi";

interface RoleTableProps {
  roles: Role[];
  canManage?: boolean;
  onView?: (
    role: Role,
  ) => void;
  onDelete?: (
    role: Role,
  ) => void;
}

export function RoleTable({
  roles,
  canManage = false,
  onView,
  onDelete,
}: RoleTableProps) {
  if (roles.length === 0) {
    return (
      <EmptyState
        icon="shield"
        title="No roles found"
        description="The organization does not currently expose any role records."
      />
    );
  }

  return (
    <TableShell>
      <table className="w-full min-w-[700px] text-left">
        <thead className="bg-[#f5efe3]">
          <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
            <th className="px-4 py-3">
              Role
            </th>

            <th className="px-4 py-3">
              Type
            </th>

            <th className="px-4 py-3">
              Access
            </th>

            <th className="px-4 py-3 text-right">
              Actions
            </th>
          </tr>
        </thead>

        <tbody>
          {roles.map(
            (role) => (
              <tr
                key={role.id}
                className="border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]"
              >
                <td className="px-4 py-3.5">
                  <button
                    type="button"
                    onClick={() =>
                      onView?.(role)
                    }
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
                  <Badge
                    tone={
                      role.is_system
                        ? "blue"
                        : "slate"
                    }
                  >
                    {role.is_system
                      ? "System"
                      : "Custom"}
                  </Badge>
                </td>

                <td className="px-4 py-3.5">
                  <span className="font-mono text-[11px] font-semibold text-[#332a21]">
                    {role.permissions.length}{" "}
                    permissions
                  </span>
                </td>

                <td className="px-4 py-3.5">
                  <div className="flex justify-end gap-1.5">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        onView?.(
                          role,
                        )
                      }
                    >
                      <Icon
                        name="edit"
                        size={12}
                      />
                      View
                    </Button>

                    {canManage &&
                    !role.is_system ? (
                      <Button
                        type="button"
                        variant="danger"
                        size="sm"
                        onClick={() =>
                          onDelete?.(
                            role,
                          )
                        }
                      >
                        Delete
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ),
          )}
        </tbody>
      </table>
    </TableShell>
  );
}
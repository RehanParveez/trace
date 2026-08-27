import type {Member,
} from "../types/organization.types";
import {formatDateTime, getMemberFullName, getMemberInitials,
} from "../utils/organization.utils";
import {Avatar, Badge, Button, Icon,
} from "./OrganizationUi";

interface MemberRowProps {
  member: Member;
  canManage?: boolean;
  onRoleChange?: (
    member: Member,
  ) => void;
  onStatusChange?: (
    member: Member,
  ) => void;
  onView?: (
    member: Member,
  ) => void;
}

export function MemberRow({
  member,
  canManage = false,
  onRoleChange,
  onStatusChange,
  onView,
}: MemberRowProps) {
  return (
    <tr className="border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]">
      <td className="px-4 py-3.5">
        <button
          type="button"
          onClick={() =>
            onView?.(member)
          }
          className="flex min-w-[220px] items-center gap-3 text-left"
        >
          <Avatar
            initials={getMemberInitials(
              member,
            )}
            size="sm"
          />

          <span className="min-w-0">
            <span className="block truncate text-[12.5px] font-semibold text-[#191410]">
              {getMemberFullName(
                member,
              )}
            </span>

            <span className="mt-0.5 block truncate text-[10.5px] text-[#6b6152]">
              {member.email}
            </span>
          </span>
        </button>
      </td>

      <td className="px-4 py-3.5">
        <span className="text-[11.5px] font-semibold text-[#332a21]">
          {member.role.name}
        </span>

        {member.role.is_system ? (
          <span className="ml-2 text-[9px] uppercase tracking-[0.08em] text-[#a2957c]">
            System
          </span>
        ) : null}
      </td>

      <td className="px-4 py-3.5">
        <Badge
          tone={
            member.is_active
              ? "green"
              : "slate"
          }
        >
          {member.is_active
            ? "Active"
            : "Inactive"}
        </Badge>
      </td>

      <td className="px-4 py-3.5 text-[11px] text-[#6b6152]">
        {formatDateTime(
          member.last_login_at,
        )}
      </td>

      <td className="px-4 py-3.5">
        {canManage ? (
          <div className="flex justify-end gap-1.5">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() =>
                onRoleChange?.(
                  member,
                )
              }
            >
              <Icon
                name="shield"
                size={12}
              />
              Role
            </Button>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() =>
                onStatusChange?.(
                  member,
                )
              }
            >
              {member.is_active
                ? "Deactivate"
                : "Activate"}
            </Button>
          </div>
        ) : null}
      </td>
    </tr>
  );
}
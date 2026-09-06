import type { Member } from "../types/organization.types";
import {formatDateTime, formatRelativeTime, getMemberFullName, getMemberInitials,
} from "../utils/organization.utils";
import { Avatar, Badge, DropdownMenu, type MenuAction } from "./OrganizationUi";

interface MemberRowProps {
  member: Member;
  canManage?: boolean;
  currentUserId?: string;
  onRoleChange?: (member: Member) => void;
  onStatusChange?: (member: Member) => void;
  onView?: (member: Member) => void;
}

export function MemberRow({
  member,
  canManage = false,
  currentUserId,
  onRoleChange,
  onStatusChange,
  onView,
}: MemberRowProps) {
  const isSelf = member.id === currentUserId;

  const actions: MenuAction[] = [
    {
      label: "View member",
      icon: "user",
      onSelect: () => onView?.(member),
    },
    {
      label: "Change role",
      icon: "shield",
      onSelect: () => onRoleChange?.(member),
    },
    ...(isSelf
      ? []
      : [
          {
            label: member.is_active ? "Deactivate member" : "Activate member",
            icon: member.is_active ? "lock" : "check",
            tone: member.is_active ? "danger" : "default",
            onSelect: () => onStatusChange?.(member),
          } as MenuAction,
        ]),
  ];

  return (
    <tr className="border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]">
      <td className="px-4 py-3.5">
        <button
          type="button"
          onClick={() => onView?.(member)}
          className="flex min-w-[220px] items-center gap-3 text-left"
        >
          <Avatar initials={getMemberInitials(member)} size="sm" />

          <span className="min-w-0">
            <span className="block truncate text-[12.5px] font-semibold text-[#191410]">
              {getMemberFullName(member)}
            </span>

            <span className="mt-0.5 block truncate text-[10.5px] text-[#6b6152]">
              {member.email}
            </span>
          </span>
        </button>
      </td>

      <td className="px-4 py-3.5">
        <div className="flex items-center gap-2">
          <span className="text-[11.5px] font-semibold text-[#332a21]">
            {member.role.name}
          </span>

          {member.role.is_system ? <Badge tone="blue">System</Badge> : null}
        </div>
      </td>

      <td className="px-4 py-3.5">
        <Badge tone={member.is_active ? "green" : "slate"}>
          {member.is_active ? "Active" : "Inactive"}
        </Badge>
      </td>

      <td
        className="px-4 py-3.5 font-mono text-[11px] text-[#6b6152]"
        title={formatDateTime(member.last_login_at)}
      >
        {formatRelativeTime(member.last_login_at)}
      </td>

      <td className="px-4 py-3.5 text-right">
        {canManage ? <DropdownMenu items={actions} /> : null}
      </td>
    </tr>
  );
}

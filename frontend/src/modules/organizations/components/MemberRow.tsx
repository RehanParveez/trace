import type { Member } from "../types/organization.types";
import {formatDateTime, formatRelativeTime, getMemberFullName, getMemberInitials,
} from "../utils/organization.utils";
import { Avatar, Badge, DropdownMenu, type MenuAction } from "./OrganizationUi";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  const isSelf = member.id === currentUserId;

  const actions: MenuAction[] = [
    {
      label: t("members.viewMember"),
      icon: "user",
      onSelect: () => onView?.(member),
    },
    {
      label: t("members.changeRole"),
      icon: "shield",
      onSelect: () => onRoleChange?.(member),
    },
    ...(isSelf
      ? []
      : [
          {
            label: member.is_active ? t("members.deactivateMember") : t("members.activateMember"),
            icon: member.is_active ? "lock" : "check",
            tone: member.is_active ? "danger" : "default",
            onSelect: () => onStatusChange?.(member),
          } as MenuAction,
        ]),
  ];

  return (
    <tr className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
      <td className="px-4 py-3.5">
        <button
          type="button"
          onClick={() => onView?.(member)}
          className="flex min-w-[220px] items-center gap-3 rounded-[6px] text-left outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)]"
        >
          <Avatar initials={getMemberInitials(member)} size="sm" />

          <span className="min-w-0">
            <span className="block truncate text-[14px] font-semibold text-[var(--color-text-primary)]">
              {getMemberFullName(member)}
            </span>

            <span className="mt-0.5 block truncate text-[12px] text-[var(--color-text-secondary)]">
              {member.email}
            </span>
          </span>
        </button>
      </td>

      <td className="px-4 py-3.5">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-[var(--color-text-primary)]">
            {member.role.name}
          </span>

          {member.role.is_system ? <Badge tone="blue">{t("members.systemBadge")}</Badge> : null}
        </div>
      </td>

      <td className="px-4 py-3.5">
        <Badge tone={member.is_active ? "green" : "slate"}>
          {member.is_active ? t("members.active") : t("members.inactive")}
        </Badge>
      </td>

      <td
        className="px-4 py-3.5 font-mono text-[12px] text-[var(--color-text-secondary)]"
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

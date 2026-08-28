import type { Invitation, Member, Role } from "../types/organization.types";
 
export function getMemberFullName(member: Member): string {
  return `${member.first_name} ${member.last_name}`.trim() || member.email;
}

export function getMemberInitials(member: Member): string {
  const first = member.first_name?.charAt(0) ?? "";
  const last = member.last_name?.charAt(0) ?? "";
 
  return (
    `${first}${last}`.toUpperCase() || member.email.charAt(0).toUpperCase()
  );
}
 
export function getOrganizationInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
 
  if (words.length === 0) {
    return "OR";
  }
 
  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase();
  }
 
  return `${words[0].charAt(0)}${words[1].charAt(0)}`.toUpperCase();
}
 
export function formatRoleName(role: Role): string {
  return role.name;
}
 
export function isSystemRole(role: Role): boolean {
  return role.is_system;
}
 
export function isInvitationAccepted(invitation: Invitation): boolean {
  return invitation.accepted_at !== null;
}
 
export function isInvitationRevoked(invitation: Invitation): boolean {
  return invitation.revoked_at !== null;
}
 
export function isInvitationExpired(invitation: Invitation): boolean {
  if (invitation.accepted_at !== null || invitation.revoked_at !== null) {
    return false;
  }
 
  return new Date(invitation.expires_at).getTime() <= Date.now();
}
 
export function getInvitationStatus(
  invitation: Invitation,
): "accepted" | "revoked" | "expired" | "pending" {
  if (isInvitationAccepted(invitation)) {
    return "accepted";
  }
 
  if (isInvitationRevoked(invitation)) {
    return "revoked";
  }
 
  if (isInvitationExpired(invitation)) {
    return "expired";
  }
 
  return "pending";
}
 
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
 
  const date = new Date(value);
 
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
 
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    date,
  );
}
 
export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Never";
  }
 
  const date = new Date(value);
 
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
 
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
 
/**
 * Short, human relative time ("2m ago", "3h ago", "5d ago") used anywhere
 * space is tight — table cells, activity rows — with `formatDateTime`
 * available as the precise fallback (e.g. in a tooltip).
 */
export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) {
    return "Never";
  }
 
  const date = new Date(value);
 
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
 
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.round(diffMs / 1000);
 
  if (diffSec < 60) {
    return "Just now";
  }
 
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) {
    return `${diffMin}m ago`;
  }
 
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) {
    return `${diffHour}h ago`;
  }
 
  const diffDay = Math.round(diffHour / 24);
  if (diffDay < 30) {
    return `${diffDay}d ago`;
  }
 
  return formatDate(value);
}
 
export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}
 
export function getInvitationStatusTone(
  status: ReturnType<typeof getInvitationStatus>,
): "green" | "red" | "gold" | "slate" {
  if (status === "accepted") {
    return "green";
  }
 
  if (status === "revoked") {
    return "red";
  }
 
  if (status === "expired") {
    return "gold";
  }
 
  return "slate";
}
 
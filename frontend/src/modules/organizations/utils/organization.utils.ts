import type {Invitation, Member, Role,
} from "../types/organization.types";

export function getMemberFullName(
  member: Member,
): string {
  return (
    `${member.first_name} ${member.last_name}`.trim() ||
    member.email
  );
}

export function getMemberInitials(
  member: Member,
): string {
  const first =
    member.first_name?.charAt(0) ?? "";

  const last =
    member.last_name?.charAt(0) ?? "";

  return (
    `${first}${last}`.toUpperCase() ||
    member.email.charAt(0).toUpperCase()
  );
}

export function formatRoleName(
  role: Role,
): string {
  return role.name;
}

export function isSystemRole(
  role: Role,
): boolean {
  return role.is_system;
}

export function isInvitationAccepted(
  invitation: Invitation,
): boolean {
  return invitation.accepted_at !== null;
}

export function isInvitationRevoked(
  invitation: Invitation,
): boolean {
  return invitation.revoked_at !== null;
}

export function isInvitationExpired(
  invitation: Invitation,
): boolean {
  if (
    invitation.accepted_at !== null ||
    invitation.revoked_at !== null
  ) {
    return false;
  }

  return (
    new Date(invitation.expires_at).getTime() <=
    Date.now()
  );
}

export function getInvitationStatus(
  invitation: Invitation,
):
  | "accepted"
  | "revoked"
  | "expired"
  | "pending" {
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

export function formatDate(
  value: string | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(date);
}

export function formatDateTime(
  value: string | null | undefined,
): string {
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

export function formatCompactNumber(
  value: number,
): string {
  return new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function getInvitationStatusTone(
  status: ReturnType<
    typeof getInvitationStatus
  >,
):
  | "green"
  | "red"
  | "gold"
  | "slate" {
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
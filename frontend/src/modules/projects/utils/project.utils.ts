import type {ProjectMemberRole, ProjectStatus,
} from "../types/project.types";

export function formatProjectStatus(
  status: ProjectStatus,
): string {
  switch (status) {
    case "PLANNING":
      return "Planning";

    case "ACTIVE":
      return "Active";

    case "ON_HOLD":
      return "On hold";

    case "COMPLETED":
      return "Completed";

    case "CANCELLED":
      return "Cancelled";

    default:
      return status;
  }
}

export function getProjectStatusTone(
  status: ProjectStatus,
): "green" | "gold" | "red" | "slate" | "blue" {
  switch (status) {
    case "ACTIVE":
      return "green";

    case "PLANNING":
      return "blue";

    case "ON_HOLD":
      return "gold";

    case "COMPLETED":
      return "green";

    case "CANCELLED":
      return "red";

    default:
      return "slate";
  }
}

export function formatProjectMemberRole(
  role: ProjectMemberRole,
): string {
  switch (role) {
    case "MANAGER":
      return "Manager";

    case "ENGINEER":
      return "Engineer";

    case "SUPERVISOR":
      return "Supervisor";

    case "SITE_MANAGER":
      return "Site manager";

    case "MEMBER":
      return "Member";

    default:
      return role;
  }
}

export function formatProjectDate(
  value: string | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function getProjectMemberName(
  member: {
    user?: {
      first_name?: string | null;
      last_name?: string | null;
      email?: string | null;
    } | null;
  },
): string {
  const first =
    member.user?.first_name?.trim() ?? "";

  const last =
    member.user?.last_name?.trim() ?? "";

  const name =
    `${first} ${last}`.trim();

  return (
    name ||
    member.user?.email ||
    "Project member"
  );
}
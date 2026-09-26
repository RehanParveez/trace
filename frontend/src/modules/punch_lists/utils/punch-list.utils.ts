import type { PunchListItemStatus, PunchListStatus } from "../types/punch-list.types";

export function formatPunchListItemStatus(status: PunchListItemStatus): string {
  switch (status) {
    case "OPEN": return "Open";
    case "IN_PROGRESS": return "In progress";
    case "RESOLVED": return "Resolved";
    case "WAIVED": return "Waived";
    default: return status;
  }
}

export function getPunchListItemStatusTone(status: PunchListItemStatus): "green" | "gold" | "blue" | "slate" {
  switch (status) {
    case "RESOLVED": return "green";
    case "WAIVED": return "slate";
    case "IN_PROGRESS": return "blue";
    default: return "gold";
  }
}

export function getPunchListStatusTone(status: PunchListStatus): "green" | "gold" {
  return status === "CLOSED" ? "green" : "gold";
}

export function formatPunchListDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}
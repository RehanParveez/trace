import type { AuditAction, AuditEntityType } from "../types/audit.types";

export function formatAuditAction(action: AuditAction): string {
  switch (action) {
    case "CREATE": return "Created";
    case "UPDATE": return "Updated";
    case "DELETE": return "Deleted";
    case "APPROVE": return "Approved";
    case "REJECT": return "Rejected";
    case "STATUS_CHANGE": return "Status changed";
    default: return action;
  }
}

export function getAuditActionTone(action: AuditAction): "green" | "red" | "gold" | "blue" | "slate" {
  switch (action) {
    case "CREATE": case "APPROVE": return "green";
    case "DELETE": case "REJECT": return "red";
    case "UPDATE": case "STATUS_CHANGE": return "gold";
    default: return "slate";
  }
}

export function formatEntityType(type: AuditEntityType): string {
  return type.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatAuditTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
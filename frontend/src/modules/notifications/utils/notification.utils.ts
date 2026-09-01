import type { NotificationType } from "../types/notification.types";

export function getNotificationIcon(
  type: NotificationType,
): "check" | "alert" | "site" | "mail" | "users" | "settings" {
  switch (type) {
    case "DRAWING_PARSED": case "BOQ_ITEM_APPROVED": case "PROGRESS_CLAIM_APPROVED":
      return "check";
    case "DRAWING_FAILED": case "PROGRESS_CLAIM_REJECTED": case "SUBSCRIPTION_USAGE_WARNING":
      return "alert";
    case "SITE_PHOTO_NEEDS_PROJECT":
      return "site";
    case "ORGANIZATION_INVITATION_RECEIVED": case "PROGRESS_CLAIM_SUBMITTED":
      return "mail";
    case "MEMBER_JOINED":
      return "users";
    default:
      return "settings";
  }
}

export function formatNotificationTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const diffMin = Math.round((Date.now() - date.getTime()) / 60000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  const diffDay = Math.round(diffHour / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short" }).format(date);
}
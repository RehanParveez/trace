import { authenticatedRequest } from "./client";
import type {AppNotification, MessageResponse, NotificationUnreadCount,
} from "./types";

export type NotificationListParams = {
  unread_only?: boolean;
  skip?: number;
  limit?: number;
};

function buildQuery(params: NotificationListParams): string {
  const query = new URLSearchParams();

  if (params.unread_only) query.set("unread_only", "true");
  if (params.skip !== undefined) query.set("skip", String(params.skip));
  if (params.limit !== undefined) query.set("limit", String(params.limit));

  const value = query.toString();
  return value ? `?${value}` : "";
}

export function listNotifications(
  params: NotificationListParams = {},
): Promise<AppNotification[]> {
  return authenticatedRequest<AppNotification[]>(
    `/notifications${buildQuery(params)}`,
  );
}

export function getUnreadNotificationCount(): Promise<NotificationUnreadCount> {
  return authenticatedRequest<NotificationUnreadCount>(
    "/notifications/unread-count",
  );
}

export function markNotificationRead(
  notificationId: string,
): Promise<AppNotification> {
  return authenticatedRequest<AppNotification>(
    `/notifications/${notificationId}/read`,
    { method: "POST" },
  );
}

export function markAllNotificationsRead(): Promise<MessageResponse> {
  return authenticatedRequest<MessageResponse>("/notifications/read-all", {
    method: "POST",
  });
}
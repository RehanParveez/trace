import { apiClient } from "../../../shared/api/client";
import type { Notification, UnreadCountResponse } from "../types/notification.types";

export const notificationsApi = {
  async list(unreadOnly = false, skip = 0, limit = 50): Promise<Notification[]> {
    const response = await apiClient.get<Notification[]>("/notifications", {
      params: { unread_only: unreadOnly, skip, limit },
    });
    return response.data;
  },

  async getUnreadCount(): Promise<UnreadCountResponse> {
    const response = await apiClient.get<UnreadCountResponse>("/notifications/unread-count");
    return response.data;
  },

  async markRead(notificationId: string): Promise<Notification> {
    const response = await apiClient.post<Notification>(`/notifications/${notificationId}/read`);
    return response.data;
  },

  async markAllRead(): Promise<void> {
    await apiClient.post("/notifications/read-all");
  },
};
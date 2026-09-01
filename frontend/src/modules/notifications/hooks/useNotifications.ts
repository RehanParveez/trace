import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../api/notifications.api";

export const notificationKeys = {
  all: ["notifications"] as const,
  list: (unreadOnly: boolean) => [...notificationKeys.all, "list", unreadOnly] as const,
  unreadCount: () => [...notificationKeys.all, "unread-count"] as const,
};

export function useNotifications(unreadOnly = false) {
  return useQuery({
    queryKey: notificationKeys.list(unreadOnly),
    queryFn: () => notificationsApi.list(unreadOnly),
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.unreadCount(),
    queryFn: notificationsApi.getUnreadCount,
    refetchInterval: 30000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) => notificationsApi.markRead(notificationId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}
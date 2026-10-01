import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router } from "expo-router";
import { restoreSession } from "../api/client";
import {getUnreadNotificationCount, listNotifications, markAllNotificationsRead, markNotificationRead,
} from "../api/notifications";
import type { AppNotification } from "../api/types";

const PAGE_SIZE = 100;

type MobileDestination =
  | { pathname: "/organization/subscription" }
  | { pathname: "/organization/invitations" }
  | { pathname: "/projects/[projectId]"; params: { projectId: string } };

function resolveMobileDestination(
  linkPath: string | null,
): MobileDestination | null {
  if (!linkPath) return null;

  if (linkPath === "/app/subscription") {
    return { pathname: "/organization/subscription" };
  }
  if (linkPath === "/app/invitations") {
    return { pathname: "/organization/invitations" };
  }

  const projectMatch = /^\/app\/projects\/([^/?#]+)\/?$/.exec(linkPath);
  if (projectMatch) {
    return {
      pathname: "/projects/[projectId]",
      params: { projectId: projectMatch[1] },
    };
  }

  return null;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function NotificationsScreen() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }

        const [rows, count] = await Promise.all([
          listNotifications({
            unread_only: unreadOnly,
            skip: 0,
            limit: PAGE_SIZE,
          }),
          getUnreadNotificationCount(),
        ]);

        if (!active) return;
        setNotifications(rows);
        setUnreadCount(count.unread_count);
        setSkip(rows.length);
        setHasMore(rows.length === PAGE_SIZE);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load notifications.",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [unreadOnly, attempt]);

  async function handleMarkRead(notification: AppNotification) {
    if (notification.is_read || busyId) return;

    setBusyId(notification.id);
    setError("");

    try {
      await markNotificationRead(notification.id);
      setAttempt((value) => value + 1);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not mark as read.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleMarkAllRead() {
    if (markingAll || unreadCount === 0) return;

    setMarkingAll(true);
    setError("");

    try {
      await markAllNotificationsRead();
      setAttempt((value) => value + 1);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not mark all as read.",
      );
    } finally {
      setMarkingAll(false);
    }
  }

  async function handleOpen(notification: AppNotification) {
    const destination = resolveMobileDestination(notification.link_path);
    if (!destination) return;

    if (!notification.is_read) {
      try {
        await markNotificationRead(notification.id);
        setAttempt((value) => value + 1);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not mark as read.",
        );
        return;
      }
    }

    router.push(destination as never);
  }

  async function loadMore() {
    if (loadingMore || !hasMore) return;

    setLoadingMore(true);
    setError("");

    try {
      const rows = await listNotifications({
        unread_only: unreadOnly,
        skip,
        limit: PAGE_SIZE,
      });
      setNotifications((current) => [...current, ...rows]);
      setSkip((current) => current + rows.length);
      setHasMore(rows.length === PAGE_SIZE);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load more notifications.",
      );
    } finally {
      setLoadingMore(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading notifications…</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.heading}>
        <View>
          <Text style={styles.eyebrow}>ACTIVITY</Text>
          <Text style={styles.title}>Notifications</Text>
        </View>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>{unreadCount} unread</Text>
        </View>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <View style={styles.toolbar}>
        <Pressable
          style={[styles.filter, unreadOnly && styles.filterSelected]}
          onPress={() => setUnreadOnly((value) => !value)}
          accessibilityRole="button"
        >
          <Text
            style={[
              styles.filterText,
              unreadOnly && styles.filterTextSelected,
            ]}
          >
            {unreadOnly ? "Showing unread" : "Show unread only"}
          </Text>
        </Pressable>

        <Pressable
          onPress={() => setAttempt((value) => value + 1)}
          accessibilityRole="button"
        >
          <Text style={styles.link}>Refresh</Text>
        </Pressable>
      </View>

      <Pressable
        style={[styles.button, (markingAll || unreadCount === 0) && styles.disabled]}
        onPress={() => void handleMarkAllRead()}
        disabled={markingAll || unreadCount === 0}
        accessibilityRole="button"
      >
        <Text style={styles.buttonText}>
          {markingAll ? "Marking…" : "Mark all read"}
        </Text>
      </Pressable>

      {notifications.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>
            {unreadOnly ? "No unread notifications." : "No notifications yet."}
          </Text>
        </View>
      ) : (
        notifications.map((notification) => {
          const destination = resolveMobileDestination(notification.link_path);

          return (
            <View
              key={notification.id}
              style={[
                styles.card,
                !notification.is_read && styles.unreadCard,
              ]}
            >
              <View style={styles.heading}>
                <Text style={styles.cardTitle}>{notification.title}</Text>
                {!notification.is_read ? (
                  <Text style={styles.unreadBadge}>Unread</Text>
                ) : null}
              </View>

              <Text style={styles.type}>{notification.type.replaceAll("_", " ")}</Text>

              {notification.body ? (
                <Text style={styles.body}>{notification.body}</Text>
              ) : null}

              <Text style={styles.muted}>{formatDate(notification.created_at)}</Text>

              <View style={styles.actions}>
                {!notification.is_read ? (
                  <Pressable
                    style={styles.secondaryButton}
                    disabled={busyId === notification.id}
                    onPress={() => void handleMarkRead(notification)}
                    accessibilityRole="button"
                  >
                    <Text style={styles.secondaryButtonText}>
                      {busyId === notification.id ? "Saving…" : "Mark read"}
                    </Text>
                  </Pressable>
                ) : null}

                {destination ? (
                  <Pressable
                    style={styles.secondaryButton}
                    onPress={() => void handleOpen(notification)}
                    accessibilityRole="button"
                  >
                    <Text style={styles.secondaryButtonText}>Open</Text>
                  </Pressable>
                ) : null}
              </View>
            </View>
          );
        })
      )}

      {hasMore ? (
        <Pressable
          style={[styles.button, loadingMore && styles.disabled]}
          onPress={() => void loadMore()}
          disabled={loadingMore}
          accessibilityRole="button"
        >
          <Text style={styles.buttonText}>
            {loadingMore ? "Loading…" : "Load more"}
          </Text>
        </Pressable>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 30, paddingBottom: 40, backgroundColor: "#F4F6F8" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8" },
  heading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  eyebrow: { color: "#8A7B67", fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: "#17212F", fontSize: 25, fontWeight: "800", marginTop: 5, marginBottom: 12 },
  countBadge: { backgroundColor: "#EAF0F7", paddingHorizontal: 10, paddingVertical: 7, borderRadius: 20 },
  countText: { color: "#183153", fontWeight: "700" },
  toolbar: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  filter: { borderWidth: 1, borderColor: "#D0D5DD", paddingHorizontal: 11, paddingVertical: 8, borderRadius: 20 },
  filterSelected: { backgroundColor: "#183153", borderColor: "#183153" },
  filterText: { color: "#344054", fontWeight: "600" },
  filterTextSelected: { color: "#FFFFFF" },
  card: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E4E7EC", borderRadius: 14, padding: 16, marginTop: 12 },
  unreadCard: { borderColor: "#183153" },
  cardTitle: { flex: 1, color: "#17212F", fontSize: 16, fontWeight: "700" },
  unreadBadge: { color: "#183153", backgroundColor: "#EAF0F7", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 16, fontSize: 11, fontWeight: "700" },
  type: { color: "#8A7B67", fontSize: 11, fontWeight: "700", marginTop: 8 },
  body: { color: "#344054", lineHeight: 20, marginTop: 8, marginBottom: 8 },
  muted: { color: "#667085", lineHeight: 20, marginTop: 6 },
  link: { color: "#183153", fontWeight: "700" },
  error: { color: "#B42318", lineHeight: 20, marginBottom: 8 },
  actions: { flexDirection: "row", gap: 8, flexWrap: "wrap", marginTop: 8 },
  button: { minHeight: 44, backgroundColor: "#183153", borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 11, marginBottom: 6 },
  buttonText: { color: "#FFFFFF", fontWeight: "700" },
  secondaryButton: { borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 9, paddingHorizontal: 12, paddingVertical: 9 },
  secondaryButtonText: { color: "#183153", fontWeight: "700" },
  disabled: { opacity: 0.55 },
});
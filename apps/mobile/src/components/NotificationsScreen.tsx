import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { useTranslation } from "react-i18next";
import { router } from "expo-router";
import { restoreSession } from "../api/client";
import {getUnreadNotificationCount, listNotifications, markAllNotificationsRead, markNotificationRead,
} from "../api/notifications";
import type { AppNotification } from "../api/types";
import LanguageSwitcher from "./LanguageSwitcher";

const PAGE_SIZE = 10;

type MobileDestination =
  | { pathname: "/organization/subscription" }
  | { pathname: "/organization/invitations" }
  | { pathname: "/projects/[projectId]"; params: { projectId: string } };

const C = {
  background: "#F3EEE4",
  surface: "#FFFEFB",
  surfaceMuted: "#F7F1E7",
  navy: "#080D18",
  text: "#17212F",
  secondary: "#5C5347",
  muted: "#82796C",
  border: "#E5DCCB",
  gold: "#D9A441",
  red: "#A33A32",
  redBg: "#F9E9E5",
};

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

function formatDate(value: string, locale?: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(locale);
}

function humanize(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function NotificationsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = i18n.resolvedLanguage || i18n.language;

  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [pageNumber, setPageNumber] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");

  function notificationTypeLabel(type: string): string {
    return t(`notifications.type.${type.toLowerCase()}`, {
      defaultValue: humanize(type),
    });
  }

  async function fetchPage(page: number) {
    const [rows, nextRows] = await Promise.all([
      listNotifications({
        unread_only: unreadOnly,
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
      listNotifications({
        unread_only: unreadOnly,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    ]);

    return {
      rows,
      hasNext: nextRows.length > 0,
    };
  }

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      setPageNumber(1);
      setHasNextPage(false);

      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }

        const [page, count] = await Promise.all([
          fetchPage(1),
          getUnreadNotificationCount(),
        ]);

        if (!active) return;
        setNotifications(page.rows);
        setUnreadCount(count.unread_count);
        setPageNumber(1);
        setHasNextPage(page.hasNext);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : t("notifications.loadFailure"),
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
  }, [unreadOnly, attempt, t]);

  async function goToPage(targetPage: number) {
    if (targetPage < 1 || targetPage === pageNumber || loading) return;

    setLoading(true);
    setError("");

    try {
      const page = await fetchPage(targetPage);
      setNotifications(page.rows);
      setPageNumber(targetPage);
      setHasNextPage(page.hasNext);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("notifications.loadFailure"),
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkRead(notification: AppNotification) {
    if (notification.is_read || busyId) return;

    setBusyId(notification.id);
    setError("");

    try {
      await markNotificationRead(notification.id);
      setAttempt((value) => value + 1);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("notifications.markReadFailure"),
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
        err instanceof Error
          ? err.message
          : t("notifications.markAllReadFailure"),
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
          err instanceof Error
            ? err.message
            : t("notifications.markReadFailure"),
        );
        return;
      }
    }

    router.push(destination as never);
  }

  const lastAvailablePage = pageNumber + (hasNextPage ? 1 : 0);
  const firstVisiblePage = Math.max(
    1,
    Math.min(pageNumber - 2, lastAvailablePage - 4),
  );
  const visiblePages = Array.from(
    {
      length: Math.min(5, lastAvailablePage - firstVisiblePage + 1),
    },
    (_, index) => firstVisiblePage + index,
  );

  if (loading) {
    return (
      <View style={styles.page}>
        <View style={[styles.heading, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("notifications.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>

        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("notifications.loading")}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
    >
      <View style={[styles.heading, isUrdu && styles.rtlRow]}>
        <View style={styles.headerContent}>
          <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
            {t("notifications.eyebrow")}
          </Text>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("notifications.pageTitle")}
          </Text>
        </View>
        <LanguageSwitcher />
      </View>

      <View style={[styles.countRow, isUrdu && styles.rtlRow]}>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>
            {t("notifications.unreadCount", { count: unreadCount })}
          </Text>
        </View>
      </View>

      {error ? (
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error}
        </Text>
      ) : null}

      <View style={[styles.toolbar, isUrdu && styles.rtlRow]}>
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
            {unreadOnly
              ? t("notifications.showingUnread")
              : t("notifications.showUnreadOnly")}
          </Text>
        </Pressable>

        <Pressable
          onPress={() => setAttempt((value) => value + 1)}
          accessibilityRole="button"
        >
          <Text style={styles.link}>{t("notifications.refresh")}</Text>
        </Pressable>
      </View>

      <Pressable
        style={[
          styles.button,
          (markingAll || unreadCount === 0) && styles.disabled,
        ]}
        onPress={() => void handleMarkAllRead()}
        disabled={markingAll || unreadCount === 0}
        accessibilityRole="button"
      >
        <Text style={styles.buttonText}>
          {markingAll
            ? t("notifications.marking")
            : t("notifications.markAllRead")}
        </Text>
      </Pressable>

      {notifications.length === 0 ? (
        <View style={styles.card}>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {unreadOnly
              ? t("notifications.noUnread")
              : t("notifications.noneYet")}
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
              <View style={[styles.heading, isUrdu && styles.rtlRow]}>
                <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                  {notification.title}
                </Text>
                {!notification.is_read ? (
                  <Text style={styles.unreadBadge}>
                    {t("notifications.unread")}
                  </Text>
                ) : null}
              </View>

              <Text style={[styles.type, isUrdu && styles.rtlText]}>
                {notificationTypeLabel(notification.type)}
              </Text>

              {notification.body ? (
                <Text style={[styles.body, isUrdu && styles.rtlText]}>
                  {notification.body}
                </Text>
              ) : null}

              <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                {formatDate(notification.created_at, locale)}
              </Text>

              <View style={[styles.actions, isUrdu && styles.rtlRow]}>
                {!notification.is_read ? (
                  <Pressable
                    style={styles.secondaryButton}
                    disabled={busyId === notification.id}
                    onPress={() => void handleMarkRead(notification)}
                    accessibilityRole="button"
                  >
                    <Text style={styles.secondaryButtonText}>
                      {busyId === notification.id
                        ? t("notifications.saving")
                        : t("notifications.markRead")}
                    </Text>
                  </Pressable>
                ) : null}

                {destination ? (
                  <Pressable
                    style={styles.secondaryButton}
                    onPress={() => void handleOpen(notification)}
                    accessibilityRole="button"
                  >
                    <Text style={styles.secondaryButtonText}>
                      {t("notifications.open")}
                    </Text>
                  </Pressable>
                ) : null}
              </View>
            </View>
          );
        })
      )}

      {notifications.length > 0 ? (
        <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
          <Pressable
            style={[
              styles.pageNavButton,
              pageNumber === 1 && styles.disabled,
            ]}
            disabled={pageNumber === 1 || loading}
            onPress={() => void goToPage(pageNumber - 1)}
            accessibilityRole="button"
          >
            <Text style={styles.pageNavText}>
              {t("notifications.previousPage")}
            </Text>
          </Pressable>

          <View style={[styles.pageNumbers, isUrdu && styles.rtlRow]}>
            {visiblePages.map((page) => (
              <Pressable
                key={page}
                style={[
                  styles.pageNumber,
                  page === pageNumber && styles.pageNumberSelected,
                ]}
                disabled={loading || page === pageNumber}
                onPress={() => void goToPage(page)}
                accessibilityRole="button"
                accessibilityState={{ selected: page === pageNumber }}
              >
                <Text
                  style={[
                    styles.pageNumberText,
                    page === pageNumber && styles.pageNumberTextSelected,
                  ]}
                >
                  {page}
                </Text>
              </Pressable>
            ))}
          </View>

          <Pressable
            style={[
              styles.pageNavButton,
              !hasNextPage && styles.disabled,
            ]}
            disabled={!hasNextPage || loading}
            onPress={() => void goToPage(pageNumber + 1)}
            accessibilityRole="button"
          >
            <Text style={styles.pageNavText}>
              {t("notifications.nextPage")}
            </Text>
          </Pressable>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: C.background },
  heading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10 },
  headerContent: { flex: 1 },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 27, fontWeight: "800", marginTop: 5, marginBottom: 8, letterSpacing: -0.4 },
  countRow: { flexDirection: "row", justifyContent: "flex-end", marginBottom: 12 },
  countBadge: { backgroundColor: C.surfaceMuted, borderWidth: 1, borderColor: C.border, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 99 },
  countText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  toolbar: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 8 },
  filter: { borderWidth: 1, borderColor: C.border, paddingHorizontal: 12, paddingVertical: 9, borderRadius: 99, backgroundColor: C.surface },
  filterSelected: { backgroundColor: C.navy, borderColor: C.navy },
  filterText: { color: C.secondary, fontSize: 12, fontWeight: "700" },
  filterTextSelected: { color: C.surface },
  card: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, borderRadius: 15, padding: 16, marginTop: 12 },
  unreadCard: { borderColor: C.gold },
  cardTitle: { flex: 1, color: C.text, fontSize: 16, fontWeight: "800" },
  unreadBadge: { color: C.navy, backgroundColor: C.surfaceMuted, paddingHorizontal: 9, paddingVertical: 5, borderRadius: 99, fontSize: 11, fontWeight: "800" },
  type: { color: C.muted, fontSize: 11, fontWeight: "800", marginTop: 8 },
  body: { color: C.secondary, lineHeight: 20, marginTop: 8, marginBottom: 8 },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  link: { color: C.navy, fontSize: 13, fontWeight: "800" },
  error: { color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19, marginBottom: 12 },
  actions: { flexDirection: "row", gap: 8, flexWrap: "wrap", marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: C.border },
  button: { minHeight: 46, backgroundColor: C.navy, borderRadius: 11, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 12, marginBottom: 6 },
  buttonText: { color: C.surface, fontSize: 13, fontWeight: "800" },
  secondaryButton: { borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, paddingHorizontal: 12, paddingVertical: 10 },
  secondaryButtonText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 14, padding: 10, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13 },
  pageNavButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: C.surfaceMuted },
  pageNavText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pageNumbers: { flexDirection: "row", alignItems: "center", gap: 5 },
  pageNumber: { minWidth: 36, height: 36, alignItems: "center", justifyContent: "center", borderRadius: 9, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  pageNumberSelected: { backgroundColor: C.navy, borderColor: C.navy },
  pageNumberText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  pageNumberTextSelected: { color: C.surface },
  disabled: { opacity: 0.45 },
});
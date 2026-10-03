import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { Link, router, Stack } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession, signOut } from "../../../api/client";
import { listProjects } from "../../../api/projects";
import type { Project } from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

const PAGE_SIZE = 5;

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

export default function ProjectsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [projects, setProjects] = useState<Project[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [canCreate, setCanCreate] = useState(false);

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

        if (active) {
          setCanCreate(
            user.role.permissions.some(
              (permission) => permission.key === "project.create",
            ),
          );
        }

        const result = await listProjects();
        if (active) {
          setProjects(result);
          setPage(1);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : t("projects.loadFailure"),
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
  }, [attempt, t]);

  async function handleSignOut() {
    setBusy(true);
    setError("");

    try {
      await signOut();
      router.replace("/");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("projects.signOutFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  const pages = pageCount(projects.length);
  const visibleProjects = paginate(projects, page);

  return (
    <>
      <Stack.Screen options={{ title: t("projects.title") }} />
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[styles.header, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Text style={[styles.brand, isUrdu && styles.rtlText]}>
              {t("projects.brand")}
            </Text>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("projects.title")}
            </Text>
            <Text style={[styles.subtitle, isUrdu && styles.rtlText]}>
              {t("projects.subtitle")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[styles.topActions, isUrdu && styles.rtlRow]}>
          <Link href="/organization" asChild>
            <Pressable style={styles.outlineButton} accessibilityRole="button">
              <Text style={[styles.outlineButtonText, isUrdu && styles.rtlText]}>
                {t("projects.organization")}
              </Text>
            </Pressable>
          </Link>

          <Pressable
            onPress={() => void handleSignOut()}
            disabled={busy}
            style={[styles.outlineButton, busy && styles.disabled]}
            accessibilityRole="button"
          >
            <Text style={[styles.outlineButtonText, isUrdu && styles.rtlText]}>
              {busy ? t("projects.signingOut") : t("projects.signOut")}
            </Text>
          </Pressable>
        </View>

        {canCreate ? (
          <Link href="/projects/new" asChild>
            <Pressable style={styles.createButton} accessibilityRole="button">
              <Text style={[styles.createButtonText, isUrdu && styles.rtlText]}>
                {t("projects.create")}
              </Text>
            </Pressable>
          </Link>
        ) : null}

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color={COLORS.navy} />
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("projects.loading")}
            </Text>
          </View>
        ) : error ? (
          <View>
            <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
            <Pressable
              style={styles.primaryButton}
              onPress={() => setAttempt((value) => value + 1)}
              accessibilityRole="button"
            >
              <Text style={[styles.primaryButtonText, isUrdu && styles.rtlText]}>
                {t("projects.tryAgain")}
              </Text>
            </Pressable>
          </View>
        ) : projects.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={[styles.emptyTitle, isUrdu && styles.rtlText]}>
              {t("projects.emptyTitle")}
            </Text>
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {canCreate
                ? t("projects.emptyCreate")
                : t("projects.emptyReadOnly")}
            </Text>
          </View>
        ) : (
          <>
            {visibleProjects.map((project) => (
              <Pressable
                key={project.id}
                style={styles.card}
                accessibilityRole="button"
                accessibilityLabel={t("projects.openProject", {
                  name: project.name,
                })}
                onPress={() =>
                  router.push({
                    pathname: "/projects/[projectId]",
                    params: { projectId: project.id },
                  })
                }
              >
                <View style={[styles.cardHeading, isUrdu && styles.rtlRow]}>
                  <Text style={[styles.projectName, isUrdu && styles.rtlText]}>
                    {project.name}
                  </Text>
                  <Text style={styles.cardArrow}>›</Text>
                </View>

                {project.code ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("projects.projectCode", { code: project.code })}
                  </Text>
                ) : null}

                {project.location ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {project.location}
                  </Text>
                ) : null}

                <Text style={[styles.status, isUrdu && styles.rtlText]}>
                  {t(`projects.status.${project.status.toLowerCase()}`, {
                    defaultValue: project.status.replaceAll("_", " "),
                  })}
                </Text>
              </Pressable>
            ))}

            {projects.length > PAGE_SIZE ? (
              <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
                <Pressable
                  style={[styles.pageButton, page <= 1 && styles.disabled]}
                  onPress={() =>
                    setPage((current) => Math.max(1, current - 1))
                  }
                  disabled={page <= 1}
                  accessibilityRole="button"
                >
                  <Text
                    style={[styles.pageButtonText, isUrdu && styles.rtlText]}
                  >
                    {t("projects.previous")}
                  </Text>
                </Pressable>
                <Text style={[styles.pageText, isUrdu && styles.rtlText]}>
                  {t("projects.pageOf", { page, pages })}
                </Text>
                <Pressable
                  style={[
                    styles.pageButton,
                    page >= pages && styles.disabled,
                  ]}
                  onPress={() =>
                    setPage((current) => Math.min(pages, current + 1))
                  }
                  disabled={page >= pages}
                  accessibilityRole="button"
                >
                  <Text
                    style={[styles.pageButtonText, isUrdu && styles.rtlText]}
                  >
                    {t("projects.next")}
                  </Text>
                </Pressable>
              </View>
            ) : null}
          </>
        )}
      </ScrollView>
    </>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#F7F3EC",
  navy: "#080D18",
  text: "#171C26",
  secondary: "#5C5347",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
  red: "#A63A32",
  redBackground: "#FBEAE7",
};

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 38, backgroundColor: COLORS.background },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 14 },
  headerCopy: { flex: 1 },
  rtlRow: { flexDirection: "row-reverse" },
  brand: { color: COLORS.gold, fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: COLORS.text, fontSize: 27, fontWeight: "800", marginTop: 5 },
  subtitle: { color: COLORS.secondary, fontSize: 13, lineHeight: 19, marginTop: 5 },
  topActions: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 10 },
  outlineButton: { minHeight: 40, justifyContent: "center", borderWidth: 1, borderColor: COLORS.border, backgroundColor: COLORS.surface, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9 },
  outlineButtonText: { color: COLORS.navy, fontSize: 12, fontWeight: "800" },
  createButton: { minHeight: 48, backgroundColor: COLORS.navy, borderRadius: 12, paddingHorizontal: 15, paddingVertical: 13, alignItems: "center", justifyContent: "center", marginBottom: 14 },
  createButtonText: { color: COLORS.surface, fontWeight: "800", fontSize: 14 },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 16, marginBottom: 12 },
  cardHeading: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10 },
  projectName: { flex: 1, color: COLORS.text, fontSize: 16, fontWeight: "800", marginBottom: 5 },
  cardArrow: { color: COLORS.gold, fontSize: 24, fontWeight: "700" },
  status: { color: COLORS.navy, backgroundColor: COLORS.surfaceMuted, borderRadius: 99, overflow: "hidden", alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 6, marginTop: 10, fontSize: 11, fontWeight: "800" },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 6, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginTop: 10, fontSize: 13, lineHeight: 19 },
  primaryButton: { minHeight: 44, backgroundColor: COLORS.navy, borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, marginTop: 10 },
  primaryButtonText: { color: COLORS.surface, fontSize: 13, fontWeight: "800" },
  center: { alignItems: "center", padding: 24, gap: 12 },
  emptyState: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 18, marginTop: 8 },
  emptyTitle: { color: COLORS.text, fontSize: 17, fontWeight: "800" },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, paddingVertical: 12 },
  pageButton: { minHeight: 40, justifyContent: "center", paddingHorizontal: 12, borderRadius: 10, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  pageButtonText: { color: COLORS.navy, fontSize: 12, fontWeight: "800" },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700" },
  disabled: { opacity: 0.5 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});
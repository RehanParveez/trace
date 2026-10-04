import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { Link, router } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession, signOut } from "../../../api/client";
import { listProjects } from "../../../api/projects";
import type { Project } from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  navy: "#080D18",
  text: "#171C26",
  secondary: "#5C5347",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
};

export default function ProjectsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [projects, setProjects] = useState<Project[]>([]);
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
        if (active) {
          setLoading(false);
        }
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

  function openProject(project: Project) {
    const projectId = project.id?.trim();

    if (!projectId) {
      setError(t("projects.missingProjectId"));
      return;
    }

    router.push({
      pathname: "/projects/[projectId]",
      params: { projectId },
    });
  }

  return (
    <ScrollView
      contentContainerStyle={styles.page}
      keyboardShouldPersistTaps="handled"
    >
      <View style={[styles.header, isUrdu && styles.rtlRow]}>
        <View style={styles.headerText}>
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

      <View style={[styles.headerActions, isUrdu && styles.rtlRow]}>
        <Link href="/organization" asChild>
          <Pressable accessibilityRole="button">
            <Text style={[styles.link, isUrdu && styles.rtlText]}>
              {t("projects.organization")}
            </Text>
          </Pressable>
        </Link>

        <Pressable
          onPress={handleSignOut}
          disabled={busy}
          accessibilityRole="button"
        >
          <Text style={[styles.link, isUrdu && styles.rtlText]}>
            {busy
              ? t("projects.signingOut")
              : t("projects.signOut")}
          </Text>
        </Pressable>
      </View>

      {canCreate ? (
        <Link href="/projects/new" asChild>
          <Pressable
            style={styles.createButton}
            accessibilityRole="button"
          >
            <Text
              style={[
                styles.createButtonText,
                isUrdu && styles.rtlText,
              ]}
            >
              {t("projects.createProject")}
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
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {error}
          </Text>

          <Pressable
            style={styles.retryButton}
            onPress={() => setAttempt((value) => value + 1)}
            accessibilityRole="button"
          >
            <Text style={[styles.retryButtonText, isUrdu && styles.rtlText]}>
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
              ? t("projects.emptyCanCreate")
              : t("projects.emptyCannotCreate")}
          </Text>
        </View>
      ) : (
        projects.map((project) => {
          const statusKey =
            `projects.status.${project.status.toLowerCase()}`;

          return (
            <Pressable
              key={project.id}
              style={styles.card}
              accessibilityRole="button"
              accessibilityLabel={t("projects.openProject", {
                name: project.name,
              })}
              onPress={() => openProject(project)}
            >
              <View style={[styles.cardHeading, isUrdu && styles.rtlRow]}>
                <Text style={[styles.projectName, isUrdu && styles.rtlText]}>
                  {project.name}
                </Text>
                <Text style={styles.cardArrow}>
                  {isUrdu ? "‹" : "›"}
                </Text>
              </View>

              {project.code ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {t("projects.code", { code: project.code })}
                </Text>
              ) : null}

              {project.location ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {project.location}
                </Text>
              ) : null}

              <Text style={[styles.status, isUrdu && styles.rtlText]}>
                {t(statusKey, {
                  defaultValue: project.status.replaceAll("_", " "),
                })}
              </Text>
            </Pressable>
          );
        })
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 28, paddingBottom: 40, backgroundColor: COLORS.background },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 14 },
  headerText: { flex: 1 },
  headerActions: { flexDirection: "row", justifyContent: "flex-end", alignItems: "center", gap: 20, marginBottom: 20 },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
  brand: { color: COLORS.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.2, textTransform: "uppercase" },
  title: { color: COLORS.text, fontSize: 27, fontWeight: "800", marginTop: 5 },
  subtitle: { color: COLORS.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  link: { color: COLORS.navy, fontSize: 13, fontWeight: "800" },
  createButton: { minHeight: 46, backgroundColor: COLORS.navy, borderRadius: 11, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 12, marginBottom: 16 },
  createButtonText: { color: COLORS.surface, fontSize: 13, fontWeight: "800" },
  center: { alignItems: "center", justifyContent: "center", padding: 24, gap: 12 },
  card: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 16, marginBottom: 12 },
  cardHeading: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10 },
  projectName: { flex: 1, color: COLORS.text, fontSize: 17, fontWeight: "800", marginBottom: 5 },
  cardArrow: { color: COLORS.gold, fontSize: 23, fontWeight: "700" },
  status: { color: COLORS.navy, backgroundColor: "#F7F3EC", borderRadius: 99, alignSelf: "flex-start", overflow: "hidden", paddingHorizontal: 10, paddingVertical: 6, marginTop: 10, fontSize: 11, fontWeight: "800" },
  muted: { color: COLORS.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  error: { color: "#A63A32", backgroundColor: "#FBEAE7", borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19, marginBottom: 8 },
  retryButton: { minHeight: 46, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 11, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 12 },
  retryButtonText: { color: COLORS.navy, fontSize: 13, fontWeight: "800" },
  emptyState: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, padding: 18 },
  emptyTitle: { color: COLORS.text, fontSize: 17, fontWeight: "800", marginBottom: 6 },
});
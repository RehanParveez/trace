import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../api/client";
import { listProjects } from "../../../api/projects";
import type { Project, ProjectStatus } from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

const PAGE_SIZE = 3;

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

export default function ChangeOrdersProjectPickerScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canRead, setCanRead] = useState<boolean | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      setPageNumber(1);

      try {
        const user = await restoreSession();

        if (!user) {
          router.replace("/");
          return;
        }

        const hasReadPermission = user.role.permissions.some(
          (permission) => permission.key === "change_order:read",
        );

        if (!active) return;
        setCanRead(hasReadPermission);

        if (!hasReadPermission) {
          setProjects([]);
          return;
        }

        const rows = await listProjects();
        if (active) setProjects(rows);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : t("changeOrders.loadFailure"),
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

  function openProject(projectId: string) {
    router.push({
      pathname: "/projects/[projectId]/change-orders",
      params: { projectId },
    });
  }

  function projectStatusLabel(status: ProjectStatus): string {
    return t(`changeOrders.projectStatus.${status.toLowerCase()}`, {
      defaultValue: status.replaceAll("_", " "),
    });
  }

  const totalPages = Math.ceil(projects.length / PAGE_SIZE);
  const startIndex = (pageNumber - 1) * PAGE_SIZE;
  const visibleProjects = projects.slice(startIndex, startIndex + PAGE_SIZE);
  const visiblePages = Array.from(
    { length: totalPages },
    (_, index) => index + 1,
  ).filter((page) => Math.abs(page - pageNumber) <= 2);

  return (
    <ScrollView
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
    >
      <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
        <Text style={styles.brand}>Trace</Text>
        <LanguageSwitcher />
      </View>

      <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
        {t("changeOrders.eyebrow")}
      </Text>
      <Text style={[styles.title, isUrdu && styles.rtlText]}>
        {t("changeOrders.pageTitle")}
      </Text>
      <Text style={[styles.subtitle, isUrdu && styles.rtlText]}>
        {t("changeOrders.subtitle")}
      </Text>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("changeOrders.loadingProjects")}
          </Text>
        </View>
      ) : error ? (
        <View style={styles.messageCard}>
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {error}
          </Text>
          <Pressable
            style={styles.button}
            accessibilityRole="button"
            accessibilityLabel={t("changeOrders.tryAgain")}
            onPress={() => setAttempt((value) => value + 1)}
          >
            <Text style={styles.buttonText}>
              {t("changeOrders.tryAgain")}
            </Text>
          </Pressable>
        </View>
      ) : canRead === false ? (
        <View style={styles.messageCard}>
          <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
            {t("changeOrders.accessUnavailable")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("changeOrders.accessDenied")}
          </Text>
        </View>
      ) : projects.length === 0 ? (
        <View style={styles.messageCard}>
          <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
            {t("changeOrders.noProjectsTitle")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("changeOrders.noProjectsHelp")}
          </Text>
        </View>
      ) : (
        <>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("changeOrders.selectProject")}
          </Text>

          {visibleProjects.map((project) => (
            <Pressable
              key={project.id}
              style={styles.card}
              accessibilityRole="button"
              accessibilityLabel={t(
                "changeOrders.openProjectAccessibility",
                { name: project.name },
              )}
              onPress={() => openProject(project.id)}
            >
              <View style={[styles.row, isUrdu && styles.rtlRow]}>
                <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                  {project.name}
                </Text>
                <Text style={styles.arrow}>{isUrdu ? "‹" : "›"}</Text>
              </View>

              {project.code ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {t("changeOrders.code", { code: project.code })}
                </Text>
              ) : null}

              {project.location ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {project.location}
                </Text>
              ) : null}

              <Text style={[styles.status, isUrdu && styles.rtlText]}>
                {projectStatusLabel(project.status)}
              </Text>
            </Pressable>
          ))}

          {totalPages > 1 ? (
            <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
              <Pressable
                style={[
                  styles.pageNavButton,
                  pageNumber === 1 && styles.disabled,
                ]}
                disabled={pageNumber === 1}
                onPress={() =>
                  setPageNumber((current) => Math.max(1, current - 1))
                }
                accessibilityRole="button"
              >
                <Text style={styles.pageNavText}>
                  {t("changeOrders.previousPage")}
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
                    disabled={page === pageNumber}
                    onPress={() => setPageNumber(page)}
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
                  pageNumber === totalPages && styles.disabled,
                ]}
                disabled={pageNumber === totalPages}
                onPress={() =>
                  setPageNumber((current) =>
                    Math.min(totalPages, current + 1),
                  )
                }
                accessibilityRole="button"
              >
                <Text style={styles.pageNavText}>
                  {t("changeOrders.nextPage")}
                </Text>
              </Pressable>
            </View>
          ) : null}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 20 },
  brand: { color: C.navy, fontSize: 16, fontWeight: "800" },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 28, fontWeight: "800", marginTop: 5, letterSpacing: -0.4 },
  subtitle: { color: C.secondary, fontSize: 14, lineHeight: 21, marginTop: 6, marginBottom: 20 },
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: "800", marginBottom: 8 },
  card: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, padding: 16, marginTop: 10 },
  messageCard: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, padding: 18, marginTop: 12 },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  cardTitle: { color: C.text, fontSize: 17, fontWeight: "800", flexShrink: 1 },
  arrow: { color: C.muted, fontSize: 26 },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  status: { color: C.navy, backgroundColor: C.surfaceMuted, alignSelf: "flex-start", overflow: "hidden", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 6, fontSize: 11, fontWeight: "800", marginTop: 12 },
  center: { alignItems: "center", padding: 28, gap: 12 },
  error: { color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19 },
  button: { backgroundColor: C.navy, borderRadius: 11, paddingHorizontal: 14, paddingVertical: 13, alignItems: "center", marginTop: 16 },
  buttonText: { color: C.surface, fontSize: 13, fontWeight: "800" },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 16, padding: 10, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13 },
  pageNavButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: C.surfaceMuted },
  pageNavText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pageNumbers: { flexDirection: "row", alignItems: "center", gap: 5 },
  pageNumber: { minWidth: 36, height: 36, alignItems: "center", justifyContent: "center", borderRadius: 9, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  pageNumberSelected: { backgroundColor: C.navy, borderColor: C.navy },
  pageNumberText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  pageNumberTextSelected: { color: C.surface },
  disabled: { opacity: 0.45 },
});
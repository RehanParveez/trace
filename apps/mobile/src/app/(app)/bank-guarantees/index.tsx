import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../api/client";
import { listProjects } from "../../../api/projects";
import type { Project } from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

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

export default function BankGuaranteesProjectPickerScreen() {
  const { t, i18n } = useTranslation();

  const isUrdu = i18n.resolvedLanguage === "ur";

  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canRead, setCanRead] = useState<boolean | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      setCanRead(null);

      try {
        const user = await restoreSession();

        if (!user) {
          router.replace("/");
          return;
        }

        const hasReadPermission = user.role.permissions.some(
          (permission) => permission.key === "bank_guarantee:read",
        );

        if (!active) return;

        setCanRead(hasReadPermission);

        if (!hasReadPermission) {
          setProjects([]);
          return;
        }

        const projectRows = await listProjects();

        if (!active) return;

        setProjects(projectRows);
      } catch (err) {
        if (!active) return;

        setError(
          err instanceof Error
            ? err.message
            : t("bankGuarantees.loadProjectsFailure"),
        );
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

  function openProject(projectId: string) {
    router.push({
      pathname: "/projects/[projectId]/bank-guarantees",
      params: { projectId },
    });
  }

  function formatStatus(status: string) {
    return status.replace(/_/g, " ");
  }

  return (
    <ScrollView
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
    >
      <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
        <View style={styles.brandContainer}>
          <Text style={styles.brand}>
            {t("bankGuarantees.brand")}
          </Text>
        </View>

        <LanguageSwitcher />
      </View>

      <View style={styles.header}>
        <Text style={[styles.title, isUrdu && styles.rtlText]}>
          {t("bankGuarantees.pickerTitle")}
        </Text>

        <Text style={[styles.subtitle, isUrdu && styles.rtlText]}>
          {t("bankGuarantees.pickerSubtitle")}
        </Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />

          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("bankGuarantees.loadingProjects")}
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
            accessibilityLabel={t("bankGuarantees.tryAgain")}
            onPress={() => setAttempt((value) => value + 1)}
          >
            <Text style={styles.buttonText}>
              {t("bankGuarantees.tryAgain")}
            </Text>
          </Pressable>
        </View>
      ) : canRead === false ? (
        <View style={styles.messageCard}>
          <Text style={[styles.emptyTitle, isUrdu && styles.rtlText]}>
            {t("bankGuarantees.accessUnavailable")}
          </Text>

          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("bankGuarantees.accessDenied")}
          </Text>
        </View>
      ) : projects.length === 0 ? (
        <View style={styles.messageCard}>
          <Text style={[styles.emptyTitle, isUrdu && styles.rtlText]}>
            {t("bankGuarantees.noProjectsTitle")}
          </Text>

          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("bankGuarantees.noProjectsHelp")}
          </Text>
        </View>
      ) : (
        <View>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("bankGuarantees.selectProject")}
          </Text>

          {projects.map((project) => (
            <Pressable
              key={project.id}
              style={styles.card}
              accessibilityRole="button"
              accessibilityLabel={t(
                "bankGuarantees.accessibilityOpen",
                {
                  name: project.name,
                },
              )}
              onPress={() => openProject(project.id)}
            >
              <View
                style={[
                  styles.cardHeading,
                  isUrdu && styles.rtlRow,
                ]}
              >
                <Text
                  style={[
                    styles.projectName,
                    isUrdu && styles.rtlText,
                  ]}
                >
                  {project.name}
                </Text>

                <Text style={styles.cardArrow}>
                  {isUrdu ? "‹" : "›"}
                </Text>
              </View>

              {project.code ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {t("bankGuarantees.code", {
                    code: project.code,
                  })}
                </Text>
              ) : null}

              {project.location ? (
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {project.location}
                </Text>
              ) : null}

              <View
                style={[
                  styles.cardFooter,
                  isUrdu && styles.rtlRow,
                ]}
              >
                <Text style={styles.status}>
                  {formatStatus(project.status)}
                </Text>

                <Text style={styles.openLabel}>
                  {t("bankGuarantees.openLabel")}
                </Text>
              </View>
            </Pressable>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 22 },
  brandContainer: { flex: 1 },
  brand: { color: C.navy, fontSize: 16, fontWeight: "800", letterSpacing: 0.2 },
  header: { marginBottom: 22 },
  title: { color: C.text, fontSize: 27, fontWeight: "800", marginTop: 5, letterSpacing: -0.4 },
  subtitle: { color: C.secondary, fontSize: 14, lineHeight: 21, marginTop: 7 },
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: "800", marginBottom: 10 },
  card: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, padding: 16, marginBottom: 12 },
  cardHeading: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10 },
  projectName: { color: C.text, fontSize: 17, fontWeight: "800", flexShrink: 1 },
  cardArrow: { color: C.muted, fontSize: 26, lineHeight: 30 },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  cardFooter: { borderTopWidth: 1, borderTopColor: C.border, marginTop: 14, paddingTop: 12, flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10 },
  status: { color: C.navy, backgroundColor: C.surfaceMuted, overflow: "hidden", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 6, fontSize: 11, fontWeight: "800", textTransform: "capitalize" },
  openLabel: { color: C.navy, fontSize: 13, fontWeight: "800" },
  center: { alignItems: "center", padding: 28, gap: 12, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 15 },
  messageCard: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, padding: 18 },
  emptyTitle: { color: C.text, fontSize: 17, fontWeight: "800" },
  error: { color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19 },
  button: { minHeight: 46, backgroundColor: C.navy, borderRadius: 11, paddingHorizontal: 16, paddingVertical: 13, alignItems: "center", justifyContent: "center", marginTop: 15 },
  buttonText: { color: C.surface, fontSize: 13, fontWeight: "800" },
});
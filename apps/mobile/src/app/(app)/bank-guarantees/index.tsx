import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../api/client";
import { listProjects } from "../../../api/projects";
import type { Project } from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

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
      <View style={styles.topBar}>
        <View style={styles.brandContainer}>
          <Text style={styles.brand}>
            {t("bankGuarantees.brand")}
          </Text>
        </View>

        <LanguageSwitcher />
      </View>

      <View style={styles.header}>
        <Text style={styles.title}>
          {t("bankGuarantees.pickerTitle")}
        </Text>

        <Text style={styles.subtitle}>
          {t("bankGuarantees.pickerSubtitle")}
        </Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#183153" />

          <Text style={styles.muted}>
            {t("bankGuarantees.loadingProjects")}
          </Text>
        </View>
      ) : error ? (
        <View style={styles.messageCard}>
          <Text style={styles.error}>{error}</Text>

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
          <Text style={styles.emptyTitle}>
            {t("bankGuarantees.accessUnavailable")}
          </Text>

          <Text style={styles.muted}>
            {t("bankGuarantees.accessDenied")}
          </Text>
        </View>
      ) : projects.length === 0 ? (
        <View style={styles.messageCard}>
          <Text style={styles.emptyTitle}>
            {t("bankGuarantees.noProjectsTitle")}
          </Text>

          <Text style={styles.muted}>
            {t("bankGuarantees.noProjectsHelp")}
          </Text>
        </View>
      ) : (
        <View>
          <Text style={styles.sectionTitle}>
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
                <Text style={styles.projectName}>
                  {project.name}
                </Text>

                <Text style={styles.cardArrow}>
                  {isUrdu ? "‹" : "›"}
                </Text>
              </View>

              {project.code ? (
                <Text style={styles.muted}>
                  {t("bankGuarantees.code", {
                    code: project.code,
                  })}
                </Text>
              ) : null}

              {project.location ? (
                <Text style={styles.muted}>
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
  page: {flexGrow: 1, padding: 24, paddingTop: 30, paddingBottom: 40, backgroundColor: "#F4F6F8",},
  rtlPage: {direction: "rtl",},
  topBar: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 24,},
  brandContainer: {flex: 1,},
  brand: {color: "#183153", fontSize: 16, fontWeight: "700",},
  header: {marginBottom: 24,},
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginTop: 6,},
  subtitle: {color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 6,},
  sectionTitle: {color: "#17212F", fontSize: 17, fontWeight: "700", marginBottom: 12,},
  card: {backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#E4E7EC", padding: 18, marginBottom: 12,},
  cardHeading: {flexDirection: "row", justifyContent: "space-between", alignItems: "center",},
  rtlRow: {flexDirection: "row-reverse",},
  projectName: {color: "#17212F", fontSize: 18, fontWeight: "700", flexShrink: 1, marginRight: 12,},
  cardArrow: {color: "#667085", fontSize: 26,},
  muted: {color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 6,},
  cardFooter: {borderTopWidth: 1, borderTopColor: "#EAECF0", marginTop: 14, paddingTop: 12, flexDirection: "row", justifyContent: "space-between", alignItems: "center",},
  status: {color: "#183153", fontSize: 12, fontWeight: "700", textTransform: "capitalize",},
  openLabel: {color: "#183153", fontSize: 13, fontWeight: "700",},
  center: {alignItems: "center", padding: 28, gap: 12,},
  messageCard: {backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#E4E7EC", padding: 20,},
  emptyTitle: {color: "#17212F", fontSize: 18, fontWeight: "700",},
  error: {color: "#B42318", fontSize: 14, lineHeight: 20,},
  button: {backgroundColor: "#183153", borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16,},
  buttonText: {color: "#FFFFFF", fontWeight: "700",},
});
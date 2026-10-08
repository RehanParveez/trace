import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router, useLocalSearchParams, Link } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../api/client";
import { getProject, listClients } from "../../../api/projects";
import type { Client, Project } from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

function formatDate(
  value: string | null,
  locale: string,
  notSet: string,
): string {
  if (!value) return notSet;

  const date = new Date(`${value.slice(0, 10)}T00:00:00`);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(locale);
}

function ProjectLink(props: {
  projectId: string;
  pathname: string;
  label: string;
  isUrdu: boolean;
}) {
  return (
    <Link
      href={{
        pathname: props.pathname as never,
        params: { projectId: props.projectId },
      }}
      asChild
    >
      <Pressable style={styles.navButton} accessibilityRole="button">
        <Text
          style={[
            styles.navButtonText,
            props.isUrdu && styles.rtlText,
          ]}
        >
          {props.label}
        </Text>
        <Text style={styles.navArrow}>›</Text>
      </Pressable>
    </Link>
  );
}

export default function ProjectDetailScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";

  const params = useLocalSearchParams<{
    projectId?: string | string[];
  }>();

  const routeProjectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const projectId = routeProjectId?.trim() || undefined;

  const [project, setProject] = useState<Project | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    async function load() {
      if (!projectId) {
        setError(t("projectDetail.missingProjectId"));
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const user = await restoreSession();

        if (!user) {
          router.replace("/");
          return;
        }

        const projectResult = await getProject(projectId);

        if (!active) return;

        setProject(projectResult);

        try {
          const clientResult = await listClients();

          if (active) {
            setClients(clientResult);
          }
        } catch {
        }
      } catch (err) {
        if (active) {
          const message =
            err instanceof Error ? err.message : "";

          setError(
            message.toLowerCase().includes("project not found")
              ? t("projectDetail.projectNotFound")
              : message || t("projectDetail.loadFailure"),
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
  }, [projectId, attempt, t]);

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>

        <ActivityIndicator size="large" color={COLORS.navy} />

        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("projectDetail.loading")}
        </Text>
      </View>
    );
  }

  if (error || !project) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Pressable
            onPress={() => router.replace("/projects")}
            accessibilityRole="button"
          >
            <Text style={[styles.link, isUrdu && styles.rtlText]}>
              {t("projectDetail.projects")}
            </Text>
          </Pressable>

          <LanguageSwitcher />
        </View>

        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error || t("projectDetail.projectNotFound")}
        </Text>

        <Pressable
          style={styles.navButton}
          onPress={() => setAttempt((current) => current + 1)}
          accessibilityRole="button"
        >
          <Text style={[styles.navButtonText, isUrdu && styles.rtlText]}>
            {t("projectDetail.tryAgain")}
          </Text>
        </Pressable>
      </View>
    );
  }

  const client = clients.find((item) => item.id === project.client_id);
  const projectStatusKey =
    `projectDetail.status.${project.status.toLowerCase()}`;

  return (
    <ScrollView
      contentContainerStyle={styles.page}
      keyboardShouldPersistTaps="handled"
    >
      <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
        <Pressable
          onPress={() => router.replace("/projects")}
          accessibilityRole="button"
        >
          <Text style={[styles.link, isUrdu && styles.rtlText]}>
            {t("projectDetail.projects")}
          </Text>
        </Pressable>

        <LanguageSwitcher />
      </View>

      <View style={styles.hero}>
        <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
          {t("projectDetail.project")}
        </Text>

        <Text style={[styles.heroTitle, isUrdu && styles.rtlText]}>
          {project.name}
        </Text>

        {project.code ? (
          <Text style={[styles.heroSubtitle, isUrdu && styles.rtlText]}>
            {project.code}
          </Text>
        ) : null}

        <Text style={[styles.status, isUrdu && styles.rtlText]}>
          {t(projectStatusKey, {
            defaultValue: project.status.replaceAll("_", " "),
          })}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
          {t("projectDetail.overview")}
        </Text>

        {project.description ? (
          <Text style={[styles.description, isUrdu && styles.rtlText]}>
            {project.description}
          </Text>
        ) : null}

        <InfoRow
          label={t("projectDetail.client")}
          value={client?.name || t("projectDetail.notAssigned")}
          isUrdu={isUrdu}
        />

        <InfoRow
          label={t("projectDetail.location")}
          value={project.location || t("projectDetail.notSet")}
          isUrdu={isUrdu}
        />

        <InfoRow
          label={t("projectDetail.startDate")}
          value={formatDate(
            project.start_date,
            locale,
            t("projectDetail.notSet"),
          )}
          isUrdu={isUrdu}
        />

        <InfoRow
          label={t("projectDetail.expectedCompletion")}
          value={formatDate(
            project.expected_end_date,
            locale,
            t("projectDetail.notSet"),
          )}
          isUrdu={isUrdu}
        />

        <InfoRow
          label={t("projectDetail.actualCompletion")}
          value={formatDate(
            project.actual_end_date,
            locale,
            t("projectDetail.notSet"),
          )}
          isUrdu={isUrdu}
        />
      </View>

      <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
        {t("projectDetail.projectWorkspace")}
      </Text>

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/manage"
        label={t("projectDetail.manageProject")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/team"
        label={t("projectDetail.projectTeam")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/milestones"
        label={t("projectDetail.milestones")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/drawings-boq"
        label={t("projectDetail.drawingsBOQ")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/progress-verification"
        label={t("projectDetail.progressVerification")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/site-photos"
        label={t("projectDetail.sitePhotos")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/site-progress"
        label={t("projectDetail.siteProgress")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/subcontractors"
        label={t("projectDetail.subcontractors")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/labour"
        label={t("projectDetail.labour")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/bank-guarantees"
        label={t("projectDetail.bankGuarantees")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/change-orders"
        label={t("projectDetail.changeOrders")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/budgets"
        label={t("projectDetail.budget")}
        isUrdu={isUrdu}
      />

      <ProjectLink
        projectId={project.id}
        pathname="/projects/[projectId]/expenses"
        label={t("projectDetail.expenses")}
        isUrdu={isUrdu}
      />

      <Pressable
        style={styles.refreshButton}
        onPress={() => setAttempt((current) => current + 1)}
        accessibilityRole="button"
      >
        <Text style={[styles.refreshButtonText, isUrdu && styles.rtlText]}>
          {t("projectDetail.refresh")}
        </Text>
      </Pressable>
    </ScrollView>
  );
}

function InfoRow(props: {
  label: string;
  value: string;
  isUrdu: boolean;
}) {
  return (
    <View style={[styles.infoRow, props.isUrdu && styles.rtlRow]}>
      <Text style={[styles.infoLabel, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>

      <Text style={[styles.infoValue, props.isUrdu && styles.rtlText]}>
        {props.value}
      </Text>
    </View>
  );
}

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

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 22, paddingBottom: 38, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 8 },
  rtlRow: { flexDirection: "row-reverse" },
  hero: { backgroundColor: COLORS.navy, borderRadius: 17, borderWidth: 1, borderColor: "#242B38", padding: 20, marginTop: 12, marginBottom: 16 },
  eyebrow: { color: "#D9B76B", fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
  heroTitle: { color: COLORS.surface, fontSize: 25, fontWeight: "800", marginTop: 8 },
  heroSubtitle: { color: "#D6D0C5", fontSize: 14, marginTop: 5 },
  status: { color: COLORS.navy, backgroundColor: "#E4C06E", borderRadius: 99, overflow: "hidden", alignSelf: "flex-start", paddingHorizontal: 11, paddingVertical: 6, marginTop: 14, fontSize: 11, fontWeight: "800" },
  card: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 16, marginBottom: 14 },
  sectionTitle: { color: COLORS.text, fontSize: 17, fontWeight: "800", marginBottom: 8, marginTop: 10 },
  description: { color: COLORS.secondary, fontSize: 13, lineHeight: 20, marginBottom: 12 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 10, borderTopWidth: 1, borderTopColor: "#F0EADF" },
  infoLabel: { color: COLORS.muted, fontSize: 12, flex: 1 },
  infoValue: { color: COLORS.text, fontSize: 13, fontWeight: "700", flex: 1, textAlign: "right" },
  muted: { color: COLORS.muted, fontSize: 13, lineHeight: 20 },
  error: { color: "#A63A32", backgroundColor: "#FBEAE7", borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginTop: 12, marginBottom: 8, fontSize: 13, lineHeight: 19 },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  navButton: { minHeight: 48, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, backgroundColor: COLORS.surface, borderRadius: 12, borderWidth: 1, borderColor: COLORS.border, paddingHorizontal: 15, paddingVertical: 12, marginTop: 8 },
  navButtonText: { flex: 1, color: COLORS.navy, fontSize: 13, fontWeight: "800" },
  navArrow: { color: COLORS.gold, fontSize: 22, fontWeight: "700" },
  refreshButton: { minHeight: 46, alignItems: "center", justifyContent: "center", backgroundColor: COLORS.navy, borderRadius: 11, paddingHorizontal: 14, paddingVertical: 11, marginTop: 16 },
  refreshButtonText: { color: COLORS.surface, fontSize: 13, fontWeight: "800" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});
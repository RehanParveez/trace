import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {createMilestone, deleteMilestone, getProject, listMilestones, updateMilestone,
} from "../../../../api/projects";
import type { Milestone, Project } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";

const PAGE_SIZE = 3;

function clean(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function validDate(value: string): boolean {
  if (!value) return true;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return (
    !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
  );
}

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

export default function ProjectMilestonesScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  const [milestoneName, setMilestoneName] = useState("");
  const [milestoneDescription, setMilestoneDescription] = useState("");
  const [milestoneDueDate, setMilestoneDueDate] = useState("");
  const [editingMilestoneId, setEditingMilestoneId] = useState("");

  const canUpdate = permissions.includes("project.update");
  const pages = pageCount(milestones.length);
  const visibleMilestones = paginate(milestones, page);

  const load = useCallback(async () => {
    if (!projectId) {
      setError(t("projectMilestones.projectNotFound"));
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

      setPermissions(user.role.permissions.map((permission) => permission.key));
      setProject(await getProject(projectId));

      try {
        setMilestones(await listMilestones(projectId));
        setPage(1);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("projectMilestones.loadMilestonesFailure"),
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("projectMilestones.loadProjectFailure"),
      );
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");

    try {
      await action();
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("projectMilestones.actionFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  function clearForm() {
    setEditingMilestoneId("");
    setMilestoneName("");
    setMilestoneDescription("");
    setMilestoneDueDate("");
  }

  async function saveMilestone() {
    if (!projectId || !milestoneName.trim()) {
      setError(t("projectMilestones.validation.name"));
      return;
    }

    if (!validDate(milestoneDueDate)) {
      setError(t("projectMilestones.validation.dueDate"));
      return;
    }

    await run(async () => {
      const payload = {
        name: milestoneName.trim(),
        description: clean(milestoneDescription),
        due_date: milestoneDueDate || null,
      };

      if (editingMilestoneId) {
        await updateMilestone(projectId, editingMilestoneId, payload);
      } else {
        await createMilestone(projectId, payload);
      }

      clearForm();
    });
  }

  function confirmDeleteMilestone(milestone: Milestone) {
    if (!projectId) return;

    Alert.alert(
      t("projectMilestones.deleteConfirmTitle"),
      t("projectMilestones.deleteConfirmMessage", { name: milestone.name }),
      [
        {
          text: t("projectMilestones.cancel"),
          style: "cancel",
        },
        {
          text: t("projectMilestones.delete"),
          style: "destructive",
          onPress: () =>
            void run(() => deleteMilestone(projectId, milestone.id)),
        },
      ],
    );
  }

  async function toggleMilestone(milestone: Milestone) {
    if (!projectId) return;

    await run(() =>
      updateMilestone(projectId, milestone.id, {
        completed_at: milestone.completed_at
          ? null
          : new Date().toISOString().slice(0, 10),
      }),
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("projectMilestones.loading")}
        </Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, styles.headerCopy, isUrdu && styles.rtlText]}>
            {t("projectMilestones.title")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error || t("projectMilestones.projectNotFound")}
        </Text>
        <Pressable onPress={() => router.back()}>
          <Text style={[styles.link, isUrdu && styles.rtlText]}>
            {t("projectMilestones.backToProject")}
          </Text>
        </Pressable>
      </View>
    );
  }

  if (!canUpdate) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("projectMilestones.backToProjectName", {
                  name: project.name,
                })}
              </Text>
            </Pressable>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("projectMilestones.title")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {t("projectMilestones.accessDenied")}
        </Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("projectMilestones.backToProjectName", {
                  name: project.name,
                })}
              </Text>
            </Pressable>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("projectMilestones.title")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
        ) : null}

        <View style={styles.formCard}>
          <Text style={[styles.section, isUrdu && styles.rtlText]}>
            {editingMilestoneId
              ? t("projectMilestones.editMilestone")
              : t("projectMilestones.addMilestone")}
          </Text>

          <Field
            label={t("projectMilestones.milestoneName")}
            value={milestoneName}
            onChangeText={setMilestoneName}
            isUrdu={isUrdu}
          />
          <Field
            label={t("projectMilestones.description")}
            value={milestoneDescription}
            onChangeText={setMilestoneDescription}
            multiline
            isUrdu={isUrdu}
          />
          <Field
            label={t("projectMilestones.dueDate")}
            value={milestoneDueDate}
            onChangeText={setMilestoneDueDate}
            isUrdu={isUrdu}
          />

          <Action
            title={
              editingMilestoneId
                ? t("projectMilestones.saveChanges")
                : t("projectMilestones.addMilestone")
            }
            onPress={() => void saveMilestone()}
            isUrdu={isUrdu}
          />

          {editingMilestoneId ? (
            <Action
              title={t("projectMilestones.cancelEdit")}
              secondary
              onPress={clearForm}
              isUrdu={isUrdu}
            />
          ) : null}
        </View>

        <Text style={[styles.section, isUrdu && styles.rtlText]}>
          {t("projectMilestones.allMilestones")}
        </Text>

        {milestones.length === 0 ? (
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectMilestones.empty")}
          </Text>
        ) : (
          <>
            {visibleMilestones.map((milestone) => (
              <View key={milestone.id} style={styles.card}>
                <Text style={[styles.itemTitle, isUrdu && styles.rtlText]}>
                  {milestone.name}
                </Text>
                <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                  {milestone.completed_at
                    ? t("projectMilestones.completedOn", {
                        date: milestone.completed_at,
                      })
                    : milestone.due_date
                      ? t("projectMilestones.dueOn", {
                          date: milestone.due_date,
                        })
                      : t("projectMilestones.dateNotSet")}
                </Text>

                {milestone.description ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {milestone.description}
                  </Text>
                ) : null}

                <View style={[styles.row, isUrdu && styles.rtlRow]}>
                  <Action
                    title={t("projectMilestones.edit")}
                    secondary
                    onPress={() => {
                      setEditingMilestoneId(milestone.id);
                      setMilestoneName(milestone.name);
                      setMilestoneDescription(milestone.description ?? "");
                      setMilestoneDueDate(milestone.due_date ?? "");
                    }}
                    isUrdu={isUrdu}
                  />
                  <Action
                    title={
                      milestone.completed_at
                        ? t("projectMilestones.reopen")
                        : t("projectMilestones.complete")
                    }
                    secondary
                    onPress={() => void toggleMilestone(milestone)}
                    isUrdu={isUrdu}
                  />
                  <Action
                    title={t("projectMilestones.delete")}
                    danger
                    onPress={() => confirmDeleteMilestone(milestone)}
                    isUrdu={isUrdu}
                  />
                </View>
              </View>
            ))}

            <Pagination
              page={page}
              pages={pages}
              isUrdu={isUrdu}
              onPrevious={() => setPage((current) => Math.max(1, current - 1))}
              onNext={() =>
                setPage((current) => Math.min(pages, current + 1))
              }
            />
          </>
        )}

        {busy ? (
          <View style={styles.busy}>
            <ActivityIndicator color={COLORS.navy} />
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("projectMilestones.saving")}
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Pagination(props: {
  page: number;
  pages: number;
  isUrdu: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const { t } = useTranslation();

  return (
    <View style={[styles.pagination, props.isUrdu && styles.rtlRow]}>
      <Action
        title={t("projectMilestones.previous")}
        secondary
        disabled={props.page <= 1}
        onPress={props.onPrevious}
        isUrdu={props.isUrdu}
      />
      <Text style={[styles.pageText, props.isUrdu && styles.rtlText]}>
        {t("projectMilestones.pageOf", {
          page: props.page,
          pages: props.pages,
        })}
      </Text>
      <Action
        title={t("projectMilestones.next")}
        secondary
        disabled={props.page >= props.pages}
        onPress={props.onNext}
        isUrdu={props.isUrdu}
      />
    </View>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  multiline?: boolean;
  isUrdu: boolean;
}) {
  return (
    <>
      <Text style={[styles.label, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <TextInput
        style={[
          styles.input,
          props.multiline && styles.multiline,
          props.isUrdu && styles.rtlText,
        ]}
        value={props.value}
        onChangeText={props.onChangeText}
        multiline={props.multiline}
        textAlignVertical={props.multiline ? "top" : "center"}
        textAlign={props.isUrdu ? "right" : "left"}
      />
    </>
  );
}

function Action(props: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  danger?: boolean;
  disabled?: boolean;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.action,
        props.secondary && styles.actionSecondary,
        props.danger && styles.actionDanger,
        props.disabled && styles.disabled,
      ]}
      onPress={props.onPress}
      disabled={props.disabled}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          props.secondary && styles.actionSecondaryText,
          props.danger && styles.actionDangerText,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.title}
      </Text>
    </Pressable>
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
  flex: { flex: 1, backgroundColor: COLORS.background },
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 38, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 8 },
  headerCopy: { flex: 1 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 26, fontWeight: "800", marginTop: 10, marginBottom: 4 },
  section: { color: COLORS.text, fontSize: 18, fontWeight: "800", marginTop: 8, marginBottom: 5 },
  formCard: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 10 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 12, marginBottom: 6 },
  input: { minHeight: 46, backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: COLORS.text },
  multiline: { minHeight: 82, textAlignVertical: "top" },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 10 },
  itemTitle: { color: COLORS.text, fontSize: 15, fontWeight: "800" },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 6, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginVertical: 10, lineHeight: 19, fontSize: 13 },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 },
  action: { minHeight: 42, flexGrow: 1, backgroundColor: COLORS.navy, borderWidth: 1, borderColor: COLORS.navy, borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 12, paddingVertical: 10, marginTop: 10 },
  actionSecondary: { backgroundColor: COLORS.surface, borderColor: COLORS.border },
  actionDanger: { backgroundColor: COLORS.red, borderColor: COLORS.red },
  actionText: { color: COLORS.surface, fontSize: 12, fontWeight: "800", textAlign: "center" },
  actionSecondaryText: { color: COLORS.navy },
  actionDangerText: { color: COLORS.surface },
  disabled: { opacity: 0.5 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 10 },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", textAlign: "center" },
  busy: { alignItems: "center", padding: 18, gap: 8 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});
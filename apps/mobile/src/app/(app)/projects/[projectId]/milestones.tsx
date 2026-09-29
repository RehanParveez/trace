import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { restoreSession } from "../../../../api/client";
import {
  createMilestone,
  deleteMilestone,
  getProject,
  listMilestones,
  updateMilestone,
} from "../../../../api/projects";
import type { Milestone, Project } from "../../../../api/types";

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

export default function ProjectMilestonesScreen() {
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

  const [milestoneName, setMilestoneName] = useState("");
  const [milestoneDescription, setMilestoneDescription] = useState("");
  const [milestoneDueDate, setMilestoneDueDate] = useState("");
  const [editingMilestoneId, setEditingMilestoneId] = useState("");

  const canUpdate = permissions.includes("project.update");

  const load = useCallback(async () => {
    if (!projectId) {
      setError("Project not found.");
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
      setPermissions(user.role.permissions.map((p) => p.key));
      setProject(await getProject(projectId));
      try {
        setMilestones(await listMilestones(projectId));
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not load milestones.",
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load project.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

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
      setError(err instanceof Error ? err.message : "The action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveMilestone() {
    if (!projectId || !milestoneName.trim()) {
      setError("Enter a milestone name.");
      return;
    }
    if (!validDate(milestoneDueDate)) {
      setError("Milestone date must be a valid YYYY-MM-DD date.");
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
      setMilestoneName("");
      setMilestoneDescription("");
      setMilestoneDueDate("");
      setEditingMilestoneId("");
    });
  }

  function confirmDeleteMilestone(milestone: Milestone) {
    if (!projectId) return;
    Alert.alert("Delete milestone?", `Delete “${milestone.name}”?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: () =>
          void run(() => deleteMilestone(projectId, milestone.id)),
      },
    ]);
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
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading milestones…</Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <Text style={styles.error}>{error || "Project not found."}</Text>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  Back to project</Text>
        </Pressable>
      </View>
    );
  }

  if (!canUpdate) {
    return (
      <View style={styles.page}>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  {project.name}</Text>
        </Pressable>
        <Text style={styles.title}>Milestones</Text>
        <Text style={styles.error}>
          Your organization role does not allow project updates.
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
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  {project.name}</Text>
        </Pressable>

        <Text style={styles.title}>Milestones</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Text style={styles.section}>
          {editingMilestoneId ? "Edit milestone" : "Add milestone"}
        </Text>
        <Field
          label="Milestone name"
          value={milestoneName}
          onChangeText={setMilestoneName}
        />
        <Field
          label="Description"
          value={milestoneDescription}
          onChangeText={setMilestoneDescription}
          multiline
        />
        <Field
          label="Due date (YYYY-MM-DD)"
          value={milestoneDueDate}
          onChangeText={setMilestoneDueDate}
        />
        <Action
          title={editingMilestoneId ? "Save milestone changes" : "Add milestone"}
          onPress={() => void saveMilestone()}
        />
        {editingMilestoneId ? (
          <Action
            title="Cancel milestone edit"
            secondary
            onPress={() => {
              setEditingMilestoneId("");
              setMilestoneName("");
              setMilestoneDescription("");
              setMilestoneDueDate("");
            }}
          />
        ) : null}

        <Text style={styles.section}>All milestones</Text>
        {milestones.length === 0 ? (
          <Text style={styles.muted}>No milestones for this project yet.</Text>
        ) : null}

        {milestones.map((milestone) => (
          <View key={milestone.id} style={styles.card}>
            <Text style={styles.itemTitle}>{milestone.name}</Text>
            <Text style={styles.muted}>
              {milestone.completed_at
                ? `Completed ${milestone.completed_at}`
                : `Due ${milestone.due_date || "date not set"}`}
            </Text>
            {milestone.description ? (
              <Text style={styles.muted}>{milestone.description}</Text>
            ) : null}
            <View style={styles.row}>
              <Action
                title="Edit"
                secondary
                onPress={() => {
                  setEditingMilestoneId(milestone.id);
                  setMilestoneName(milestone.name);
                  setMilestoneDescription(milestone.description ?? "");
                  setMilestoneDueDate(milestone.due_date ?? "");
                }}
              />
              <Action
                title={milestone.completed_at ? "Reopen" : "Complete"}
                secondary
                onPress={() => void toggleMilestone(milestone)}
              />
              <Action
                title="Delete"
                danger
                onPress={() => confirmDeleteMilestone(milestone)}
              />
            </View>
          </View>
        ))}

        {busy ? (
          <View style={styles.busy}>
            <ActivityIndicator color="#183153" />
            <Text style={styles.muted}>Saving changes…</Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field({
  label,
  value,
  onChangeText,
  multiline = false,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  multiline?: boolean;
}) {
  return (
    <>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline]}
        value={value}
        onChangeText={onChangeText}
        multiline={multiline}
        textAlignVertical={multiline ? "top" : "center"}
      />
    </>
  );
}

function Action({
  title,
  onPress,
  secondary = false,
  danger = false,
}: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  danger?: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.action,
        secondary && styles.actionSecondary,
        danger && styles.actionDanger,
      ]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          secondary && styles.actionSecondaryText,
          danger && styles.actionDangerText,
        ]}
      >
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#F4F6F8" },
  page: {flexGrow: 1, padding: 22, paddingTop: 52, paddingBottom: 48, backgroundColor: "#F4F6F8",},
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8",},
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginVertical: 18,},
  section: {color: "#17212F", fontSize: 20, fontWeight: "700", marginTop: 32, marginBottom: 8,},
  label: {color: "#344054", fontSize: 14, fontWeight: "600", marginTop: 14, marginBottom: 7,},
  input: {backgroundColor: "white", borderColor: "#D0D5DD", borderWidth: 1, borderRadius: 10, padding: 14, fontSize: 16, color: "#17212F",},
  multiline: { minHeight: 86 },
  card: {backgroundColor: "white", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 15, marginTop: 10,},
  itemTitle: { color: "#17212F", fontSize: 16, fontWeight: "700" },
  muted: { color: "#667085", marginTop: 6, lineHeight: 20 },
  error: { color: "#B42318", marginVertical: 12, lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700", fontSize: 15 },
  action: {backgroundColor: "#183153", borderRadius: 10, alignItems: "center", padding: 13, marginTop: 10,},
  actionSecondary: {backgroundColor: "white", borderWidth: 1, borderColor: "#D0D5DD",},
  actionDanger: { backgroundColor: "#B42318" },
  actionText: { color: "white", fontWeight: "700" },
  actionSecondaryText: { color: "#183153" },
  actionDangerText: { color: "white" },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  busy: { alignItems: "center", padding: 18, gap: 8 },
});
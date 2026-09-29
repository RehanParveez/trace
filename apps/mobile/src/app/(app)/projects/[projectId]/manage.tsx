import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text,
  TextInput, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { restoreSession } from "../../../../api/client";
import {addProjectMember, createClient, createMilestone, deleteClient, deleteMilestone, deleteProject, deleteProjectMember, getProject, listClients, listMilestones,
  listOrganizationMembers, listProjectMembers, updateClient, updateMilestone, updateProject, updateProjectMember,
} from "../../../../api/projects";
import type {Client, Milestone, OrganizationMember, Project, ProjectMember, ProjectMemberRole, ProjectStatus,
} from "../../../../api/types";

const roles: ProjectMemberRole[] = [
  "MANAGER",
  "ENGINEER",
  "SUPERVISOR",
  "SITE_MANAGER",
  "MEMBER",
];

const statuses: ProjectStatus[] = [
  "PLANNING",
  "ACTIVE",
  "ON_HOLD",
  "COMPLETED",
  "CANCELLED",
];

function clean(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function validDate(value: string): boolean {
  if (!value) return true;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value;
}

export default function ManageProjectScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [organizationMembers, setOrganizationMembers] = useState<
    OrganizationMember[]
  >([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [startDate, setStartDate] = useState("");
  const [expectedEndDate, setExpectedEndDate] = useState("");
  const [actualEndDate, setActualEndDate] = useState("");
  const [status, setStatus] = useState<ProjectStatus>("PLANNING");
  const [clientId, setClientId] = useState("");

  const [clientName, setClientName] = useState("");
  const [clientContact, setClientContact] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [editingClientId, setEditingClientId] = useState("");

  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState<ProjectMemberRole>("MEMBER");

  const [milestoneName, setMilestoneName] = useState("");
  const [milestoneDescription, setMilestoneDescription] = useState("");
  const [milestoneDueDate, setMilestoneDueDate] = useState("");
  const [editingMilestoneId, setEditingMilestoneId] = useState("");

  const canUpdate = permissions.includes("project.update");
  const canDelete = permissions.includes("project.delete");
  const canReadOrganization = permissions.includes("organization.read");

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

      const granted = user.role.permissions.map((permission) => permission.key);
      setPermissions(granted);

      const projectResult = await getProject(projectId);
      setProject(projectResult);
      setName(projectResult.name);
      setCode(projectResult.code ?? "");
      setDescription(projectResult.description ?? "");
      setLocation(projectResult.location ?? "");
      setStartDate(projectResult.start_date ?? "");
      setExpectedEndDate(projectResult.expected_end_date ?? "");
      setActualEndDate(projectResult.actual_end_date ?? "");
      setStatus(projectResult.status);
      setClientId(projectResult.client_id ?? "");

      const [clientResult, memberResult, milestoneResult] =
        await Promise.allSettled([
          listClients(),
          listProjectMembers(projectId),
          listMilestones(projectId),
        ]);

      if (clientResult.status === "fulfilled") setClients(clientResult.value);
      if (memberResult.status === "fulfilled") setMembers(memberResult.value);
      if (milestoneResult.status === "fulfilled") {
        setMilestones(milestoneResult.value);
      }

      if (granted.includes("organization.read")) {
        try {
          const orgMembers = await listOrganizationMembers();
          setOrganizationMembers(orgMembers.filter((member) => member.is_active));
        } catch {
        }
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

  async function saveProject() {
    if (!projectId || !name.trim()) {
      setError("Enter a project name.");
      return;
    }
    if (![startDate, expectedEndDate, actualEndDate].every(validDate)) {
      setError("Dates must be valid and use YYYY-MM-DD.");
      return;
    }

    await run(() =>
      updateProject(projectId, {
        name: name.trim(),
        code: clean(code),
        description: clean(description),
        location: clean(location),
        client_id: clientId || null,
        status,
        start_date: startDate || null,
        expected_end_date: expectedEndDate || null,
        actual_end_date: actualEndDate || null,
      }),
    );
  }

  function confirmDeleteProject() {
    if (!projectId) return;
    Alert.alert(
      "Delete project?",
      "This permanently deletes the project and its associated project records.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => {
            void run(async () => {
              await deleteProject(projectId);
              router.replace("/projects");
            });
          },
        },
      ],
    );
  }

  async function saveClient() {
    if (!clientName.trim()) {
      setError("Enter a client name.");
      return;
    }

    const payload = {
      name: clientName.trim(),
      contact_name: clean(clientContact),
      email: clean(clientEmail),
      phone: clean(clientPhone),
    };

    await run(async () => {
      if (editingClientId) {
        await updateClient(editingClientId, payload);
      } else {
        await createClient(payload);
      }
      setClientName("");
      setClientContact("");
      setClientEmail("");
      setClientPhone("");
      setEditingClientId("");
    });
  }

  function beginEditClient(client: Client) {
    setEditingClientId(client.id);
    setClientName(client.name);
    setClientContact(client.contact_name ?? "");
    setClientEmail(client.email ?? "");
    setClientPhone(client.phone ?? "");
  }

  async function assignClient(id: string) {
    if (!projectId) return;
    setClientId(id);
    await run(() =>
      updateProject(projectId, {
        client_id: id || null,
      }),
    );
  }

  function confirmDeleteClient(client: Client) {
    Alert.alert("Delete client?", `Delete ${client.name}?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: () =>
          void run(async () => {
            await deleteClient(client.id);
            if (clientId === client.id && projectId) {
              await updateProject(projectId, { client_id: null });
              setClientId("");
            }
          }),
      },
    ]);
  }

  async function addMember() {
    if (!projectId || !memberUserId) {
      setError("Choose an organization member first.");
      return;
    }
    await run(() => addProjectMember(projectId, memberUserId, memberRole));
    setMemberUserId("");
  }

  async function changeMemberRole(userId: string, role: ProjectMemberRole) {
    if (!projectId) return;
    await run(() => updateProjectMember(projectId, userId, role));
  }

  function confirmRemoveMember(member: ProjectMember) {
    if (!projectId) return;
    Alert.alert(
      "Remove project member?",
      `Remove ${member.user.first_name} ${member.user.last_name} from this project?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () =>
            void run(() => deleteProjectMember(projectId, member.user_id)),
        },
      ],
    );
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
        <Text style={styles.muted}>Loading project management…</Text>
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

  if (!canUpdate && !canDelete) {
    return (
      <View style={styles.page}>
        <Text style={styles.title}>Project management</Text>
        <Text style={styles.error}>
          Your organization role does not allow project updates.
        </Text>
      </View>
    );
  }

  const assignedIds = new Set(members.map((member) => member.user_id));
  const availableMembers = organizationMembers.filter(
    (member) => !assignedIds.has(member.id),
  );

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

        <Text style={styles.title}>Manage project</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}

        {canUpdate ? (
          <>
            <Text style={styles.section}>Project details</Text>
            <Field label="Project name" value={name} onChangeText={setName} />
            <Field label="Project code" value={code} onChangeText={setCode} />
            <Field
              label="Location"
              value={location}
              onChangeText={setLocation}
            />
            <Field
              label="Description"
              value={description}
              onChangeText={setDescription}
              multiline
            />
            <Field
              label="Start date (YYYY-MM-DD)"
              value={startDate}
              onChangeText={setStartDate}
            />
            <Field
              label="Expected end date (YYYY-MM-DD)"
              value={expectedEndDate}
              onChangeText={setExpectedEndDate}
            />
            <Field
              label="Actual end date (YYYY-MM-DD)"
              value={actualEndDate}
              onChangeText={setActualEndDate}
            />

            <Text style={styles.label}>Status</Text>
            <View style={styles.chips}>
              {statuses.map((value) => (
                <Chip
                  key={value}
                  label={value.replaceAll("_", " ")}
                  selected={status === value}
                  onPress={() => setStatus(value)}
                />
              ))}
            </View>

            <Text style={styles.label}>Assign client</Text>
            <Chip
              label="No client"
              selected={!clientId}
              onPress={() => void assignClient("")}
            />
            {clients.map((client) => (
              <Chip
                key={client.id}
                label={client.name}
                selected={clientId === client.id}
                onPress={() => void assignClient(client.id)}
              />
            ))}
            <Action title="Save project" onPress={() => void saveProject()} />
          </>
        ) : null}

        {canUpdate ? (
          <>
            <Text style={styles.section}>Clients</Text>
            <Field
              label="Client name"
              value={clientName}
              onChangeText={setClientName}
            />
            <Field
              label="Contact name"
              value={clientContact}
              onChangeText={setClientContact}
            />
            <Field
              label="Email"
              value={clientEmail}
              onChangeText={setClientEmail}
              keyboardType="email-address"
            />
            <Field
              label="Phone"
              value={clientPhone}
              onChangeText={setClientPhone}
              keyboardType="phone-pad"
            />
            <Action
              title={editingClientId ? "Save client changes" : "Create client"}
              onPress={() => void saveClient()}
            />
            {editingClientId ? (
              <Action
                title="Cancel client edit"
                secondary
                onPress={() => {
                  setEditingClientId("");
                  setClientName("");
                  setClientContact("");
                  setClientEmail("");
                  setClientPhone("");
                }}
              />
            ) : null}
            {clients.map((client) => (
              <View key={client.id} style={styles.card}>
                <Text style={styles.itemTitle}>{client.name}</Text>
                <Text style={styles.muted}>
                  {client.contact_name || client.email || client.phone || ""}
                </Text>
                <View style={styles.row}>
                  <Action
                    title="Edit"
                    secondary
                    onPress={() => beginEditClient(client)}
                  />
                  <Action
                    title="Delete"
                    danger
                    onPress={() => confirmDeleteClient(client)}
                  />
                </View>
              </View>
            ))}
          </>
        ) : null}

        {canUpdate ? (
          <>
            <Text style={styles.section}>Project team</Text>
            {canReadOrganization ? (
              <>
                <Text style={styles.label}>Choose organization member</Text>
                {availableMembers.map((member) => (
                  <Chip
                    key={member.id}
                    label={`${member.first_name} ${member.last_name} · ${member.email}`}
                    selected={memberUserId === member.id}
                    onPress={() => setMemberUserId(member.id)}
                  />
                ))}
                {availableMembers.length === 0 ? (
                  <Text style={styles.muted}>
                    No unassigned active organization members found.
                  </Text>
                ) : null}
                <Text style={styles.label}>Project role</Text>
                <View style={styles.chips}>
                  {roles.map((role) => (
                    <Chip
                      key={role}
                      label={role.replaceAll("_", " ")}
                      selected={memberRole === role}
                      onPress={() => setMemberRole(role)}
                    />
                  ))}
                </View>
                <Action title="Add to project" onPress={() => void addMember()} />
              </>
            ) : (
              <Text style={styles.muted}>
                Your role cannot read organization members, so you cannot add
                project members.
              </Text>
            )}

            {members.map((member) => (
              <View key={member.id} style={styles.card}>
                <Text style={styles.itemTitle}>
                  {member.user.first_name} {member.user.last_name}
                </Text>
                <Text style={styles.muted}>{member.user.email}</Text>
                <Text style={styles.label}>Role: {member.role}</Text>
                <View style={styles.chips}>
                  {roles.map((role) => (
                    <Chip
                      key={role}
                      label={role.replaceAll("_", " ")}
                      selected={member.role === role}
                      onPress={() => void changeMemberRole(member.user_id, role)}
                    />
                  ))}
                </View>
                <Action
                  title="Remove member"
                  danger
                  onPress={() => confirmRemoveMember(member)}
                />
              </View>
            ))}
          </>
        ) : null}

        {canUpdate ? (
          <>
            <Text style={styles.section}>Milestones</Text>
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
          </>
        ) : null}

        {canDelete ? (
          <>
            <Text style={styles.section}>Danger zone</Text>
            <Action
              title="Delete project"
              danger
              onPress={confirmDeleteProject}
            />
          </>
        ) : null}

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
  keyboardType = "default",
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  multiline?: boolean;
  keyboardType?: "default" | "email-address" | "phone-pad";
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
        keyboardType={keyboardType}
        autoCapitalize={keyboardType === "email-address" ? "none" : "sentences"}
      />
    </>
  );
}

function Chip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.chip, selected && styles.chipSelected]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
        {label}
      </Text>
    </Pressable>
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
  page: { flexGrow: 1, padding: 22, paddingTop: 52, paddingBottom: 48, backgroundColor: "#F4F6F8" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8" },
  title: { color: "#17212F", fontSize: 28, fontWeight: "700", marginVertical: 18 },
  section: { color: "#17212F", fontSize: 20, fontWeight: "700", marginTop: 32, marginBottom: 8 },
  label: { color: "#344054", fontSize: 14, fontWeight: "600", marginTop: 14, marginBottom: 7 },
  input: { backgroundColor: "white", borderColor: "#D0D5DD", borderWidth: 1, borderRadius: 10, padding: 14, fontSize: 16, color: "#17212F" },
  multiline: { minHeight: 86 },
  card: { backgroundColor: "white", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 15, marginTop: 10 },
  itemTitle: { color: "#17212F", fontSize: 16, fontWeight: "700" },
  muted: { color: "#667085", marginTop: 6, lineHeight: 20 },
  error: { color: "#B42318", marginVertical: 12, lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700", fontSize: 15 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 },
  chip: { borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 20, backgroundColor: "white", paddingHorizontal: 12, paddingVertical: 9, marginTop: 6 },
  chipSelected: { borderColor: "#183153", backgroundColor: "#E8EEF5" },
  chipText: { color: "#344054", fontSize: 13, fontWeight: "600" },
  chipTextSelected: { color: "#183153" },
  action: { backgroundColor: "#183153", borderRadius: 10, alignItems: "center", padding: 13, marginTop: 10 },
  actionSecondary: { backgroundColor: "white", borderWidth: 1, borderColor: "#D0D5DD" },
  actionDanger: { backgroundColor: "#B42318" },
  actionText: { color: "white", fontWeight: "700" },
  actionSecondaryText: { color: "#183153" },
  actionDangerText: { color: "white" },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  busy: { alignItems: "center", padding: 18, gap: 8 },
});
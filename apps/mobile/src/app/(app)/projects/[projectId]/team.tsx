import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { restoreSession } from "../../../../api/client";
import {addProjectMember, deleteProjectMember, getProject, listOrganizationMembers, listProjectMembers, updateProjectMember,
} from "../../../../api/projects";
import type {OrganizationMember, Project, ProjectMember,  ProjectMemberRole,
} from "../../../../api/types";

const roles: ProjectMemberRole[] = [
  "MANAGER",
  "ENGINEER",
  "SUPERVISOR",
  "SITE_MANAGER",
  "MEMBER",
];

export default function ProjectTeamScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [organizationMembers, setOrganizationMembers] = useState<
    OrganizationMember[]
  >([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState<ProjectMemberRole>("MEMBER");

  const canUpdate = permissions.includes("project.update");
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
      const granted = user.role.permissions.map((p) => p.key);
      setPermissions(granted);

      setProject(await getProject(projectId));

      try {
        setMembers(await listProjectMembers(projectId));
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not load project members.",
        );
      }

      if (granted.includes("organization.read")) {
        try {
          const orgMembers = await listOrganizationMembers();
          setOrganizationMembers(orgMembers.filter((m) => m.is_active));
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

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading project team…</Text>
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
        <Text style={styles.title}>Project team</Text>
        <Text style={styles.error}>
          Your organization role does not allow project updates.
        </Text>
      </View>
    );
  }

  const assignedIds = new Set(members.map((m) => m.user_id));
  const availableMembers = organizationMembers.filter(
    (m) => !assignedIds.has(m.id),
  );

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Pressable onPress={() => router.back()}>
        <Text style={styles.link}>‹  {project.name}</Text>
      </Pressable>

      <Text style={styles.title}>Project team</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}

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
          Your role cannot read organization members, so you cannot add project
          members.
        </Text>
      )}

      <Text style={styles.section}>Current members</Text>
      {members.length === 0 ? (
        <Text style={styles.muted}>No members assigned to this project yet.</Text>
      ) : null}

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

      {busy ? (
        <View style={styles.busy}>
          <ActivityIndicator color="#183153" />
          <Text style={styles.muted}>Saving changes…</Text>
        </View>
      ) : null}
    </ScrollView>
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
  danger = false,
}: {
  title: string;
  onPress: () => void;
  danger?: boolean;
}) {
  return (
    <Pressable
      style={[styles.action, danger && styles.actionDanger]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <Text style={styles.actionText}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 22, paddingTop: 52, paddingBottom: 48, backgroundColor: "#F4F6F8",},
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8",},
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginVertical: 18,},
  section: {color: "#17212F", fontSize: 20,fontWeight: "700", marginTop: 32, marginBottom: 8,},
  label: {color: "#344054", fontSize: 14, fontWeight: "600", marginTop: 14, marginBottom: 7,},
  card: {backgroundColor: "white", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 15, marginTop: 10,},
  itemTitle: { color: "#17212F", fontSize: 16, fontWeight: "700" },
  muted: {color: "#667085", marginTop: 6, lineHeight: 20 },
  error: {color: "#B42318", marginVertical: 12, lineHeight: 20 },
  link: {color: "#183153", fontWeight: "700", fontSize: 15 },
  chips: {flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 },
  chip: {borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 20, backgroundColor: "white", paddingHorizontal: 12, paddingVertical: 9, marginTop: 6,},
  chipSelected: {borderColor: "#183153", backgroundColor: "#E8EEF5" },
  chipText: { color: "#344054", fontSize: 13, fontWeight: "600" },
  chipTextSelected: {color: "#183153" },
  action: {backgroundColor: "#183153", borderRadius: 10, alignItems: "center", padding: 13, marginTop: 10,},
  actionDanger: { backgroundColor: "#B42318" },
  actionText: { color: "white", fontWeight: "700" },
  busy: { alignItems: "center", padding: 18, gap: 8 },
});
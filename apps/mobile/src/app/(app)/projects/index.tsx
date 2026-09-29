import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { Link, router } from "expo-router";
import { restoreSession, signOut } from "../../../api/client";
import { listProjects } from "../../../api/projects";
import type { Project } from "../../../api/types";

export default function ProjectsScreen() {
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
        if (active) setProjects(result);
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Could not load projects.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, [attempt]);

  async function handleSignOut() {
    setBusy(true);
    try {
      await signOut();
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign out.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>Trace</Text>
          <Text style={styles.title}>Projects</Text>
          <Text style={styles.subtitle}>Your organization’s active work</Text>
        </View>

        <View style={{ flexDirection: "row", alignItems: "center", gap: 16 }}>
        <Link href="/organization" asChild>
          <Pressable accessibilityRole="button">
            <Text style={styles.link}>Organization</Text>
          </Pressable>
        </Link>

        <Pressable
          onPress={handleSignOut}
          disabled={busy}
          accessibilityRole="button"
        >
          <Text style={styles.link}>
            {busy ? "Signing out…" : "Sign out"}
          </Text>
        </Pressable>
      </View>
      </View>

      {canCreate ? (
        <Link href="/projects/new" asChild>
          <Pressable style={styles.createButton} accessibilityRole="button">
            <Text style={styles.createButtonText}>＋  Create project</Text>
          </Pressable>
        </Link>
      ) : null}

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#183153" />
          <Text style={styles.muted}>Loading projects…</Text>
        </View>
      ) : error ? (
        <View>
          <Text style={styles.error}>{error}</Text>
          <Pressable
            style={styles.button}
            onPress={() => setAttempt((value) => value + 1)}
          >
            <Text style={styles.buttonText}>Try again</Text>
          </Pressable>
        </View>
      ) : projects.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>No projects yet</Text>
          <Text style={styles.muted}>
            {canCreate
              ? "Create a project to start organizing your site work."
              : "There are no projects to show for your account."}
          </Text>
        </View>
      ) : (
        projects.map((project) => (
          <Pressable
            key={project.id}
            style={styles.card}
            accessibilityRole="button"
            accessibilityLabel={`Open ${project.name}`}
            onPress={() =>
              router.push({
                pathname: "/projects/[projectId]",
                params: { projectId: project.id },
              })
            }
          >
            <View style={styles.cardHeading}>
              <Text style={styles.projectName}>{project.name}</Text>
              <Text style={styles.cardArrow}>›</Text>
            </View>

            {project.code ? (
              <Text style={styles.muted}>Code: {project.code}</Text>
            ) : null}

            {project.location ? (
              <Text style={styles.muted}>{project.location}</Text>
            ) : null}

            <Text style={styles.status}>
              {project.status.replaceAll("_", " ")}
            </Text>
          </Pressable>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 24, paddingTop: 54, backgroundColor: "#F4F6F8",},
  header: {flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 24,},
  brand: { color: "#183153", fontSize: 16, fontWeight: "700" },
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginTop: 6,},
  subtitle: { color: "#667085", fontSize: 14, marginTop: 6 },
  createButton: {backgroundColor: "#183153", borderRadius: 12, padding: 15, alignItems: "center", marginBottom: 18,},
  createButtonText: { color: "white", fontWeight: "700", fontSize: 16 },
  card: {backgroundColor: "white", borderRadius: 14,
  padding: 18, marginBottom: 12, borderWidth: 1, borderColor: "#E4E7EC",},
  cardHeading: {flexDirection: "row", justifyContent: "space-between", alignItems: "center",},
  projectName: {color: "#17212F", fontSize: 18, fontWeight: "700", marginBottom: 8,},
  cardArrow: { color: "#667085", fontSize: 26, marginTop: -8 },
  status: { color: "#183153", fontWeight: "600", marginTop: 10 },
  muted: { color: "#667085", marginTop: 6, lineHeight: 20 },
  error: { color: "#B42318", marginTop: 14 },
  link: { color: "#183153", fontWeight: "600" },
  button: {backgroundColor: "#183153", padding: 14, borderRadius: 10, alignItems: "center", marginTop: 16,},
  buttonText: { color: "white", fontWeight: "700" },
  center: { alignItems: "center", padding: 24, gap: 12 },
  emptyState: {backgroundColor: "white", borderRadius: 14, padding: 20, borderWidth: 1, borderColor: "#E4E7EC",},
  emptyTitle: { color: "#17212F", fontSize: 18, fontWeight: "700" },
});
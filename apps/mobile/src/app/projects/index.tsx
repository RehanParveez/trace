import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router } from "expo-router";
import { restoreSession, signOut } from "../../api/client";
import { listProjects } from "../../api/projects";
import type { Project } from "../../api/types";

export default function ProjectsScreen() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

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
        </View>

        <Pressable onPress={handleSignOut} disabled={busy}>
          <Text style={styles.link}>{busy ? "Signing out…" : "Sign out"}</Text>
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#183153" />
          <Text style={styles.muted}>Loading projects…</Text>
        </View>
      ) : error ? (
        <View>
          <Text style={styles.error}>{error}</Text>
          <Pressable style={styles.button} onPress={() => setAttempt((n) => n + 1)}>
            <Text style={styles.buttonText}>Try again</Text>
          </Pressable>
        </View>
      ) : projects.length === 0 ? (
        <Text style={styles.muted}>There are no projects to show.</Text>
      ) : (
        projects.map((project) => (
          <View key={project.id} style={styles.card}>
            <Text style={styles.projectName}>{project.name}</Text>
            {project.code ? <Text style={styles.muted}>Code: {project.code}</Text> : null}
            {project.location ? <Text style={styles.muted}>{project.location}</Text> : null}
            <Text style={styles.status}>{project.status.replaceAll("_", " ")}</Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 24, backgroundColor: "#F4F6F8" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 24 },
  brand: { color: "#183153", fontSize: 16, fontWeight: "700" },
  title: { color: "#17212F", fontSize: 28, fontWeight: "700", marginTop: 6 },
  card: { backgroundColor: "white", borderRadius: 12, padding: 16, marginBottom: 12 },
  projectName: { color: "#17212F", fontSize: 18, fontWeight: "700", marginBottom: 8 },
  muted: { color: "#667085", marginTop: 6 },
  status: { color: "#183153", fontWeight: "600", marginTop: 10 },
  error: { color: "#B42318", marginTop: 14 },
  link: { color: "#183153", fontWeight: "600" },
  button: { backgroundColor: "#183153", padding: 14, borderRadius: 10, alignItems: "center", marginTop: 16 },
  buttonText: { color: "white", fontWeight: "700" },
  center: { alignItems: "center", padding: 24, gap: 12 },
});
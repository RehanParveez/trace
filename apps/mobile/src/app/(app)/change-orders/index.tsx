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
import { restoreSession } from "../../../api/client";
import { listProjects } from "../../../api/projects";
import type { Project } from "../../../api/types";

export default function ChangeOrdersProjectPickerScreen() {
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
            err instanceof Error ? err.message : "Could not load projects.",
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
  }, [attempt]);

  function openProject(projectId: string) {
    router.push({
      pathname: "/projects/[projectId]/change-orders",
      params: { projectId },
    });
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.brand}>Trace</Text>
      <Text style={styles.title}>Change Orders</Text>
      <Text style={styles.subtitle}>
        Choose a project to review or create change orders.
      </Text>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#183153" />
          <Text style={styles.muted}>Loading projects…</Text>
        </View>
      ) : error ? (
        <View style={styles.card}>
          <Text style={styles.error}>{error}</Text>
          <Pressable
            style={styles.button}
            accessibilityRole="button"
            onPress={() => setAttempt((value) => value + 1)}
          >
            <Text style={styles.buttonText}>Try again</Text>
          </Pressable>
        </View>
      ) : canRead === false ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Access unavailable</Text>
          <Text style={styles.muted}>
            Your role does not have permission to read change orders.
          </Text>
        </View>
      ) : projects.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>No projects available</Text>
          <Text style={styles.muted}>
            Create or join a project before opening its change orders.
          </Text>
        </View>
      ) : (
        <View style={styles.list}>
          <Text style={styles.sectionTitle}>Select a project</Text>
          {projects.map((project) => (
            <Pressable
              key={project.id}
              style={styles.card}
              accessibilityRole="button"
              accessibilityLabel={`Open change orders for ${project.name}`}
              onPress={() => openProject(project.id)}
            >
              <View style={styles.row}>
                <Text style={styles.cardTitle}>{project.name}</Text>
                <Text style={styles.arrow}>›</Text>
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
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 24, paddingTop: 30, paddingBottom: 40, backgroundColor: "#F4F6F8",},
  brand: { color: "#183153", fontSize: 16, fontWeight: "700" },
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginTop: 6,},
  subtitle: {color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 6, marginBottom: 22,},
  list: { gap: 10 },
  sectionTitle: {color: "#17212F", fontSize: 17, fontWeight: "700", marginBottom: 2,},
  card: {backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#E4E7EC", padding: 18, marginTop: 10,},
  row: {flexDirection: "row", alignItems: "center", justifyContent: "space-between",},
  cardTitle: { color: "#17212F", fontSize: 17, fontWeight: "700" },
  arrow: { color: "#667085", fontSize: 26 },
  muted: { color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 6 },
  status: { color: "#183153", fontSize: 12, fontWeight: "700", marginTop: 12 },
  center: { alignItems: "center", padding: 28, gap: 12 },
  error: { color: "#B42318", lineHeight: 20 },
  button: {backgroundColor: "#183153", borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16,},
  buttonText: { color: "#FFFFFF", fontWeight: "700" },
});
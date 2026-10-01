import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router, useLocalSearchParams, Link } from "expo-router";
import { restoreSession } from "../../../api/client";
import { getProject, listClients } from "../../../api/projects";
import type { Client, Project } from "../../../api/types";

function formatDate(value: string | null): string {
  if (!value) return "Not set";
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

export default function ProjectDetailScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    async function load() {
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

        const projectResult = await getProject(projectId);
        if (!active) return;
        setProject(projectResult);

        try {
          const clientResult = await listClients();
          if (active) setClients(clientResult);
        } catch {
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Could not load this project.",
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
  }, [projectId, attempt]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading project…</Text>
      </View>
    );
  }

  if (error || !project) {
    return (
      <View style={styles.page}>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  Projects</Text>
        </Pressable>
        <Text style={styles.error}>{error || "Project not found."}</Text>
        <Pressable
          style={styles.secondaryButton}
          onPress={() => setAttempt((v) => v + 1)}
        >
          <Text style={styles.secondaryButtonText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const client = clients.find((item) => item.id === project.client_id);

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Pressable onPress={() => router.back()}>
        <Text style={styles.link}>‹  Projects</Text>
      </Pressable>

      <View style={styles.hero}>
        <Text style={styles.eyebrow}>PROJECT</Text>
        <Text style={styles.title}>{project.name}</Text>
        {project.code ? (
          <Text style={styles.heroSubtitle}>{project.code}</Text>
        ) : null}
        <Text style={styles.status}>
          {project.status.replaceAll("_", " ")}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Project overview</Text>
        {project.description ? (
          <Text style={styles.description}>{project.description}</Text>
        ) : null}
        <InfoRow label="Client" value={client?.name || "Not assigned"} />
        <InfoRow label="Location" value={project.location || "Not set"} />
        <InfoRow label="Start date" value={formatDate(project.start_date)} />
        <InfoRow
          label="Expected completion"
          value={formatDate(project.expected_end_date)}
        />
        <InfoRow
          label="Actual completion"
          value={formatDate(project.actual_end_date)}
        />
      </View>

      <Link
        href={{
          pathname: "/projects/[projectId]/manage",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Manage project</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/team",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Project team</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/milestones",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Milestones</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/drawings-boq",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Drawings & BOQ</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/progress-verification",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Progress verification</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/site-photos",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Site Photos</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/site-progress",
          params: { projectId: project.id },
        }}
        asChild
      >
       <Pressable style={styles.secondaryButton} accessibilityRole="button">
         <Text style={styles.secondaryButtonText}>Site Progress</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/subcontractors",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Subcontractors</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/labour",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
          <Text style={styles.secondaryButtonText}>Labour</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/bank-guarantees",
          params: { projectId: project.id },
        }}
        asChild
      >
       <Pressable style={styles.secondaryButton} accessibilityRole="button">
        <Text style={styles.secondaryButtonText}>Bank guarantees</Text>
       </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/change-orders",
          params: { projectId: project.id },
        }}
        asChild
      >
       <Pressable style={styles.secondaryButton} accessibilityRole="button">
        <Text style={styles.secondaryButtonText}>Change Orders</Text>
       </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/budgets",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
         <Text style={styles.secondaryButtonText}>Budget</Text>
        </Pressable>
      </Link>

      <Link
        href={{
          pathname: "/projects/[projectId]/expenses",
          params: { projectId: project.id },
        }}
        asChild
      >
        <Pressable style={styles.secondaryButton} accessibilityRole="button">
         <Text style={styles.secondaryButtonText}>Expenses</Text>
        </Pressable>
      </Link>

      <Pressable
        style={styles.secondaryButton}
        onPress={() => setAttempt((v) => v + 1)}
      >
        <Text style={styles.secondaryButtonText}>Refresh project</Text>
      </Pressable>
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 22, paddingTop: 52, paddingBottom: 40, backgroundColor: "#F4F6F8",},
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8",},
  hero: {backgroundColor: "#183153", borderRadius: 18, padding: 22, marginTop: 20, marginBottom: 18,},
  eyebrow: {color: "#B9C8DA", fontSize: 12, fontWeight: "700", letterSpacing: 1.2,},
  title: { color: "white", fontSize: 26, fontWeight: "700", marginTop: 8 },
  heroSubtitle: { color: "#D7E0EA", fontSize: 15, marginTop: 5 },
  status: {color: "white", backgroundColor: "#385579", borderRadius: 20, overflow: "hidden", alignSelf: "flex-start", paddingHorizontal: 12, paddingVertical: 6, marginTop: 14, fontWeight: "600",},
  card: {backgroundColor: "white", borderRadius: 14, borderWidth: 1, borderColor: "#E4E7EC", padding: 17, marginBottom: 12,},
  sectionTitle: { color: "#17212F", fontSize: 18, fontWeight: "700" },
  description: { color: "#344054", lineHeight: 21, marginBottom: 12 },
  infoRow: {flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 9, borderTopWidth: 1, borderTopColor: "#F0F2F5",},
  infoLabel: { color: "#667085", fontSize: 13, flex: 1 },
  infoValue: {color: "#17212F", fontSize: 13, fontWeight: "600", flex: 1, textAlign: "right",},
  muted: { color: "#667085", marginTop: 5, lineHeight: 20 },
  error: { color: "#B42318", marginTop: 12, lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700" },
  secondaryButton: {borderWidth: 1, borderColor: "#D0D5DD", backgroundColor: "white", borderRadius: 10, alignItems: "center", padding: 14, marginTop: 12,},
  secondaryButtonText: { color: "#183153", fontWeight: "700" },
});
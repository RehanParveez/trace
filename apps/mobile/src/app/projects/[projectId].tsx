import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router, useLocalSearchParams, Link } from "expo-router";
import { restoreSession } from "../../api/client";
import { getProject, listClients } from "../../api/projects";
import {
  getBOQSummary,
  listBOQItems,
  listProjectBOQVersions,
  listProjectDrawings,
} from "../../api/drawingsBoq";
import type {
  BOQItem,
  BOQSummary,
  BOQVersion,
  Client,
  Drawing,
  Project,
} from "../../api/types";

function formatDate(value: string | null): string {
  if (!value) return "Not set";
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function formatMoney(value: number | string | null): string {
  if (value === null) return "Not available";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);

  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency: "PKR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function ProjectDetailScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [versions, setVersions] = useState<BOQVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [drawingsError, setDrawingsError] = useState("");
  const [boqError, setBoqError] = useState("");
  const [attempt, setAttempt] = useState(0);

  const [expandedVersion, setExpandedVersion] = useState("");
  const [boqLoading, setBoqLoading] = useState(false);
  const [boqItems, setBoqItems] = useState<BOQItem[]>([]);
  const [boqSummary, setBoqSummary] = useState<BOQSummary | null>(null);
  const boqRequest = useRef(0);

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
      setDrawingsError("");
      setBoqError("");

      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }

        const projectResult = await getProject(projectId);
        if (!active) return;
        setProject(projectResult);

        const [clientResult, drawingResult, versionResult] =
          await Promise.allSettled([
            listClients(),
            listProjectDrawings(projectId),
            listProjectBOQVersions(projectId),
          ]);

        if (!active) return;

        if (clientResult.status === "fulfilled") {
          setClients(clientResult.value);
        }

        if (drawingResult.status === "fulfilled") {
          setDrawings(drawingResult.value);
        } else {
          setDrawingsError(
            drawingResult.reason instanceof Error
              ? drawingResult.reason.message
              : "Could not load drawings.",
          );
        }

        if (versionResult.status === "fulfilled") {
          setVersions(versionResult.value);
        } else {
          setBoqError(
            versionResult.reason instanceof Error
              ? versionResult.reason.message
              : "Could not load BOQ versions.",
          );
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

  async function toggleVersion(version: BOQVersion) {
    if (expandedVersion === version.id) {
      boqRequest.current += 1;
      setExpandedVersion("");
      setBoqLoading(false);
      return;
    }

    const requestId = boqRequest.current + 1;
    boqRequest.current = requestId;
    setExpandedVersion(version.id);
    setBoqLoading(true);
    setBoqError("");
    setBoqItems([]);
    setBoqSummary(null);

    try {
      const [items, summary] = await Promise.all([
        listBOQItems(version.id),
        getBOQSummary(version.id),
      ]);

      if (boqRequest.current === requestId) {
        setBoqItems(items);
        setBoqSummary(summary);
      }
    } catch (err) {
      if (boqRequest.current === requestId) {
        setBoqError(
          err instanceof Error ? err.message : "Could not load this BOQ version.",
        );
      }
    } finally {
      if (boqRequest.current === requestId) setBoqLoading(false);
    }
  }

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
          onPress={() => setAttempt((value) => value + 1)}
        >
          <Text style={styles.secondaryButtonText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const client = clients.find((item) => item.id === project.client_id);
  const currentDrawings = drawings.filter(
    (drawing) => drawing.is_current_revision,
  );

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Pressable onPress={() => router.back()}>
        <Text style={styles.link}>‹  Projects</Text>
      </Pressable>

      <View style={styles.hero}>
        <Text style={styles.eyebrow}>PROJECT</Text>
        <Text style={styles.title}>{project.name}</Text>
        {project.code ? <Text style={styles.heroSubtitle}>{project.code}</Text> : null}
        <Text style={styles.status}>{project.status.replaceAll("_", " ")}</Text>
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
        <Pressable
          style={styles.secondaryButton}
          accessibilityRole="button"
        >
          <Text style={styles.secondaryButtonText}>Manage project</Text>
        </Pressable>
      </Link>

      <SectionHeading
        title="Drawings"
        hint="Current drawing revisions for this project"
        count={currentDrawings.length}
      />

      {drawingsError ? <Text style={styles.error}>{drawingsError}</Text> : null}

      {!drawingsError && currentDrawings.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>
            No drawings have been added to this project yet.
          </Text>
        </View>
      ) : (
        currentDrawings.map((drawing) => (
          <View key={drawing.id} style={styles.listCard}>
            <Text style={styles.itemTitle}>{drawing.original_filename}</Text>
            <Text style={styles.muted}>
              {drawing.format} · {drawing.status.replaceAll("_", " ")}
            </Text>
            {drawing.revision_label ? (
              <Text style={styles.muted}>Revision {drawing.revision_label}</Text>
            ) : null}
            {drawing.error_message ? (
              <Text style={styles.error}>{drawing.error_message}</Text>
            ) : null}
          </View>
        ))
      )}

      <SectionHeading
        title="Bill of quantities"
        hint="BOQ versions associated with this project"
        count={versions.length}
      />

      {boqError && !expandedVersion ? (
        <Text style={styles.error}>{boqError}</Text>
      ) : null}

      {!boqError && versions.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>
            No BOQ versions have been created for this project yet.
          </Text>
        </View>
      ) : (
        versions.map((version) => (
          <View key={version.id} style={styles.listCard}>
            <Pressable
              onPress={() => void toggleVersion(version)}
              accessibilityRole="button"
            >
              <View style={styles.versionHeading}>
                <View style={styles.versionCopy}>
                  <Text style={styles.itemTitle}>{version.label}</Text>
                  <Text style={styles.muted}>
                    {version.status.replaceAll("_", " ")} ·{" "}
                    {formatDate(version.created_at)}
                  </Text>
                </View>
                <Text style={styles.link}>
                  {expandedVersion === version.id ? "Hide" : "View"}
                </Text>
              </View>
            </Pressable>

            {expandedVersion === version.id ? (
              <View style={styles.versionDetails}>
                {boqLoading ? <ActivityIndicator color="#183153" /> : null}
                {boqError ? <Text style={styles.error}>{boqError}</Text> : null}

                {boqSummary ? (
                  <View style={styles.summaryBox}>
                    <InfoRow label="Items" value={String(boqSummary.item_count)} />
                    <InfoRow
                      label="Total"
                      value={formatMoney(boqSummary.grand_total)}
                    />
                    <InfoRow
                      label="Awaiting approval"
                      value={String(boqSummary.unapproved_item_count)}
                    />
                    <InfoRow
                      label="Unpriced items"
                      value={String(boqSummary.unpriced_item_count)}
                    />
                  </View>
                ) : null}

                {!boqLoading && !boqError && boqItems.length === 0 ? (
                  <Text style={styles.muted}>This BOQ has no items yet.</Text>
                ) : null}

                {boqItems.map((item) => (
                  <View key={item.id} style={styles.boqItem}>
                    <View style={styles.versionHeading}>
                      <Text style={styles.itemTitle}>{item.material_name}</Text>
                      <Text
                        style={
                          item.status === "APPROVED"
                            ? styles.approved
                            : styles.draft
                        }
                      >
                        {item.status}
                      </Text>
                    </View>
                    <Text style={styles.muted}>
                      {item.quantity} {item.unit}
                      {item.category ? ` · ${item.category}` : ""}
                    </Text>
                    <Text style={styles.muted}>
                      {item.unit_rate === null
                        ? "Rate not set"
                        : `${formatMoney(item.unit_rate)} per ${item.unit}`}
                    </Text>
                  </View>
                ))}
              </View>
            ) : null}
          </View>
        ))
      )}

      <Pressable
        style={styles.secondaryButton}
        onPress={() => setAttempt((value) => value + 1)}
      >
        <Text style={styles.secondaryButtonText}>Refresh project</Text>
      </Pressable>
    </ScrollView>
  );
}

function SectionHeading({
  title,
  hint,
  count,
}: {
  title: string;
  hint: string;
  count: number;
}) {
  return (
    <View style={styles.sectionHeading}>
      <View style={styles.sectionCopy}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Text style={styles.sectionHint}>{hint}</Text>
      </View>
      <Text style={styles.count}>{count}</Text>
    </View>
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
  sectionHeading: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 20, marginBottom: 10,},
  sectionCopy: { flex: 1 },
  sectionTitle: { color: "#17212F", fontSize: 18, fontWeight: "700" },
  sectionHint: { color: "#667085", fontSize: 13, marginTop: 4 },
  count: {color: "#183153", backgroundColor: "#E8EEF5", borderRadius: 18, overflow: "hidden", minWidth: 34, textAlign: "center", paddingHorizontal: 10, paddingVertical: 6, fontWeight: "700",},
  listCard: {backgroundColor: "white", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 16, marginBottom: 10,},
  itemTitle: {flex: 1, color: "#17212F", fontSize: 15, fontWeight: "700", marginRight: 8,},
  description: { color: "#344054", lineHeight: 21, marginBottom: 12 },
  infoRow: {flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 9, borderTopWidth: 1, borderTopColor: "#F0F2F5",},
  infoLabel: { color: "#667085", fontSize: 13, flex: 1 },
  infoValue: {color: "#17212F", fontSize: 13, fontWeight: "600", flex: 1, textAlign: "right",},
  versionHeading: {flexDirection: "row", alignItems: "center", justifyContent: "space-between",},
  versionCopy: { flex: 1 },
  versionDetails: {borderTopWidth: 1, borderTopColor: "#E4E7EC", marginTop: 14, paddingTop: 14,},
  summaryBox: {backgroundColor: "#F8FAFC", borderRadius: 10, paddingHorizontal: 12, paddingTop: 4, marginBottom: 12,},
  boqItem: {borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 12,},
  approved: { color: "#067647", fontSize: 11, fontWeight: "700" },
  draft: { color: "#B54708", fontSize: 11, fontWeight: "700" },
  muted: { color: "#667085", marginTop: 5, lineHeight: 20 },
  error: { color: "#B42318", marginTop: 12, lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700" },
  secondaryButton: {borderWidth: 1, borderColor: "#D0D5DD", backgroundColor: "white", borderRadius: 10, alignItems: "center", padding: 14, marginTop: 18,},
  secondaryButtonText: { color: "#183153", fontWeight: "700" },
});
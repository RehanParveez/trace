import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { restoreSession } from "../api/client";
import {getAIUsageSummary, listAIRequests,
} from "../api/ai_requests";
import type {AIEntityType, AIRequestPurpose, AIRequestRecord, AIUsageSummary, AuthUser,
} from "../api/types";

const PAGE_SIZE = 100;

const PURPOSES: Array<AIRequestPurpose | "ALL"> = [
  "ALL",
  "MATERIAL_NORMALIZATION",
  "CAPTION_PARSING",
  "PHOTO_TAGGING",
  "PDF_SCHEDULE_EXTRACTION",
];

const ENTITY_TYPES: Array<AIEntityType | "ALL"> = [
  "ALL",
  "DRAWING_ELEMENT",
  "SITE_PHOTO",
  "WHATSAPP_MESSAGE",
  "DRAWING",
];

function label(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function AIRequestsScreen() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [permissionChecked, setPermissionChecked] = useState(false);
  const [canRead, setCanRead] = useState(false);

  const [rows, setRows] = useState<AIRequestRecord[]>([]);
  const [summary, setSummary] = useState<AIUsageSummary | null>(null);
  const [purpose, setPurpose] = useState<AIRequestPurpose | "ALL">("ALL");
  const [entityType, setEntityType] = useState<AIEntityType | "ALL">("ALL");
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const currentUser = await restoreSession();
        if (!currentUser) {
          const { router } = await import("expo-router");
          router.replace("/");
          return;
        }
        if (!active) return;

        setUser(currentUser);
        const permitted = currentUser.role.permissions.some(
          (permission) => permission.key === "ai_request:read",
        );
        setCanRead(permitted);
        setPermissionChecked(true);

        if (!permitted) {
          setRows([]);
          setSummary(null);
          return;
        }

        const [requestRows, usage] = await Promise.all([
          listAIRequests({
            purpose: purpose === "ALL" ? undefined : purpose,
            entity_type: entityType === "ALL" ? undefined : entityType,
            skip: 0,
            limit: PAGE_SIZE,
          }),
          getAIUsageSummary(),
        ]);

        if (!active) return;
        setRows(requestRows);
        setSummary(usage);
        setSkip(requestRows.length);
        setHasMore(requestRows.length === PAGE_SIZE);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Could not load AI activity.",
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
  }, [purpose, entityType, attempt]);

  async function loadMore() {
    if (!canRead || loadingMore || !hasMore) return;

    setLoadingMore(true);
    setError("");

    try {
      const nextRows = await listAIRequests({
        purpose: purpose === "ALL" ? undefined : purpose,
        entity_type: entityType === "ALL" ? undefined : entityType,
        skip,
        limit: PAGE_SIZE,
      });

      setRows((current) => [...current, ...nextRows]);
      setSkip((current) => current + nextRows.length);
      setHasMore(nextRows.length === PAGE_SIZE);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load more AI activity.",
      );
    } finally {
      setLoadingMore(false);
    }
  }

  if (loading || !permissionChecked) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading AI activity…</Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <Text style={styles.title}>AI Requests</Text>
        <Text style={styles.error}>
          You do not have permission to view AI request history.
        </Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.heading}>
        <View>
          <Text style={styles.eyebrow}>ACTIVITY</Text>
          <Text style={styles.title}>AI Requests</Text>
        </View>
        <Pressable
          onPress={() => setAttempt((value) => value + 1)}
          accessibilityRole="button"
        >
          <Text style={styles.link}>Refresh</Text>
        </Pressable>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {summary ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Usage summary</Text>
          <InfoRow label="Total requests" value={String(summary.total_requests)} />
          <InfoRow label="Succeeded" value={String(summary.succeeded)} />
          <InfoRow label="Failed" value={String(summary.failed)} />
          <InfoRow
            label="Average latency"
            value={
              summary.average_latency_ms == null
                ? "Not available"
                : `${Math.round(summary.average_latency_ms)} ms`
            }
          />
        </View>
      ) : null}

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Purpose</Text>
        <ChoiceRow
          values={PURPOSES}
          selected={purpose}
          onSelect={setPurpose}
        />
        <Text style={[styles.sectionTitle, styles.filterHeading]}>
          Entity type
        </Text>
        <ChoiceRow
          values={ENTITY_TYPES}
          selected={entityType}
          onSelect={setEntityType}
        />
      </View>

      <View style={styles.heading}>
        <Text style={styles.sectionTitle}>Request history</Text>
        <Text style={styles.muted}>{rows.length} loaded</Text>
      </View>

      {rows.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>No AI requests match these filters.</Text>
        </View>
      ) : (
        rows.map((request) => (
          <View key={request.id} style={styles.card}>
            <View style={styles.heading}>
              <Text style={styles.sectionTitle}>{label(request.purpose)}</Text>
              <Text
                style={[
                  styles.badge,
                  request.response?.status === "FAILED" && styles.failedBadge,
                ]}
              >
                {request.response ? label(request.response.status) : "Pending"}
              </Text>
            </View>

            <InfoRow label="Provider" value={label(request.provider)} />
            <InfoRow label="Model" value={request.model} />
            <InfoRow
              label="Entity"
              value={
                request.entity_type
                  ? `${label(request.entity_type)}${request.entity_id ? ` · ${request.entity_id}` : ""}`
                  : "Not linked"
              }
            />
            <InfoRow label="Requested" value={formatDate(request.created_at)} />

            {request.response?.latency_ms != null ? (
              <InfoRow
                label="Latency"
                value={`${request.response.latency_ms} ms`}
              />
            ) : null}

            {request.response?.error_message ? (
              <Text style={styles.error}>{request.response.error_message}</Text>
            ) : null}

            {request.response?.parsed_output ? (
              <View style={styles.output}>
                <Text style={styles.outputLabel}>Parsed output</Text>
                <Text selectable style={styles.outputText}>
                  {JSON.stringify(request.response.parsed_output, null, 2)}
                </Text>
              </View>
            ) : null}
          </View>
        ))
      )}

      {hasMore ? (
        <ActionButton
          label={loadingMore ? "Loading…" : "Load more"}
          onPress={() => void loadMore()}
          disabled={loadingMore}
        />
      ) : null}
    </ScrollView>
  );
}

function ChoiceRow<T extends string>({
  values,
  selected,
  onSelect,
}: {
  values: T[];
  selected: T;
  onSelect: (value: T) => void;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <View style={styles.choices}>
        {values.map((value) => (
          <Pressable
            key={value}
            onPress={() => onSelect(value)}
            style={[
              styles.choice,
              selected === value && styles.choiceSelected,
            ]}
          >
            <Text
              style={[
                styles.choiceText,
                selected === value && styles.choiceTextSelected,
              ]}
            >
              {value === "ALL" ? "All" : label(value)}
            </Text>
          </Pressable>
        ))}
      </View>
    </ScrollView>
  );
}

function InfoRow({ label: title, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.muted}>{title}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function ActionButton({
  label: title,
  onPress,
  disabled,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      style={[styles.button, disabled && styles.disabled]}
    >
      <Text style={styles.buttonText}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 30, paddingBottom: 40, backgroundColor: "#F4F6F8" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8" },
  heading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10 },
  eyebrow: { color: "#8A7B67", fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: "#17212F", fontSize: 25, fontWeight: "800", marginTop: 5 },
  sectionTitle: { color: "#17212F", fontSize: 16, fontWeight: "700" },
  filterHeading: { marginTop: 16, marginBottom: 8 },
  card: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E4E7EC", borderRadius: 14, padding: 16, marginBottom: 12 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 8 },
  infoValue: { flex: 1, color: "#17212F", textAlign: "right", fontWeight: "600" },
  muted: { color: "#667085", lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700" },
  error: { color: "#B42318", lineHeight: 20, marginTop: 8 },
  badge: { color: "#027A48", backgroundColor: "#ECFDF3", paddingHorizontal: 9, paddingVertical: 5, overflow: "hidden", borderRadius: 20, fontSize: 12, fontWeight: "700" },
  failedBadge: { color: "#B42318", backgroundColor: "#FEF3F2" },
  choices: { flexDirection: "row", gap: 8, paddingVertical: 4 },
  choice: { borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 18, paddingHorizontal: 11, paddingVertical: 8 },
  choiceSelected: { backgroundColor: "#183153", borderColor: "#183153" },
  choiceText: { color: "#344054", fontSize: 12, fontWeight: "600" },
  choiceTextSelected: { color: "#FFFFFF" },
  output: { backgroundColor: "#F4F6F8", borderRadius: 8, padding: 10, marginTop: 10 },
  outputLabel: { fontWeight: "700", color: "#344054", marginBottom: 6 },
  outputText: { color: "#344054", fontSize: 12, lineHeight: 18 },
  button: { minHeight: 46, backgroundColor: "#183153", borderRadius: 10, alignItems: "center", justifyContent: "center", padding: 12, marginTop: 8 },
  buttonText: { color: "#FFFFFF", fontWeight: "700" },
  disabled: { opacity: 0.55 },
});
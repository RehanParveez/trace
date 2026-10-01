import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text,TextInput, View,
} from "react-native";
import { restoreSession } from "../api/client";
import { getLatestAuditByEntityType, listAuditLogForEntity, listAuditLogs,
} from "../api/audit";
import type {AuditAction, AuditEntityType, AuditLogEntry, AuthUser, EntityActivitySummary,
} from "../api/types";

const PAGE_SIZE = 100;

const ENTITY_TYPES: AuditEntityType[] = [
  "ORGANIZATION",
  "ROLE",
  "MEMBER",
  "INVITATION",
  "SUBSCRIPTION",
  "PROJECT",
  "BOQ_ITEM",
  "DRAWING",
  "PROGRESS_CLAIM",
  "WHATSAPP_CHANNEL",
  "MATERIAL_LIBRARY",
  "SITE_PHOTO",
  "RUNNING_BILL",
  "labour",
  "subcontractor",
  "retention",
  "CHANGE_ORDER",
  "SCHEDULE_TASK",
  "PUNCH_LIST",
  "BANK_GUARANTEE",
];

const ACTIONS: AuditAction[] = [
  "CREATE",
  "UPDATE",
  "DELETE",
  "APPROVE",
  "REJECT",
  "STATUS_CHANGE",
];

function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value;
}

function dateBound(value: string, endOfDay: boolean): string | undefined {
  if (!value) return undefined;
  const time = endOfDay ? "23:59:59.999" : "00:00:00.000";
  return new Date(`${value}T${time}Z`).toISOString();
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function humanize(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function entityKey(type: string, id: string): string {
  return `${type}:${id}`;
}

export function AuditLogScreen() {
  const [permissionChecked, setPermissionChecked] = useState(false);
  const [canRead, setCanRead] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");

  const [entityTypeInput, setEntityTypeInput] = useState("");
  const [entityIdInput, setEntityIdInput] = useState("");
  const [actorIdInput, setActorIdInput] = useState("");
  const [actionInput, setActionInput] = useState("");
  const [fromInput, setFromInput] = useState("");
  const [toInput, setToInput] = useState("");

  const [filters, setFilters] = useState<{
    entity_type?: AuditEntityType;
    entity_id?: string;
    actor_user_id?: string;
    action?: AuditAction;
    created_from?: string;
    created_to?: string;
  }>({});

  const [expandedIds, setExpandedIds] = useState<string[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [entityHistory, setEntityHistory] = useState<AuditLogEntry[]>([]);
  const [loadingEntity, setLoadingEntity] = useState(false);
  const [latestRows, setLatestRows] = useState<EntityActivitySummary[]>([]);
  const [loadingLatest, setLoadingLatest] = useState(false);

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
          (permission) => permission.key === "audit_log:read",
        );
        setCanRead(permitted);
        setPermissionChecked(true);

        if (!permitted) {
          setEntries([]);
          return;
        }

        const rows = await listAuditLogs({
          ...filters,
          skip: 0,
          limit: PAGE_SIZE,
        });
        if (!active) return;

        setEntries(rows);
        setSkip(rows.length);
        setHasMore(rows.length === PAGE_SIZE);
        setSelectedEntity(null);
        setEntityHistory([]);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Could not load the audit log.",
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
  }, [filters, attempt]);

  function applyFilters() {
    setError("");

    const entityType = entityTypeInput.trim();
    const action = actionInput.trim();
    const entityId = entityIdInput.trim();
    const actorId = actorIdInput.trim();
    const from = fromInput.trim();
    const to = toInput.trim();

    if (entityType && !ENTITY_TYPES.includes(entityType as AuditEntityType)) {
      setError("Choose an entity type from the listed backend values.");
      return;
    }
    if (action && !ACTIONS.includes(action as AuditAction)) {
      setError("Choose an action from the listed backend values.");
      return;
    }
    if (from && !validDate(from)) {
      setError("Start date must be a real date in YYYY-MM-DD format.");
      return;
    }
    if (to && !validDate(to)) {
      setError("End date must be a real date in YYYY-MM-DD format.");
      return;
    }
    if (from && to && from > to) {
      setError("Start date cannot be later than end date.");
      return;
    }

    setFilters({
      entity_type: entityType
        ? (entityType as AuditEntityType)
        : undefined,
      entity_id: entityId || undefined,
      actor_user_id: actorId || undefined,
      action: action ? (action as AuditAction) : undefined,
      created_from: dateBound(from, false),
      created_to: dateBound(to, true),
    });
  }

  async function loadMore() {
    if (!canRead || loadingMore || !hasMore) return;

    setLoadingMore(true);
    setError("");

    try {
      const rows = await listAuditLogs({
        ...filters,
        skip,
        limit: PAGE_SIZE,
      });
      setEntries((current) => [...current, ...rows]);
      setSkip((current) => current + rows.length);
      setHasMore(rows.length === PAGE_SIZE);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load more audit entries.",
      );
    } finally {
      setLoadingMore(false);
    }
  }

  async function showLatestByType() {
    if (!canRead) return;
    if (!filters.entity_type) {
      setError("Select an entity type first to load latest activity by type.");
      return;
    }

    setLoadingLatest(true);
    setError("");

    try {
      const rows = await getLatestAuditByEntityType(filters.entity_type);
      setLatestRows(rows);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load latest entity activity.",
      );
    } finally {
      setLoadingLatest(false);
    }
  }

  async function showEntityHistory(entry: AuditLogEntry) {
    if (!canRead || !entry.entity_id) return;

    const key = entityKey(entry.entity_type, entry.entity_id);
    if (selectedEntity === key) {
      setSelectedEntity(null);
      setEntityHistory([]);
      return;
    }

    setSelectedEntity(key);
    setLoadingEntity(true);
    setError("");

    try {
      const rows = await listAuditLogForEntity(
        entry.entity_type,
        entry.entity_id,
      );
      setEntityHistory(rows);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load this entity's history.",
      );
    } finally {
      setLoadingEntity(false);
    }
  }

  function toggleChanges(id: string) {
    setExpandedIds((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
  }

  if (loading || !permissionChecked) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading audit log…</Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <Text style={styles.title}>Audit Log</Text>
        <Text style={styles.error}>
          You do not have permission to view the audit log.
        </Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.header}>
        <View>
          <Text style={styles.eyebrow}>ACTIVITY</Text>
          <Text style={styles.title}>Audit Log</Text>
        </View>
        <Pressable
          onPress={() => setAttempt((value) => value + 1)}
          accessibilityRole="button"
        >
          <Text style={styles.link}>Refresh</Text>
        </Pressable>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Filters</Text>

        <Field
          label={`Entity type (${ENTITY_TYPES.join(", ")})`}
          value={entityTypeInput}
          onChangeText={setEntityTypeInput}
          placeholder="Leave blank for all"
          autoCapitalize="characters"
        />
        <Field
          label={`Action (${ACTIONS.join(", ")})`}
          value={actionInput}
          onChangeText={setActionInput}
          placeholder="Leave blank for all"
          autoCapitalize="characters"
        />
        <Field
          label="Entity ID (optional)"
          value={entityIdInput}
          onChangeText={setEntityIdInput}
          placeholder="UUID"
          autoCapitalize="none"
        />
        <Field
          label="Actor user ID (optional)"
          value={actorIdInput}
          onChangeText={setActorIdInput}
          placeholder="UUID"
          autoCapitalize="none"
        />
        <Field
          label="Created from (YYYY-MM-DD)"
          value={fromInput}
          onChangeText={setFromInput}
          placeholder="YYYY-MM-DD"
          autoCapitalize="none"
        />
        <Field
          label="Created to (YYYY-MM-DD)"
          value={toInput}
          onChangeText={setToInput}
          placeholder="YYYY-MM-DD"
          autoCapitalize="none"
        />

        <ActionButton label="Apply filters" onPress={applyFilters} />
        <ActionButton
          label="Clear filters"
          secondary
          onPress={() => {
            setEntityTypeInput("");
            setEntityIdInput("");
            setActorIdInput("");
            setActionInput("");
            setFromInput("");
            setToInput("");
            setFilters({});
            setLatestRows([]);
          }}
        />
        <ActionButton
          label={loadingLatest ? "Loading latest…" : "Latest by entity type"}
          secondary
          disabled={loadingLatest}
          onPress={() => void showLatestByType()}
        />
      </View>

      {latestRows.length > 0 ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Latest activity by entity</Text>
          {latestRows.map((item) => (
            <View
              key={item.entity_id}
              style={styles.latestRow}
            >
              <Text style={styles.body}>{item.last_summary}</Text>
              <Text style={styles.muted}>
                {humanize(item.last_action)} · {formatDate(item.last_created_at)}
              </Text>
              <Text selectable style={styles.idText}>{item.entity_id}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={styles.header}>
        <Text style={styles.sectionTitle}>Entries</Text>
        <Text style={styles.muted}>{entries.length} loaded</Text>
      </View>

      {entries.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>No audit entries match these filters.</Text>
        </View>
      ) : (
        entries.map((entry) => {
          const key =
            entry.entity_id == null
              ? ""
              : entityKey(entry.entity_type, entry.entity_id);
          const changesExpanded = expandedIds.includes(entry.id);

          return (
            <View key={entry.id} style={styles.card}>
              <Text style={styles.sectionTitle}>{entry.summary}</Text>
              <InfoRow label="Action" value={humanize(entry.action)} />
              <InfoRow label="Entity" value={humanize(entry.entity_type)} />
              {entry.entity_id ? (
                <InfoRow label="Entity ID" value={entry.entity_id} />
              ) : null}
              <InfoRow
                label="Actor"
                value={
                  entry.actor_name ||
                  entry.actor_email ||
                  entry.actor_user_id ||
                  "System"
                }
              />
              <InfoRow label="Time" value={formatDate(entry.created_at)} />

              <View style={styles.actions}>
                <Pressable
                  onPress={() => toggleChanges(entry.id)}
                  accessibilityRole="button"
                >
                  <Text style={styles.link}>
                    {changesExpanded ? "Hide changes" : "Show changes"}
                  </Text>
                </Pressable>

                {entry.entity_id ? (
                  <Pressable
                    onPress={() => void showEntityHistory(entry)}
                    accessibilityRole="button"
                  >
                    <Text style={styles.link}>
                      {selectedEntity === key ? "Hide entity history" : "Entity history"}
                    </Text>
                  </Pressable>
                ) : null}
              </View>

              {changesExpanded ? (
                <Text selectable style={styles.json}>
                  {JSON.stringify(entry.changes, null, 2)}
                </Text>
              ) : null}

              {selectedEntity === key ? (
                <View style={styles.history}>
                  <Text style={styles.sectionTitle}>Entity history</Text>
                  {loadingEntity ? (
                    <ActivityIndicator color="#183153" />
                  ) : (
                    entityHistory.map((historyEntry) => (
                      <View key={historyEntry.id} style={styles.historyEntry}>
                        <Text style={styles.body}>{historyEntry.summary}</Text>
                        <Text style={styles.muted}>
                          {humanize(historyEntry.action)} ·{" "}
                          {formatDate(historyEntry.created_at)}
                        </Text>
                      </View>
                    ))
                  )}
                </View>
              ) : null}
            </View>
          );
        })
      )}

      {hasMore ? (
        <ActionButton
          label={loadingMore ? "Loading…" : "Load more"}
          disabled={loadingMore}
          onPress={() => void loadMore()}
        />
      ) : null}
    </ScrollView>
  );
}

function Field({
  label,
  value,
  onChangeText,
  placeholder,
  autoCapitalize,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder: string;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
}) {
  return (
    <View>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        autoCapitalize={autoCapitalize ?? "none"}
      />
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.muted}>{label}</Text>
      <Text selectable style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function ActionButton({
  label,
  onPress,
  secondary = false,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  secondary?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      style={[
        styles.button,
        secondary && styles.secondaryButton,
        disabled && styles.disabled,
      ]}
    >
      <Text
        style={[
          styles.buttonText,
          secondary && styles.secondaryButtonText,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, paddingTop: 30, paddingBottom: 40, backgroundColor: "#F4F6F8" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8" },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 10 },
  eyebrow: { color: "#8A7B67", fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
  title: { color: "#17212F", fontSize: 25, fontWeight: "800", marginTop: 5 },
  sectionTitle: { color: "#17212F", fontSize: 16, fontWeight: "700", marginBottom: 6 },
  card: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E4E7EC", borderRadius: 14, padding: 16, marginBottom: 12 },
  label: { color: "#344054", fontSize: 12, fontWeight: "700", marginTop: 10, marginBottom: 5 },
  input: { minHeight: 44, borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 9, paddingHorizontal: 10, color: "#17212F", backgroundColor: "#FFFFFF" },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 8 },
  infoValue: { flex: 1, color: "#17212F", textAlign: "right", fontWeight: "600" },
  muted: { color: "#667085", lineHeight: 19 },
  body: { color: "#344054", lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700" },
  error: { color: "#B42318", lineHeight: 20, marginBottom: 8 },
  actions: { flexDirection: "row", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginTop: 10 },
  json: { color: "#344054", backgroundColor: "#F4F6F8", padding: 10, borderRadius: 8, fontSize: 12, lineHeight: 18, marginTop: 8 },
  latestRow: { borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 10 },
  idText: { color: "#667085", fontSize: 11, marginTop: 5 },
  history: { borderTopWidth: 1, borderTopColor: "#D0D5DD", marginTop: 12, paddingTop: 10 },
  historyEntry: { borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 9 },
  button: { minHeight: 44, backgroundColor: "#183153", borderRadius: 10, alignItems: "center", justifyContent: "center", padding: 12, marginTop: 10 },
  buttonText: { color: "#FFFFFF", fontWeight: "700" },
  secondaryButton: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D0D5DD" },
  secondaryButtonText: { color: "#183153" },
  disabled: { opacity: 0.55 },
});
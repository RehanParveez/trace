import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../api/client";
import {getLatestAuditByEntityType, listAuditLogForEntity, listAuditLogs,
} from "../api/audit";
import type {AuditAction, AuditEntityType, AuditLogEntry, AuthUser, EntityActivitySummary,
} from "../api/types";
import LanguageSwitcher from "./LanguageSwitcher";

const PAGE_SIZE = 10;

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

const C = {
  background: "#F3EEE4",
  surface: "#FFFEFB",
  surfaceMuted: "#F7F1E7",
  navy: "#080D18",
  text: "#17212F",
  secondary: "#5C5347",
  muted: "#82796C",
  border: "#E5DCCB",
  gold: "#D9A441",
  red: "#A33A32",
  redBg: "#F9E9E5",
};

function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return (
    !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
  );
}

function dateBound(value: string, endOfDay: boolean): string | undefined {
  if (!value) return undefined;
  const time = endOfDay ? "23:59:59.999" : "00:00:00.000";
  return new Date(`${value}T${time}Z`).toISOString();
}

function formatDate(value: string, locale?: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(locale);
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
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = i18n.resolvedLanguage || i18n.language;

  const [permissionChecked, setPermissionChecked] = useState(false);
  const [canRead, setCanRead] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [pageNumber, setPageNumber] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [loading, setLoading] = useState(true);
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

  function readableEntityType(type: string): string {
    return t(`audit.entityType.${type.toLowerCase()}`, {
      defaultValue: humanize(type),
    });
  }

  function readableAction(action: string): string {
    return t(`audit.action.${action.toLowerCase()}`, {
      defaultValue: humanize(action),
    });
  }

  async function fetchPage(page: number) {
    const [rows, nextRows] = await Promise.all([
      listAuditLogs({
        ...filters,
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
      listAuditLogs({
        ...filters,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    ]);

    return {
      rows,
      hasNext: nextRows.length > 0,
    };
  }

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      setPageNumber(1);
      setHasNextPage(false);

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

        const result = await fetchPage(1);
        if (!active) return;

        setEntries(result.rows);
        setPageNumber(1);
        setHasNextPage(result.hasNext);
        setSelectedEntity(null);
        setEntityHistory([]);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : t("audit.loadFailure"),
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
  }, [filters, attempt, t]);

  function applyFilters() {
    setError("");

    const entityType = entityTypeInput.trim();
    const action = actionInput.trim();
    const entityId = entityIdInput.trim();
    const actorId = actorIdInput.trim();
    const from = fromInput.trim();
    const to = toInput.trim();

    if (entityType && !ENTITY_TYPES.includes(entityType as AuditEntityType)) {
      setError(t("audit.invalidEntityType"));
      return;
    }
    if (action && !ACTIONS.includes(action as AuditAction)) {
      setError(t("audit.invalidAction"));
      return;
    }
    if (from && !validDate(from)) {
      setError(t("audit.invalidStartDate"));
      return;
    }
    if (to && !validDate(to)) {
      setError(t("audit.invalidEndDate"));
      return;
    }
    if (from && to && from > to) {
      setError(t("audit.startAfterEnd"));
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

  async function goToPage(targetPage: number) {
    if (targetPage < 1 || targetPage === pageNumber || loading) return;

    setLoading(true);
    setError("");

    try {
      const result = await fetchPage(targetPage);
      setEntries(result.rows);
      setPageNumber(targetPage);
      setHasNextPage(result.hasNext);
      setSelectedEntity(null);
      setEntityHistory([]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("audit.loadFailure"),
      );
    } finally {
      setLoading(false);
    }
  }

  async function showLatestByType() {
    if (!canRead) return;
    if (!filters.entity_type) {
      setError(t("audit.selectEntityFirst"));
      return;
    }

    setLoadingLatest(true);
    setError("");

    try {
      const rows = await getLatestAuditByEntityType(filters.entity_type);
      setLatestRows(rows);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("audit.latestFailure"),
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
        err instanceof Error ? err.message : t("audit.entityHistoryFailure"),
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

  const lastAvailablePage = pageNumber + (hasNextPage ? 1 : 0);
  const firstVisiblePage = Math.max(
    1,
    Math.min(pageNumber - 2, lastAvailablePage - 4),
  );
  const visiblePages = Array.from(
    {
      length: Math.min(5, lastAvailablePage - firstVisiblePage + 1),
    },
    (_, index) => firstVisiblePage + index,
  );

  if (loading || !permissionChecked) {
    return (
      <View style={styles.page}>
        <View style={[styles.header, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("audit.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>

        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("audit.loading")}
          </Text>
        </View>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <View style={[styles.header, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("audit.pageTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {t("audit.accessDenied")}
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
    >
      <View style={[styles.header, isUrdu && styles.rtlRow]}>
        <View style={styles.headerContent}>
          <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
            {t("audit.eyebrow")}
          </Text>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("audit.pageTitle")}
          </Text>
        </View>
        <LanguageSwitcher />
      </View>

      {error ? (
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error}
        </Text>
      ) : null}

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
          {t("audit.filters")}
        </Text>

        <Field
          label={t("audit.entityTypeLabel", {
            values: ENTITY_TYPES.join(", "),
          })}
          value={entityTypeInput}
          onChangeText={setEntityTypeInput}
          placeholder={t("audit.blankForAll")}
          autoCapitalize="characters"
          isUrdu={isUrdu}
        />
        <Field
          label={t("audit.actionLabel", {
            values: ACTIONS.join(", "),
          })}
          value={actionInput}
          onChangeText={setActionInput}
          placeholder={t("audit.blankForAll")}
          autoCapitalize="characters"
          isUrdu={isUrdu}
        />
        <Field
          label={t("audit.entityIdOptional")}
          value={entityIdInput}
          onChangeText={setEntityIdInput}
          placeholder={t("audit.uuidPlaceholder")}
          autoCapitalize="none"
          isUrdu={isUrdu}
        />
        <Field
          label={t("audit.actorIdOptional")}
          value={actorIdInput}
          onChangeText={setActorIdInput}
          placeholder={t("audit.uuidPlaceholder")}
          autoCapitalize="none"
          isUrdu={isUrdu}
        />
        <Field
          label={t("audit.createdFrom")}
          value={fromInput}
          onChangeText={setFromInput}
          placeholder={t("audit.datePlaceholder")}
          autoCapitalize="none"
          isUrdu={isUrdu}
        />
        <Field
          label={t("audit.createdTo")}
          value={toInput}
          onChangeText={setToInput}
          placeholder={t("audit.datePlaceholder")}
          autoCapitalize="none"
          isUrdu={isUrdu}
        />

        <ActionButton
          label={t("audit.applyFilters")}
          onPress={applyFilters}
        />
        <ActionButton
          label={t("audit.clearFilters")}
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
          label={
            loadingLatest
              ? t("audit.loadingLatest")
              : t("audit.latestByEntityType")
          }
          secondary
          disabled={loadingLatest}
          onPress={() => void showLatestByType()}
        />
      </View>

      {latestRows.length > 0 ? (
        <View style={styles.card}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("audit.latestActivityByEntity")}
          </Text>
          {latestRows.map((item) => (
            <View key={item.entity_id} style={styles.latestRow}>
              <Text style={[styles.body, isUrdu && styles.rtlText]}>
                {item.last_summary}
              </Text>
              <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                {readableAction(item.last_action)} ·{" "}
                {formatDate(item.last_created_at, locale)}
              </Text>
              <Text selectable style={styles.idText}>
                {item.entity_id}
              </Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={[styles.header, isUrdu && styles.rtlRow]}>
        <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
          {t("audit.entries")}
        </Text>
        <Text style={styles.muted}>
          {t("audit.loadedCount", { count: entries.length })}
        </Text>
      </View>

      {entries.length === 0 ? (
        <View style={styles.card}>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("audit.noMatchingEntries")}
          </Text>
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
              <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
                {entry.summary}
              </Text>
              <InfoRow
                label={t("audit.action")}
                value={readableAction(entry.action)}
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("audit.entity")}
                value={readableEntityType(entry.entity_type)}
                isUrdu={isUrdu}
              />
              {entry.entity_id ? (
                <InfoRow
                  label={t("audit.entityId")}
                  value={entry.entity_id}
                  isUrdu={isUrdu}
                />
              ) : null}
              <InfoRow
                label={t("audit.actor")}
                value={
                  entry.actor_name ||
                  entry.actor_email ||
                  entry.actor_user_id ||
                  t("audit.systemActor")
                }
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("audit.time")}
                value={formatDate(entry.created_at, locale)}
                isUrdu={isUrdu}
              />

              <View style={[styles.actions, isUrdu && styles.rtlRow]}>
                <Pressable
                  onPress={() => toggleChanges(entry.id)}
                  accessibilityRole="button"
                >
                  <Text style={styles.link}>
                    {changesExpanded
                      ? t("audit.hideChanges")
                      : t("audit.showChanges")}
                  </Text>
                </Pressable>

                {entry.entity_id ? (
                  <Pressable
                    onPress={() => void showEntityHistory(entry)}
                    accessibilityRole="button"
                  >
                    <Text style={styles.link}>
                      {selectedEntity === key
                        ? t("audit.hideEntityHistory")
                        : t("audit.entityHistory")}
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
                  <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
                    {t("audit.entityHistory")}
                  </Text>
                  {loadingEntity ? (
                    <ActivityIndicator color={C.navy} />
                  ) : (
                    entityHistory.map((historyEntry) => (
                      <View key={historyEntry.id} style={styles.historyEntry}>
                        <Text style={[styles.body, isUrdu && styles.rtlText]}>
                          {historyEntry.summary}
                        </Text>
                        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                          {readableAction(historyEntry.action)} ·{" "}
                          {formatDate(historyEntry.created_at, locale)}
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

      {entries.length > 0 ? (
        <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
          <Pressable
            style={[
              styles.pageNavButton,
              pageNumber === 1 && styles.disabled,
            ]}
            disabled={pageNumber === 1 || loading}
            onPress={() => void goToPage(pageNumber - 1)}
            accessibilityRole="button"
          >
            <Text style={styles.pageNavText}>{t("audit.previousPage")}</Text>
          </Pressable>

          <View style={[styles.pageNumbers, isUrdu && styles.rtlRow]}>
            {visiblePages.map((page) => (
              <Pressable
                key={page}
                style={[
                  styles.pageNumber,
                  page === pageNumber && styles.pageNumberSelected,
                ]}
                disabled={loading || page === pageNumber}
                onPress={() => void goToPage(page)}
                accessibilityRole="button"
                accessibilityState={{ selected: page === pageNumber }}
              >
                <Text
                  style={[
                    styles.pageNumberText,
                    page === pageNumber && styles.pageNumberTextSelected,
                  ]}
                >
                  {page}
                </Text>
              </Pressable>
            ))}
          </View>

          <Pressable
            style={[
              styles.pageNavButton,
              !hasNextPage && styles.disabled,
            ]}
            disabled={!hasNextPage || loading}
            onPress={() => void goToPage(pageNumber + 1)}
            accessibilityRole="button"
          >
            <Text style={styles.pageNavText}>{t("audit.nextPage")}</Text>
          </Pressable>
        </View>
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
  isUrdu,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder: string;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  isUrdu: boolean;
}) {
  return (
    <View>
      <Text style={[styles.label, isUrdu && styles.rtlText]}>{label}</Text>
      <TextInput
        style={[styles.input, isUrdu && styles.rtlText]}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={C.muted}
        autoCapitalize={autoCapitalize ?? "none"}
        textAlign={isUrdu ? "right" : "left"}
      />
    </View>
  );
}

function InfoRow({
  label,
  value,
  isUrdu,
}: {
  label: string;
  value: string;
  isUrdu: boolean;
}) {
  return (
    <View style={[styles.infoRow, isUrdu && styles.rtlRow]}>
      <Text style={[styles.muted, isUrdu && styles.rtlText]}>{label}</Text>
      <Text
        selectable
        style={[styles.infoValue, isUrdu && styles.rtlText]}
      >
        {value}
      </Text>
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
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: C.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 18 },
  headerContent: { flex: 1 },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 27, fontWeight: "800", marginTop: 5, letterSpacing: -0.4 },
  sectionTitle: { color: C.text, fontSize: 17, fontWeight: "800", marginBottom: 8 },
  card: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, borderRadius: 15, padding: 16, marginBottom: 12 },
  label: { color: C.secondary, fontSize: 12, fontWeight: "700", marginTop: 13, marginBottom: 7 },
  input: { minHeight: 46, borderWidth: 1, borderColor: C.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, color: C.text, backgroundColor: C.surface, fontSize: 14 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 9 },
  infoValue: { flex: 1, color: C.text, textAlign: "right", fontWeight: "700", fontSize: 13 },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19 },
  body: { color: C.secondary, lineHeight: 20 },
  link: { color: C.navy, fontSize: 13, fontWeight: "800" },
  error: { color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19, marginBottom: 12 },
  actions: { flexDirection: "row", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: C.border },
  json: { color: C.text, backgroundColor: C.surfaceMuted, borderWidth: 1, borderColor: C.border, padding: 10, borderRadius: 9, fontSize: 12, lineHeight: 18, marginTop: 10 },
  latestRow: { borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 10 },
  idText: { color: C.muted, fontSize: 11, marginTop: 5 },
  history: { borderTopWidth: 1, borderTopColor: C.border, marginTop: 12, paddingTop: 12 },
  historyEntry: { borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 9 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 4, padding: 10, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13 },
  pageNavButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: C.surfaceMuted },
  pageNavText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pageNumbers: { flexDirection: "row", alignItems: "center", gap: 5 },
  pageNumber: { minWidth: 36, height: 36, alignItems: "center", justifyContent: "center", borderRadius: 9, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  pageNumberSelected: { backgroundColor: C.navy, borderColor: C.navy },
  pageNumberText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  pageNumberTextSelected: { color: C.surface },
  button: { minHeight: 46, backgroundColor: C.navy, borderRadius: 11, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 12, marginTop: 10 },
  buttonText: { color: C.surface, fontSize: 13, fontWeight: "800", textAlign: "center" },
  secondaryButton: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  secondaryButtonText: { color: C.navy },
  disabled: { opacity: 0.45 },
});
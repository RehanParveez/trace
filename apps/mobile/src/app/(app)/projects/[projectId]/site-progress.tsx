import { useCallback, useState } from "react";
import {ActivityIndicator, Alert, FlatList, Modal, Platform, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { useFocusEffect, useLocalSearchParams, Stack } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { siteProgressApi } from "../../../../api/siteProgress";
import type {AuthUser, SiteLog, SiteLogCreatePayload, SiteLogUpdatePayload,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";

const PAGE_SIZE = 5;

type FormState = {
  log_date: string;
  workforce_count: string;
  weather: string;
  blockers: string;
  notes: string;
};

function createEmptyForm(): FormState {
  return {
    log_date: new Date().toISOString().slice(0, 10),
    workforce_count: "",
    weather: "",
    blockers: "",
    notes: "",
  };
}

function hasPermission(user: AuthUser | null, keys: string[]) {
  const permissions = user?.role?.permissions ?? [];
  return permissions.some((permission) => keys.includes(permission.key));
}

export default function SiteProgressScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  const params = useLocalSearchParams<{ projectId?: string | string[] }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [logs, setLogs] = useState<SiteLog[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingLog, setEditingLog] = useState<SiteLog | null>(null);
  const [form, setForm] = useState<FormState>(createEmptyForm());
  const [saving, setSaving] = useState(false);

  const canRead = hasPermission(user, [
    "site_progress:read",
    "site_progress.read",
    "site_log:read",
    "site_log.read",
  ]);
  const canCreate = hasPermission(user, [
    "site_progress:create",
    "site_progress.create",
    "site_log:create",
    "site_log.create",
  ]);
  const canManage = hasPermission(user, [
    "site_progress:manage",
    "site_progress.manage",
    "site_log:manage",
    "site_log.manage",
  ]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;

      async function restore() {
        try {
          const restoredUser = await restoreSession();
          if (!cancelled) setUser(restoredUser);
        } catch {
          if (!cancelled) setUser(null);
        } finally {
          if (!cancelled) setAuthLoading(false);
        }
      }

      void restore();

      return () => {
        cancelled = true;
      };
    }, []),
  );

  const loadLogs = useCallback(
    async (isRefresh = false) => {
      if (!projectId || !canRead) {
        setLoading(false);
        setRefreshing(false);
        return;
      }

      try {
        if (isRefresh) setRefreshing(true);
        else setLoading(true);
        setError(null);

        const data = await siteProgressApi.listLogs(projectId);
        setLogs(data);
        setPage(1);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : t("siteProgress.loadFailure");

        setError(message);

        if (message.toLowerCase().includes("project not found")) {
          Alert.alert(
            t("siteProgress.projectNotFoundTitle"),
            t("siteProgress.projectNotFoundMessage"),
          );
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, canRead, t],
  );

  useFocusEffect(
    useCallback(() => {
      if (!authLoading && canRead) void loadLogs();
    }, [authLoading, canRead, loadLogs]),
  );

  const openCreate = () => {
    setEditingLog(null);
    setForm(createEmptyForm());
    setError(null);
    setModalVisible(true);
  };

  const openEdit = (log: SiteLog) => {
    setEditingLog(log);
    setForm({
      log_date: log.log_date,
      workforce_count:
        log.workforce_count != null ? String(log.workforce_count) : "",
      weather: log.weather ?? "",
      blockers: log.blockers ?? "",
      notes: log.notes ?? "",
    });
    setError(null);
    setModalVisible(true);
  };

  const validateForm = (): string | null => {
    if (!form.log_date || !/^\d{4}-\d{2}-\d{2}$/.test(form.log_date)) {
      return t("siteProgress.validation.logDate");
    }

    if (form.workforce_count !== "") {
      const count = Number(form.workforce_count);
      if (!Number.isInteger(count) || count < 0) {
        return t("siteProgress.validation.workforceCount");
      }
    }

    return null;
  };

  const handleSave = async () => {
    const validationError = validateForm();

    if (validationError) {
      Alert.alert(t("siteProgress.validation.title"), validationError);
      return;
    }

    if (!projectId) {
      Alert.alert(
        t("siteProgress.errorTitle"),
        t("siteProgress.projectNotFoundMessage"),
      );
      return;
    }

    setSaving(true);

    try {
      const payloadBase = {
        log_date: form.log_date,
        workforce_count:
          form.workforce_count === "" ? null : Number(form.workforce_count),
        weather: form.weather.trim() || null,
        blockers: form.blockers.trim() || null,
        notes: form.notes.trim() || null,
      };

      if (editingLog) {
        const updatePayload: SiteLogUpdatePayload = payloadBase;
        await siteProgressApi.updateLog(editingLog.id, updatePayload);
      } else {
        const createPayload: SiteLogCreatePayload = {
          project_id: projectId,
          ...payloadBase,
        };
        await siteProgressApi.createLog(createPayload);
      }

      setModalVisible(false);
      await loadLogs(true);
    } catch (err) {
      Alert.alert(
        t("siteProgress.errorTitle"),
        err instanceof Error
          ? err.message
          : t("siteProgress.saveFailure"),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (log: SiteLog) => {
    Alert.alert(
      t("siteProgress.deleteConfirmTitle"),
      t("siteProgress.deleteConfirmMessage", { date: log.log_date }),
      [
        { text: t("siteProgress.cancel"), style: "cancel" },
        {
          text: t("siteProgress.delete"),
          style: "destructive",
          onPress: async () => {
            try {
              await siteProgressApi.deleteLog(log.id);
              await loadLogs(true);
            } catch (err) {
              Alert.alert(
                t("siteProgress.errorTitle"),
                err instanceof Error
                  ? err.message
                  : t("siteProgress.deleteFailure"),
              );
            }
          },
        },
      ],
    );
  };

  if (authLoading) {
    return (
      <View style={styles.centered}>
        <View style={styles.headerRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("siteProgress.loading")}
        </Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <>
        <Stack.Screen options={{ title: t("siteProgress.title") }} />
        <View style={styles.centered}>
          <View style={styles.headerRow}>
            <LanguageSwitcher />
          </View>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("siteProgress.title")}
          </Text>
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {t("siteProgress.accessDenied")}
          </Text>
        </View>
      </>
    );
  }

  const pages = Math.max(1, Math.ceil(logs.length / PAGE_SIZE));
  const visibleLogs = logs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <>
      <Stack.Screen options={{ title: t("siteProgress.title") }} />

      <View style={styles.screen}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, styles.headerTitle, isUrdu && styles.rtlText]}>
            {t("siteProgress.title")}
          </Text>
          <View style={styles.headerActions}>
            {canCreate ? (
              <Pressable
                onPress={openCreate}
                style={styles.headerButton}
                accessibilityRole="button"
              >
                <Text style={styles.headerButtonText}>
                  {t("siteProgress.new")}
                </Text>
              </Pressable>
            ) : null}
            <LanguageSwitcher />
          </View>
        </View>

        {loading ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={COLORS.navy} />
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("siteProgress.loading")}
            </Text>
          </View>
        ) : error ? (
          <View style={styles.errorArea}>
            <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
            <Pressable
              onPress={() => void loadLogs()}
              style={styles.button}
              accessibilityRole="button"
            >
              <Text style={styles.buttonText}>{t("siteProgress.retry")}</Text>
            </Pressable>
          </View>
        ) : (
          <FlatList
            data={visibleLogs}
            keyExtractor={(item) => item.id}
            contentContainerStyle={
              logs.length === 0 ? styles.emptyContainer : styles.list
            }
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={() => void loadLogs(true)}
                tintColor={COLORS.navy}
              />
            }
            ListEmptyComponent={
              <Text style={[styles.emptyText, isUrdu && styles.rtlText]}>
                {t("siteProgress.empty")}
              </Text>
            }
            ListFooterComponent={
              logs.length > PAGE_SIZE ? (
                <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
                  <Pressable
                    style={[
                      styles.pageButton,
                      page <= 1 && styles.disabled,
                    ]}
                    onPress={() => setPage((current) => Math.max(1, current - 1))}
                    disabled={page <= 1}
                    accessibilityRole="button"
                  >
                    <Text style={[styles.pageButtonText, isUrdu && styles.rtlText]}>
                      {t("siteProgress.previous")}
                    </Text>
                  </Pressable>
                  <Text style={[styles.pageText, isUrdu && styles.rtlText]}>
                    {t("siteProgress.pageOf", { page, pages })}
                  </Text>
                  <Pressable
                    style={[
                      styles.pageButton,
                      page >= pages && styles.disabled,
                    ]}
                    onPress={() =>
                      setPage((current) => Math.min(pages, current + 1))
                    }
                    disabled={page >= pages}
                    accessibilityRole="button"
                  >
                    <Text style={[styles.pageButtonText, isUrdu && styles.rtlText]}>
                      {t("siteProgress.next")}
                    </Text>
                  </Pressable>
                </View>
              ) : null
            }
            renderItem={({ item }) => (
              <View style={styles.card}>
                <View style={[styles.cardHeader, isUrdu && styles.rtlRow]}>
                  <Text style={[styles.date, isUrdu && styles.rtlText]}>
                    {item.log_date}
                  </Text>

                  {canManage ? (
                    <View style={[styles.actions, isUrdu && styles.rtlRow]}>
                      <Pressable
                        onPress={() => openEdit(item)}
                        accessibilityRole="button"
                      >
                        <Text style={[styles.actionText, isUrdu && styles.rtlText]}>
                          {t("siteProgress.edit")}
                        </Text>
                      </Pressable>
                      <Pressable
                        onPress={() => handleDelete(item)}
                        accessibilityRole="button"
                      >
                        <Text
                          style={[
                            styles.actionText,
                            styles.deleteText,
                            isUrdu && styles.rtlText,
                          ]}
                        >
                          {t("siteProgress.delete")}
                        </Text>
                      </Pressable>
                    </View>
                  ) : null}
                </View>

                {item.workforce_count != null ? (
                  <Text style={[styles.meta, isUrdu && styles.rtlText]}>
                    {t("siteProgress.workforce", {
                      count: item.workforce_count,
                    })}
                  </Text>
                ) : null}

                {item.weather ? (
                  <Text style={[styles.meta, isUrdu && styles.rtlText]}>
                    {t("siteProgress.weatherValue", {
                      weather: item.weather,
                    })}
                  </Text>
                ) : null}

                {item.blockers ? (
                  <Text style={[styles.blockers, isUrdu && styles.rtlText]}>
                    {t("siteProgress.blockersValue", {
                      blockers: item.blockers,
                    })}
                  </Text>
                ) : null}

                {item.notes ? (
                  <Text style={[styles.notes, isUrdu && styles.rtlText]}>
                    {item.notes}
                  </Text>
                ) : null}
              </View>
            )}
          />
        )}
      </View>

      <Modal
        visible={modalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setModalVisible(false)}
      >
        <ScrollView
          contentContainerStyle={styles.modalContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={[styles.modalHeader, isUrdu && styles.rtlRow]}>
            <Text style={[styles.modalTitle, isUrdu && styles.rtlText]}>
              {editingLog
                ? t("siteProgress.editLog")
                : t("siteProgress.newLog")}
            </Text>
            <LanguageSwitcher />
          </View>

          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("siteProgress.logDate")}
          </Text>
          <TextInput
            style={[styles.input, isUrdu && styles.rtlText]}
            value={form.log_date}
            onChangeText={(value) =>
              setForm((current) => ({ ...current, log_date: value }))
            }
            placeholder="YYYY-MM-DD"
            autoCapitalize="none"
            textAlign={isUrdu ? "right" : "left"}
          />

          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("siteProgress.workforceCount")}
          </Text>
          <TextInput
            style={[styles.input, isUrdu && styles.rtlText]}
            value={form.workforce_count}
            onChangeText={(value) =>
              setForm((current) => ({ ...current, workforce_count: value }))
            }
            placeholder={t("siteProgress.workforcePlaceholder")}
            keyboardType="number-pad"
            textAlign={isUrdu ? "right" : "left"}
          />

          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("siteProgress.weather")}
          </Text>
          <TextInput
            style={[styles.input, isUrdu && styles.rtlText]}
            value={form.weather}
            onChangeText={(value) =>
              setForm((current) => ({ ...current, weather: value }))
            }
            placeholder={t("siteProgress.weatherPlaceholder")}
            maxLength={255}
            textAlign={isUrdu ? "right" : "left"}
          />

          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("siteProgress.blockers")}
          </Text>
          <TextInput
            style={[styles.input, styles.multiline, isUrdu && styles.rtlText]}
            value={form.blockers}
            onChangeText={(value) =>
              setForm((current) => ({ ...current, blockers: value }))
            }
            placeholder={t("siteProgress.blockersPlaceholder")}
            multiline
            numberOfLines={3}
            textAlign={isUrdu ? "right" : "left"}
            textAlignVertical="top"
          />

          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("siteProgress.notes")}
          </Text>
          <TextInput
            style={[styles.input, styles.multiline, isUrdu && styles.rtlText]}
            value={form.notes}
            onChangeText={(value) =>
              setForm((current) => ({ ...current, notes: value }))
            }
            placeholder={t("siteProgress.notesPlaceholder")}
            multiline
            numberOfLines={4}
            textAlign={isUrdu ? "right" : "left"}
            textAlignVertical="top"
          />

          <View style={[styles.modalActions, isUrdu && styles.rtlRow]}>
            <Pressable
              style={[styles.button, styles.secondaryButton]}
              onPress={() => setModalVisible(false)}
              disabled={saving}
            >
              <Text style={styles.secondaryButtonText}>
                {t("siteProgress.cancel")}
              </Text>
            </Pressable>

            <Pressable
              style={[styles.button, saving && styles.disabled]}
              onPress={() => void handleSave()}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color={COLORS.surface} />
              ) : (
                <Text style={styles.buttonText}>
                  {editingLog
                    ? t("siteProgress.update")
                    : t("siteProgress.create")}
                </Text>
              )}
            </Pressable>
          </View>
        </ScrollView>
      </Modal>
    </>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#F7F3EC",
  navy: "#080D18",
  text: "#171C26",
  secondary: "#5C5347",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
  red: "#A63A32",
  redBackground: "#FBEAE7",
  orange: "#9B641A",
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background, paddingHorizontal: 16, paddingTop: 14 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24, gap: 12, backgroundColor: COLORS.background },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 12 },
  headerActions: { flexDirection: "row", alignItems: "center", gap: 8 },
  headerTitle: { flex: 1, marginBottom: 0 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 24, fontWeight: "800" },
  headerButton: { minHeight: 38, paddingHorizontal: 12, justifyContent: "center", borderRadius: 10, backgroundColor: COLORS.navy },
  headerButtonText: { color: COLORS.surface, fontWeight: "800", fontSize: 13 },
  list: { paddingBottom: 32 },
  emptyContainer: { flexGrow: 1, justifyContent: "center", alignItems: "center", padding: 20 },
  emptyText: { color: COLORS.muted, fontSize: 14, textAlign: "center", lineHeight: 21 },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginBottom: 12 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 7 },
  date: { fontSize: 15, fontWeight: "800", color: COLORS.text },
  actions: { flexDirection: "row", gap: 12 },
  actionText: { color: COLORS.navy, fontWeight: "800", fontSize: 12 },
  deleteText: { color: COLORS.red },
  meta: { fontSize: 13, color: COLORS.secondary, marginTop: 4, lineHeight: 19 },
  blockers: { fontSize: 13, color: COLORS.orange, marginTop: 6, lineHeight: 19 },
  notes: { fontSize: 13, color: COLORS.muted, marginTop: 6, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginVertical: 8, textAlign: "center", lineHeight: 19, fontSize: 13 },
  errorArea: { flex: 1, justifyContent: "center", padding: 16 },
  loading: { color: COLORS.muted, fontSize: 13 },
  button: { minHeight: 44, paddingHorizontal: 16, paddingVertical: 11, backgroundColor: COLORS.navy, borderRadius: 10, alignItems: "center", justifyContent: "center", marginTop: 8 },
  buttonText: { color: COLORS.surface, fontWeight: "800", fontSize: 13 },
  disabled: { opacity: 0.5 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, paddingVertical: 12 },
  pageButton: { minHeight: 40, paddingHorizontal: 12, justifyContent: "center", backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10 },
  pageButtonText: { color: COLORS.navy, fontSize: 12, fontWeight: "800" },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700" },
  modalContent: { flexGrow: 1, padding: 20, paddingBottom: 36, backgroundColor: COLORS.background },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 14 },
  modalTitle: { flex: 1, color: COLORS.text, fontSize: 21, fontWeight: "800" },
  label: { fontSize: 12, fontWeight: "700", color: COLORS.secondary, marginBottom: 5, marginTop: 12 },
  input: { minHeight: 45, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, backgroundColor: COLORS.surface, color: COLORS.text },
  multiline: { minHeight: 82, textAlignVertical: "top" },
  modalActions: { flexDirection: "row", justifyContent: "flex-end", gap: 10, marginTop: 24 },
  secondaryButton: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  secondaryButtonText: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
  muted: {color: COLORS.muted, fontSize: 13, lineHeight: 20,},
});
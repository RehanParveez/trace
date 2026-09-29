import React, { useCallback, useEffect, useState } from "react";
import {View, Text, FlatList, TouchableOpacity, TextInput, ActivityIndicator, Alert, StyleSheet, Modal, ScrollView, Platform,
} from "react-native";
import { useLocalSearchParams, Stack } from "expo-router";
import { siteProgressApi } from "../../../../api/siteProgress";
import type {SiteLog, SiteLogCreatePayload, SiteLogUpdatePayload,
} from "../../../../api/types";

const canRead = true;
const canCreate = true;
const canManage = true;

type FormState = {
  log_date: string;
  workforce_count: string;
  weather: string;
  blockers: string;
  notes: string;
};

const emptyForm: FormState = {
  log_date: new Date().toISOString().slice(0, 10),
  workforce_count: "",
  weather: "",
  blockers: "",
  notes: "",
};

export default function SiteProgressScreen() {
  const { projectId } = useLocalSearchParams<{ projectId: string }>();

  const [logs, setLogs] = useState<SiteLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingLog, setEditingLog] = useState<SiteLog | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);

  const loadLogs = useCallback(
    async (isRefresh = false) => {
      if (!projectId || !canRead) return;

      try {
        if (isRefresh) setRefreshing(true);
        else setLoading(true);
        setError(null);

        const data = await siteProgressApi.listLogs(projectId);
        setLogs(data);
      } catch (err: any) {
        const msg = err?.message ?? "Failed to load site logs";
        setError(msg);

        if (msg.toLowerCase().includes("project not found")) {
          Alert.alert(
            "Project not found",
            "This project does not exist or is outside your organization.",
          );
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const openCreate = () => {
    setEditingLog(null);
    setForm(emptyForm);
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
    setModalVisible(true);
  };

  const validateForm = (): string | null => {
    if (!form.log_date || !/^\d{4}-\d{2}-\d{2}$/.test(form.log_date)) {
      return "Log date is required (YYYY-MM-DD).";
    }
    if (form.workforce_count !== "") {
      const n = Number(form.workforce_count);
      if (isNaN(n) || n < 0 || !Number.isInteger(n)) {
        return "Workforce count must be a non-negative integer.";
      }
    }
    return null;
  };

  const handleSave = async () => {
    const validationError = validateForm();
    if (validationError) {
      Alert.alert("Validation", validationError);
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
          project_id: projectId!,
          ...payloadBase,
        };
        await siteProgressApi.createLog(createPayload);
      }

      setModalVisible(false);
      await loadLogs(true);
    } catch (err: any) {
      Alert.alert("Error", err?.message ?? "Failed to save log");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (log: SiteLog) => {
    Alert.alert(
      "Delete Site Log",
      `Delete log for ${log.log_date}? This cannot be undone.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              await siteProgressApi.deleteLog(log.id);
              await loadLogs(true);
            } catch (err: any) {
              Alert.alert("Error", err?.message ?? "Failed to delete log");
            }
          },
        },
      ],
    );
  };

  if (!canRead) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>
          You do not have permission to view site logs.
        </Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen
        options={{
          title: "Site Progress",
          headerRight: canCreate
            ? () => (
                <TouchableOpacity
                  onPress={openCreate}
                  style={{ marginRight: 12 }}
                >
                  <Text style={styles.headerBtn}>+ New</Text>
                </TouchableOpacity>
              )
            : undefined,
        }}
      />

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" />
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity
            onPress={() => loadLogs()}
            style={styles.retryBtn}
          >
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={logs}
          keyExtractor={(item) => item.id}
          contentContainerStyle={
            logs.length === 0 ? styles.emptyContainer : styles.list
          }
          refreshing={refreshing}
          onRefresh={() => loadLogs(true)}
          ListEmptyComponent={
            <Text style={styles.emptyText}>
              No site logs yet for this project.
            </Text>
          }
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Text style={styles.date}>{item.log_date}</Text>
                {canManage && (
                  <View style={styles.actions}>
                    <TouchableOpacity onPress={() => openEdit(item)}>
                      <Text style={styles.actionText}>Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => handleDelete(item)}>
                      <Text style={[styles.actionText, styles.deleteText]}>
                        Delete
                      </Text>
                    </TouchableOpacity>
                  </View>
                )}
              </View>

              {item.workforce_count != null && (
                <Text style={styles.meta}>
                  Workforce: {item.workforce_count}
                </Text>
              )}
              {item.weather ? (
                <Text style={styles.meta}>Weather: {item.weather}</Text>
              ) : null}
              {item.blockers ? (
                <Text style={styles.blockers}>Blockers: {item.blockers}</Text>
              ) : null}
              {item.notes ? (
                <Text style={styles.notes}>{item.notes}</Text>
              ) : null}
            </View>
          )}
        />
      )}

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
          <Text style={styles.modalTitle}>
            {editingLog ? "Edit Site Log" : "New Site Log"}
          </Text>

          <Text style={styles.label}>Log Date *</Text>
          <TextInput
            style={styles.input}
            value={form.log_date}
            onChangeText={(v) => setForm((f) => ({ ...f, log_date: v }))}
            placeholder="YYYY-MM-DD"
            autoCapitalize="none"
          />

          <Text style={styles.label}>Workforce Count</Text>
          <TextInput
            style={styles.input}
            value={form.workforce_count}
            onChangeText={(v) =>
              setForm((f) => ({ ...f, workforce_count: v }))
            }
            placeholder="0 or more"
            keyboardType="number-pad"
          />

          <Text style={styles.label}>Weather</Text>
          <TextInput
            style={styles.input}
            value={form.weather}
            onChangeText={(v) => setForm((f) => ({ ...f, weather: v }))}
            placeholder="e.g. Sunny, 32°C"
            maxLength={255}
          />

          <Text style={styles.label}>Blockers</Text>
          <TextInput
            style={[styles.input, styles.multiline]}
            value={form.blockers}
            onChangeText={(v) => setForm((f) => ({ ...f, blockers: v }))}
            placeholder="Any blockers on site..."
            multiline
            numberOfLines={3}
          />

          <Text style={styles.label}>Notes</Text>
          <TextInput
            style={[styles.input, styles.multiline]}
            value={form.notes}
            onChangeText={(v) => setForm((f) => ({ ...f, notes: v }))}
            placeholder="General notes..."
            multiline
            numberOfLines={4}
          />

          <View style={styles.modalActions}>
            <TouchableOpacity
              style={[styles.btn, styles.cancelBtn]}
              onPress={() => setModalVisible(false)}
              disabled={saving}
            >
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.btn, styles.saveBtn]}
              onPress={handleSave}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.saveBtnText}>
                  {editingLog ? "Update" : "Create"}
                </Text>
              )}
            </TouchableOpacity>
          </View>
        </ScrollView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  centered: {flex: 1, justifyContent: "center", alignItems: "center", padding: 24,},
  errorText: {color: "#c0392b", textAlign: "center", marginBottom: 12,},
  retryBtn: {paddingHorizontal: 16, paddingVertical: 8, backgroundColor: "#3498db", borderRadius: 6,},
  retryText: { color: "#fff", fontWeight: "600" },
  list: { padding: 16, paddingBottom: 40 },
  emptyContainer: {flexGrow: 1, justifyContent: "center", alignItems: "center",},
  emptyText: { color: "#7f8c8d", fontSize: 16 },
  card: {backgroundColor: "#fff", borderRadius: 10, padding: 14, marginBottom: 12,
    ...Platform.select({
      ios: {shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 6, shadowOffset: { width: 0, height: 2 },},
      android: { elevation: 2 },
    }),
  },
  cardHeader: {flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6,},
  date: { fontSize: 16, fontWeight: "700", color: "#2c3e50" },
  actions: { flexDirection: "row", gap: 12 },
  actionText: { color: "#3498db", fontWeight: "600" },
  deleteText: { color: "#e74c3c" },
  meta: { fontSize: 14, color: "#34495e", marginTop: 2 },
  blockers: { fontSize: 14, color: "#e67e22", marginTop: 4 },
  notes: { fontSize: 14, color: "#7f8c8d", marginTop: 4 },
  headerBtn: { color: "#3498db", fontWeight: "600", fontSize: 16 },
  modalContent: { padding: 20, paddingBottom: 40 },
  modalTitle: {fontSize: 20, fontWeight: "700", marginBottom: 20, color: "#2c3e50",},
  label: {fontSize: 13, fontWeight: "600", color: "#7f8c8d", marginBottom: 4, marginTop: 12,},
  input: {borderWidth: 1, borderColor: "#dfe6e9", borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15, backgroundColor: "#fafafa",},
  multiline: { minHeight: 80, textAlignVertical: "top" },
  modalActions: {flexDirection: "row", justifyContent: "flex-end", gap: 12, marginTop: 28,},
  btn: {paddingHorizontal: 20, paddingVertical: 12, borderRadius: 8, minWidth: 100, alignItems: "center",},
  cancelBtn: { backgroundColor: "#ecf0f1" },
  cancelBtnText: { color: "#2c3e50", fontWeight: "600" },
  saveBtn: { backgroundColor: "#27ae60" },
  saveBtnText: { color: "#fff", fontWeight: "600" },
});
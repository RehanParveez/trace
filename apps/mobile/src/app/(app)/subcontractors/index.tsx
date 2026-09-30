import { useCallback, useState } from "react";
import {ActivityIndicator, Modal, Pressable, RefreshControl, ScrollView, StyleSheet,Switch, Text, TextInput, View,
} from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { restoreSession } from "../../../api/client";
import {createSubcontractor, listSubcontractors, updateSubcontractor,
} from "../../../api/subcontractors";
import type {AuthUser, Subcontractor, SubcontractorCreatePayload, SubcontractorUpdatePayload,
} from "../../../api/types";

type Form = {
  name: string;
  trade_specialization: string;
  contact_name: string;
  contact_phone: string;
  ntn_or_cnic: string;
  is_active_taxpayer: boolean;
  is_active: boolean;
  notes: string;
};

const emptyForm: Form = {
  name: "",
  trade_specialization: "",
  contact_name: "",
  contact_phone: "",
  ntn_or_cnic: "",
  is_active_taxpayer: false,
  is_active: true,
  notes: "",
};

export default function SubcontractorsScreen() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [rows, setRows] = useState<Subcontractor[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formVisible, setFormVisible] = useState(false);
  const [editing, setEditing] = useState<Subcontractor | null>(null);
  const [form, setForm] = useState<Form>(emptyForm);

  const permissions = user?.role.permissions.map((permission) => permission.key) ?? [];
  const canRead = permissions.includes("subcontractor:read");
  const canManage = permissions.includes("subcontractor:manage");

  const load = useCallback(async (refresh = false) => {
    try {
      if (refresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const currentUser = await restoreSession();
      if (!currentUser) {
        router.replace("/");
        return;
      }

      setUser(currentUser);
      if (!currentUser.role.permissions.some((p) => p.key === "subcontractor:read")) {
        setRows([]);
        return;
      }

      setRows(await listSubcontractors());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load subcontractors.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError(null);
    setFormVisible(true);
  }

  function openEdit(row: Subcontractor) {
    setEditing(row);
    setForm({
      name: row.name,
      trade_specialization: row.trade_specialization,
      contact_name: row.contact_name ?? "",
      contact_phone: row.contact_phone ?? "",
      ntn_or_cnic: row.ntn_or_cnic ?? "",
      is_active_taxpayer: row.is_active_taxpayer,
      is_active: row.is_active,
      notes: row.notes ?? "",
    });
    setError(null);
    setFormVisible(true);
  }

  async function save() {
    if (!form.name.trim() || !form.trade_specialization.trim()) {
      setError("Name and trade specialization are required.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (editing) {
        const payload: SubcontractorUpdatePayload = {
          name: form.name.trim(),
          trade_specialization: form.trade_specialization.trim(),
          contact_name: form.contact_name.trim() || null,
          contact_phone: form.contact_phone.trim() || null,
          ntn_or_cnic: form.ntn_or_cnic.trim() || null,
          is_active_taxpayer: form.is_active_taxpayer,
          is_active: form.is_active,
          notes: form.notes.trim() || null,
        };
        await updateSubcontractor(editing.id, payload);
      } else {
        const payload: SubcontractorCreatePayload = {
          name: form.name.trim(),
          trade_specialization: form.trade_specialization.trim(),
          contact_name: form.contact_name.trim() || null,
          contact_phone: form.contact_phone.trim() || null,
          ntn_or_cnic: form.ntn_or_cnic.trim() || null,
          is_active_taxpayer: form.is_active_taxpayer,
          notes: form.notes.trim() || null,
        };
        await createSubcontractor(payload);
      }

      setFormVisible(false);
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save subcontractor.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: "Subcontractors" }} />
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading subcontractors…</Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: "Subcontractors" }} />
      {!canRead ? (
        <View style={styles.center}>
          <Text style={styles.title}>Access unavailable</Text>
          <Text style={styles.muted}>
            Your role does not have permission to view subcontractors.
          </Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.page}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => void load(true)} />
          }
        >
          <Text style={styles.title}>Subcontractor directory</Text>
          <Text style={styles.muted}>Organization subcontractors and trade contacts</Text>

          {canManage ? (
            <Button label="+ Add subcontractor" onPress={openCreate} primary />
          ) : null}

          {error ? <Text style={styles.error}>{error}</Text> : null}

          {rows.length === 0 ? (
            <Text style={styles.empty}>No subcontractors have been added.</Text>
          ) : (
            rows.map((row) => (
              <View key={row.id} style={styles.card}>
                <View style={styles.rowBetween}>
                  <Text style={styles.cardTitle}>{row.name}</Text>
                  <Text style={[styles.badge, row.is_active ? styles.active : styles.inactive]}>
                    {row.is_active ? "ACTIVE" : "INACTIVE"}
                  </Text>
                </View>
                <Text style={styles.body}>{row.trade_specialization}</Text>
                {row.contact_name ? <Text style={styles.muted}>{row.contact_name}</Text> : null}
                {row.contact_phone ? <Text style={styles.muted}>{row.contact_phone}</Text> : null}
                {row.ntn_or_cnic ? <Text style={styles.muted}>NTN/CNIC: {row.ntn_or_cnic}</Text> : null}
                <Text style={styles.muted}>
                  Taxpayer: {row.is_active_taxpayer ? "Active" : "Not marked active"}
                </Text>
                {canManage ? (
                  <Button label="Edit" onPress={() => openEdit(row)} />
                ) : null}
              </View>
            ))
          )}
        </ScrollView>
      )}

      <Modal visible={formVisible} animationType="slide" onRequestClose={() => setFormVisible(false)}>
        <ScrollView contentContainerStyle={styles.page}>
          <Text style={styles.title}>
            {editing ? "Edit subcontractor" : "Add subcontractor"}
          </Text>
          <Field label="Name" value={form.name} onChangeText={(v) => setForm({ ...form, name: v })} />
          <Field label="Trade specialization" value={form.trade_specialization} onChangeText={(v) => setForm({ ...form, trade_specialization: v })} />
          <Field label="Contact name" value={form.contact_name} onChangeText={(v) => setForm({ ...form, contact_name: v })} />
          <Field label="Contact phone" value={form.contact_phone} onChangeText={(v) => setForm({ ...form, contact_phone: v })} keyboardType="phone-pad" />
          <Field label="NTN or CNIC" value={form.ntn_or_cnic} onChangeText={(v) => setForm({ ...form, ntn_or_cnic: v })} />
          <Toggle label="Active taxpayer" value={form.is_active_taxpayer} onValueChange={(v) => setForm({ ...form, is_active_taxpayer: v })} />
          {editing ? (
            <Toggle label="Active subcontractor" value={form.is_active} onValueChange={(v) => setForm({ ...form, is_active: v })} />
          ) : null}
          <Field label="Notes" value={form.notes} onChangeText={(v) => setForm({ ...form, notes: v })} multiline />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Button label={saving ? "Saving…" : "Save"} onPress={() => void save()} primary disabled={saving} />
          <Button label="Cancel" onPress={() => setFormVisible(false)} disabled={saving} />
        </ScrollView>
      </Modal>
    </>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "phone-pad" | "numeric" | "decimal-pad";
  multiline?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{props.label}</Text>
      <TextInput
        style={[styles.input, props.multiline && styles.multiline]}
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType={props.keyboardType ?? "default"}
        multiline={props.multiline}
      />
    </View>
  );
}

function Toggle(props: { label: string; value: boolean; onValueChange: (v: boolean) => void }) {
  return (
    <View style={styles.rowBetween}>
      <Text style={styles.body}>{props.label}</Text>
      <Switch value={props.value} onValueChange={props.onValueChange} />
    </View>
  );
}

function Button(props: {
  label: string;
  onPress: () => void;
  primary?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={props.disabled}
      onPress={props.onPress}
      style={[styles.button, props.primary && styles.primaryButton, props.disabled && styles.disabled]}
    >
      <Text style={[styles.buttonText, props.primary && styles.primaryButtonText]}>
        {props.label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, backgroundColor: "#F4F6F8", padding: 18, gap: 12 },
  center: { flex: 1, backgroundColor: "#F4F6F8", justifyContent: "center", alignItems: "center", padding: 24, gap: 10 },
  title: { color: "#17212F", fontSize: 23, fontWeight: "800" },
  cardTitle: { color: "#17212F", fontSize: 17, fontWeight: "700", flex: 1 },
  body: { color: "#17212F", fontSize: 15 },
  muted: { color: "#667085", fontSize: 14 },
  empty: { color: "#667085", textAlign: "center", padding: 28 },
  error: { color: "#B42318", fontSize: 14, paddingVertical: 6 },
  card: { backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#D8DEE6", padding: 16, gap: 8 },
  rowBetween: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  badge: { overflow: "hidden", borderRadius: 20, paddingHorizontal: 9, paddingVertical: 4, fontSize: 11, fontWeight: "800" },
  active: { color: "#087443", backgroundColor: "#E7F6EE" },
  inactive: { color: "#667085", backgroundColor: "#EEF0F3" },
  field: { gap: 6 },
  label: { color: "#344054", fontSize: 13, fontWeight: "700" },
  input: { minHeight: 46, backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, paddingHorizontal: 12, color: "#17212F" },
  multiline: { minHeight: 90, textAlignVertical: "top", paddingTop: 10 },
  button: { minHeight: 46, borderRadius: 10, borderWidth: 1, borderColor: "#D0D5DD", backgroundColor: "#FFFFFF", alignItems: "center", justifyContent: "center", paddingHorizontal: 14, marginTop: 4 },
  buttonText: { color: "#183153", fontSize: 15, fontWeight: "700" },
  primaryButton: { backgroundColor: "#183153", borderColor: "#183153" },
  primaryButtonText: { color: "#FFFFFF" },
  disabled: { opacity: 0.55 },
});
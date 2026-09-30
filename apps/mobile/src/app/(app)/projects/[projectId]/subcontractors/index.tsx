import { useCallback, useState } from "react";
import {ActivityIndicator, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import {Stack, router, useFocusEffect, useLocalSearchParams,
} from "expo-router";
import { restoreSession } from "../../../../../api/client";
import { getProject } from "../../../../../api/projects";
import {createAgreement, getProjectSubcontractCost, listProjectAgreements, listSubcontractors,
} from "../../../../../api/subcontractors";
import type {AuthUser, Project, ProjectSubcontractCost, SubcontractAgreementCreatePayload, SubcontractAgreementDetail, Subcontractor,
} from "../../../../../api/types";

type ItemForm = {
  description: string;
  unit: string;
  quantity: string;
  rate: string;
};

const emptyItem = (): ItemForm => ({
  description: "",
  unit: "",
  quantity: "",
  rate: "",
});

export default function ProjectSubcontractorsScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [agreements, setAgreements] = useState<SubcontractAgreementDetail[]>([]);
  const [subcontractors, setSubcontractors] = useState<Subcontractor[]>([]);
  const [cost, setCost] = useState<ProjectSubcontractCost | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formVisible, setFormVisible] = useState(false);

  const [subcontractorId, setSubcontractorId] = useState("");
  const [scope, setScope] = useState("");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [retention, setRetention] = useState("10");
  const [retentionCap, setRetentionCap] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<ItemForm[]>([emptyItem()]);

  const permissions = user?.role.permissions.map((p) => p.key) ?? [];
  const canRead = permissions.includes("subcontractor:read");
  const canManage = permissions.includes("subcontractor:manage");

  const load = useCallback(async (refresh = false) => {
    try {
      if (refresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      if (!projectId) throw new Error("Project ID is missing.");

      const currentUser = await restoreSession();
      if (!currentUser) {
        router.replace("/");
        return;
      }

      setUser(currentUser);
      if (!currentUser.role.permissions.some((p) => p.key === "subcontractor:read")) {
        setProject(null);
        setAgreements([]);
        setSubcontractors([]);
        setCost(null);
        return;
      }

      const [projectResult, agreementRows, projectCost, directory] =
        await Promise.all([
          getProject(projectId),
          listProjectAgreements(projectId),
          getProjectSubcontractCost(projectId),
          listSubcontractors(),
        ]);

      setProject(projectResult);
      setAgreements(agreementRows);
      setCost(projectCost);
      setSubcontractors(directory);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load project subcontractors.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId]);

  useFocusEffect(useCallback(() => {
    void load();
  }, [load]));

  function resetForm() {
    setSubcontractorId("");
    setScope("");
    setStartDate(new Date().toISOString().slice(0, 10));
    setRetention("10");
    setRetentionCap("");
    setNotes("");
    setItems([emptyItem()]);
  }

  async function saveAgreement() {
    if (!projectId || !subcontractorId || !scope.trim()) {
      setError("Choose a subcontractor and enter the agreement scope.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
      setError("Enter the start date as YYYY-MM-DD.");
      return;
    }
    if (!Number.isFinite(Number(retention)) || Number(retention) < 0 || Number(retention) > 100) {
      setError("Retention must be between 0 and 100.");
      return;
    }
    if (retentionCap.trim() && (!Number.isFinite(Number(retentionCap)) || Number(retentionCap) < 0 || Number(retentionCap) > 100)) {
      setError("Retention cap must be between 0 and 100.");
      return;
    }
    if (items.length === 0 || items.some((item) =>
      !item.description.trim() ||
      !item.unit.trim() ||
      !Number.isFinite(Number(item.quantity)) ||
      Number(item.quantity) <= 0 ||
      !Number.isFinite(Number(item.rate)) ||
      Number(item.rate) < 0
    )) {
      setError("Each contract item needs a description, unit, positive quantity, and non-negative rate.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const payload: SubcontractAgreementCreatePayload = {
        project_id: projectId,
        subcontractor_id: subcontractorId,
        scope_description: scope.trim(),
        start_date: startDate,
        default_retention_percentage: Number(retention),
        default_retention_cap_percentage: retentionCap.trim()
          ? Number(retentionCap)
          : null,
        notes: notes.trim() || null,
        items: items.map((item) => ({
          description: item.description.trim(),
          unit: item.unit.trim(),
          quantity: Number(item.quantity),
          rate: Number(item.rate),
        })),
      };

      await createAgreement(payload);
      setFormVisible(false);
      resetForm();
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create agreement.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: "Subcontractors" }} />
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading project…</Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: project?.name ?? "Subcontractors" }} />

      {!canRead ? (
        <View style={styles.center}>
          <Text style={styles.title}>Access unavailable</Text>
          <Text style={styles.muted}>
            Your role cannot view subcontractor agreements.
          </Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.page}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => void load(true)}
            />
          }
        >
          <Text style={styles.eyebrow}>{project?.name ?? "PROJECT"}</Text>
          <Text style={styles.title}>Subcontractors</Text>

          <View style={styles.card}>
            <Text style={styles.label}>Total billed to this project</Text>
            <Text style={styles.amount}>
              {cost
                ? `${cost.currency} ${Number(cost.total_billed).toLocaleString()}`
                : "—"}
            </Text>
          </View>

          {canManage ? (
            <Button
              label="+ New agreement"
              primary
              onPress={() => {
                resetForm();
                setError(null);
                setFormVisible(true);
              }}
            />
          ) : null}

          {error ? <Text style={styles.error}>{error}</Text> : null}

          {agreements.length === 0 ? (
            <Text style={styles.muted}>No agreements for this project yet.</Text>
          ) : agreements.map((agreement) => {
            const contractor = subcontractors.find(
              (item) => item.id === agreement.subcontractor_id,
            );

            return (
              <Pressable
                key={agreement.id}
                style={styles.card}
                accessibilityRole="button"
                onPress={() => router.push({
                  pathname: "/projects/[projectId]/subcontractors/[agreementId]",
                  params: { projectId: projectId!, agreementId: agreement.id },
                })}
              >
                <Text style={styles.cardTitle}>
                  {contractor?.name ?? "Subcontractor"}
                </Text>
                <Text style={styles.body}>{agreement.scope_description}</Text>
                <Text style={styles.muted}>
                  Contract value: {cost?.currency ?? ""}{" "}
                  {Number(agreement.contract_value).toLocaleString()}
                </Text>
                <Text style={styles.muted}>
                  {agreement.start_date} · {agreement.status.replaceAll("_", " ")}
                </Text>
                <Text style={styles.link}>Open agreement ›</Text>
              </Pressable>
            );
          })}
        </ScrollView>
      )}

      <Modal
        visible={formVisible}
        animationType="slide"
        onRequestClose={() => setFormVisible(false)}
      >
        <ScrollView contentContainerStyle={styles.page}>
          <Text style={styles.title}>New subcontract agreement</Text>
          <Text style={styles.label}>Select subcontractor</Text>

          {subcontractors.filter((item) => item.is_active).map((item) => (
            <Pressable
              key={item.id}
              style={[
                styles.selectRow,
                subcontractorId === item.id && styles.selected,
              ]}
              onPress={() => setSubcontractorId(item.id)}
            >
              <Text style={styles.body}>
                {item.name} · {item.trade_specialization}
              </Text>
            </Pressable>
          ))}

          {subcontractors.every((item) => !item.is_active) ? (
            <Text style={styles.error}>
              Add an active subcontractor in the organization directory first.
            </Text>
          ) : null}

          <Field label="Scope" value={scope} onChangeText={setScope} multiline />
          <Field
            label="Start date (YYYY-MM-DD)"
            value={startDate}
            onChangeText={setStartDate}
          />
          <Field
            label="Default retention percentage"
            value={retention}
            onChangeText={setRetention}
            keyboardType="decimal-pad"
          />
          <Field
            label="Retention cap percentage (optional)"
            value={retentionCap}
            onChangeText={setRetentionCap}
            keyboardType="decimal-pad"
          />

          <Text style={styles.sectionTitle}>Contract items</Text>

          {items.map((item, index) => (
            <View key={index} style={styles.itemCard}>
              <Field
                label="Description"
                value={item.description}
                onChangeText={(value) => setItems((old) =>
                  old.map((row, i) => i === index ? { ...row, description: value } : row)
                )}
              />
              <Field
                label="Unit"
                value={item.unit}
                onChangeText={(value) => setItems((old) =>
                  old.map((row, i) => i === index ? { ...row, unit: value } : row)
                )}
              />
              <Field
                label="Quantity"
                value={item.quantity}
                onChangeText={(value) => setItems((old) =>
                  old.map((row, i) => i === index ? { ...row, quantity: value } : row)
                )}
                keyboardType="decimal-pad"
              />
              <Field
                label="Rate"
                value={item.rate}
                onChangeText={(value) => setItems((old) =>
                  old.map((row, i) => i === index ? { ...row, rate: value } : row)
                )}
                keyboardType="decimal-pad"
              />
              {items.length > 1 ? (
                <Button
                  label="Remove item"
                  onPress={() => setItems((old) => old.filter((_, i) => i !== index))}
                />
              ) : null}
            </View>
          ))}

          <Button
            label="+ Add item"
            onPress={() => setItems((old) => [...old, emptyItem()])}
          />
          <Field label="Notes (optional)" value={notes} onChangeText={setNotes} multiline />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Button
            label={saving ? "Creating…" : "Create agreement"}
            primary
            disabled={saving}
            onPress={() => void saveAgreement()}
          />
          <Button
            label="Cancel"
            disabled={saving}
            onPress={() => setFormVisible(false)}
          />
        </ScrollView>
      </Modal>
    </>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
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
      style={[
        styles.button,
        props.primary && styles.primary,
        props.disabled && styles.disabled,
      ]}
    >
      <Text style={[styles.buttonText, props.primary && styles.primaryText]}>
        {props.label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 18, gap: 12, backgroundColor: "#F4F6F8" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 10, backgroundColor: "#F4F6F8" },
  eyebrow: { color: "#8A7B67", fontSize: 12, fontWeight: "800" },
  title: { fontSize: 23, fontWeight: "800", color: "#17212F" },
  sectionTitle: { fontSize: 17, fontWeight: "800", color: "#17212F" },
  label: { color: "#344054", fontSize: 13, fontWeight: "700" },
  body: { color: "#17212F", fontSize: 15 },
  muted: { color: "#667085", fontSize: 14 },
  amount: { color: "#183153", fontSize: 22, fontWeight: "800" },
  card: { backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#D8DEE6", padding: 16, gap: 8 },
  cardTitle: { color: "#17212F", fontSize: 17, fontWeight: "800" },
  link: { color: "#183153", fontWeight: "700" },
  error: { color: "#B42318" },
  field: { gap: 5 },
  input: { minHeight: 44, borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 9, backgroundColor: "#FFFFFF", paddingHorizontal: 11, color: "#17212F" },
  multiline: { minHeight: 76, textAlignVertical: "top", paddingTop: 9 },
  itemCard: { backgroundColor: "#EEF1F5", padding: 12, borderRadius: 12, gap: 8 },
  selectRow: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 9, padding: 12 },
  selected: { borderColor: "#183153", borderWidth: 2 },
  button: { minHeight: 44, borderWidth: 1, borderColor: "#D0D5DD", backgroundColor: "#FFFFFF", borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 14 },
  buttonText: { color: "#183153", fontWeight: "700" },
  primary: { backgroundColor: "#183153", borderColor: "#183153" },
  primaryText: { color: "#FFFFFF" },
  disabled: { opacity: 0.5 },
});
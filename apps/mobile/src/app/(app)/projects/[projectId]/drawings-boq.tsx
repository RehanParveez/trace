import { useCallback, useEffect, useRef, useState } from "react";
import {ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import * as DocumentPicker from "expo-document-picker";
import { restoreSession } from "../../../../api/client";
import { getProject } from "../../../../api/projects";
import {addCustomBOQItem, approveBOQItem, createBOQVersion, getBOQSummary, listBOQItems, listProjectBOQVersions, listProjectDrawings, updateBOQItem, uploadProjectDrawing,
} from "../../../../api/drawingsBoq";
import type {BOQItem, BOQSummary, BOQVersion, Drawing, Project,
} from "../../../../api/types";

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

export default function DrawingsBoqScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [versions, setVersions] = useState<BOQVersion[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [drawingsError, setDrawingsError] = useState("");
  const [boqError, setBoqError] = useState("");

  const [expandedVersion, setExpandedVersion] = useState("");
  const [boqLoading, setBoqLoading] = useState(false);
  const [boqItems, setBoqItems] = useState<BOQItem[]>([]);
  const [boqSummary, setBoqSummary] = useState<BOQSummary | null>(null);
  const boqRequest = useRef(0);

  const [versionLabel, setVersionLabel] = useState("");
  const [itemName, setItemName] = useState("");
  const [itemUnit, setItemUnit] = useState("");
  const [itemQuantity, setItemQuantity] = useState("");
  const [itemCategory, setItemCategory] = useState("");
  const [itemRate, setItemRate] = useState("");
  const [editingItemId, setEditingItemId] = useState("");
  const [editingItemVersion, setEditingItemVersion] = useState<number | null>(null);

  const canUpload = permissions.includes("drawing:create");
  const canCreateItem = permissions.includes("boq_item_create");
  const canUpdateItem = permissions.includes("boq:update");
  const canApprove = permissions.includes("boq:approve");

  const load = useCallback(async () => {
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
      setPermissions(user.role.permissions.map((p) => p.key));
      setProject(await getProject(projectId));

      const [drawingResult, versionResult] = await Promise.allSettled([
        listProjectDrawings(projectId),
        listProjectBOQVersions(projectId),
      ]);

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
      setError(err instanceof Error ? err.message : "Could not load project.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleVersion(version: BOQVersion) {
    if (expandedVersion === version.id) {
      boqRequest.current += 1;
      setExpandedVersion("");
      setBoqLoading(false);
      setEditingItemId("");
      setEditingItemVersion(null);
      return;
    }

    const requestId = boqRequest.current + 1;
    boqRequest.current = requestId;
    setExpandedVersion(version.id);
    setBoqLoading(true);
    setBoqError("");
    setBoqItems([]);
    setBoqSummary(null);
    setEditingItemId("");
    setEditingItemVersion(null);

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

  async function handleUploadDrawing() {
    if (!projectId || !canUpload) return;
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*", "*/*"],
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;

      const file = result.assets[0];
      setBusy(true);
      setError("");
      await uploadProjectDrawing(projectId, {
        uri: file.uri,
        name: file.name,
        mimeType: file.mimeType,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload drawing.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateVersion() {
    if (!projectId) return;
    if (!versionLabel.trim()) {
      setError("Enter a BOQ version label.");
      return;
    }
    await run(async () => {
      await createBOQVersion(projectId, { label: versionLabel.trim() });
      setVersionLabel("");
    });
  }

  async function refreshExpandedVersion() {
    const version = versions.find((v) => v.id === expandedVersion);
    if (version) {
      setExpandedVersion("");
      await toggleVersion(version);
    }
  }

  async function handleAddCustomItem() {
    if (!expandedVersion) {
      setError("Expand a BOQ version first.");
      return;
    }
    if (!itemName.trim() || !itemUnit.trim()) {
      setError("Enter material name and unit.");
      return;
    }
    const qty = Number(itemQuantity);
    if (!Number.isFinite(qty) || qty <= 0) {
      setError("Quantity must be a positive number.");
      return;
    }
    const rate = itemRate.trim() === "" ? null : Number(itemRate);
    if (rate !== null && !Number.isFinite(rate)) {
      setError("Unit rate must be a valid number.");
      return;
    }

    await run(async () => {
      await addCustomBOQItem(expandedVersion, {
        material_name: itemName.trim(),
        unit: itemUnit.trim(),
        quantity: qty,
        category: itemCategory.trim() || null,
        unit_rate: rate,
      });
      setItemName("");
      setItemUnit("");
      setItemQuantity("");
      setItemCategory("");
      setItemRate("");
      await refreshExpandedVersion();
    });
  }

  function beginEditItem(item: BOQItem) {
    setEditingItemId(item.id);
    setEditingItemVersion(item.version ?? null);
    setItemName(item.material_name);
    setItemUnit(item.unit);
    setItemQuantity(String(item.quantity));
    setItemCategory(item.category ?? "");
    setItemRate(item.unit_rate === null ? "" : String(item.unit_rate));
  }

  async function handleSaveItem() {
    if (!editingItemId) return;
    if (editingItemVersion == null) {
      setError("Missing item version. Re-open the item and try again.");
      return;
    }
    if (!itemName.trim() || !itemUnit.trim()) {
      setError("Enter material name and unit.");
      return;
    }
    const qty = Number(itemQuantity);
    if (!Number.isFinite(qty) || qty <= 0) {
      setError("Quantity must be a positive number.");
      return;
    }
    const rate = itemRate.trim() === "" ? null : Number(itemRate);
    if (rate !== null && !Number.isFinite(rate)) {
      setError("Unit rate must be a valid number.");
      return;
    }

    await run(async () => {
      await updateBOQItem(editingItemId, {
        material_name: itemName.trim(),
        unit: itemUnit.trim(),
        quantity: qty,
        category: itemCategory.trim() || null,
        unit_rate: rate,
        version: editingItemVersion,
      });
      setEditingItemId("");
      setEditingItemVersion(null);
      setItemName("");
      setItemUnit("");
      setItemQuantity("");
      setItemCategory("");
      setItemRate("");
      await refreshExpandedVersion();
    });
  }

  async function handleApproveItem(item: BOQItem) {
    await run(async () => {
      await approveBOQItem(item.id);
      await refreshExpandedVersion();
    });
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading drawings & BOQ…</Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <Text style={styles.error}>{error || "Project not found."}</Text>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  Back to project</Text>
        </Pressable>
      </View>
    );
  }

  const currentDrawings = drawings.filter((d) => d.is_current_revision);

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  {project.name}</Text>
        </Pressable>

        <Text style={styles.title}>Drawings & BOQ</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Text style={styles.section}>Drawings</Text>
        {drawingsError ? <Text style={styles.error}>{drawingsError}</Text> : null}

        {canUpload ? (
          <Action title="Upload drawing" onPress={() => void handleUploadDrawing()} />
        ) : null}

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

        <Text style={styles.section}>Bill of quantities</Text>
        {boqError && !expandedVersion ? (
          <Text style={styles.error}>{boqError}</Text>
        ) : null}

        <Text style={styles.label}>New BOQ version label</Text>
        <TextInput
          style={styles.input}
          value={versionLabel}
          onChangeText={setVersionLabel}
          placeholder="e.g. Rev A"
        />
        <Action title="Create BOQ version" onPress={() => void handleCreateVersion()} />

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
                      <InfoRow label="Total" value={formatMoney(boqSummary.grand_total)} />
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

                  {(canCreateItem || canUpdateItem) && (
                    <>
                      <Text style={styles.label}>
                        {editingItemId ? "Edit BOQ item" : "Add custom BOQ item"}
                      </Text>
                      <Field label="Material name" value={itemName} onChangeText={setItemName} />
                      <Field label="Unit" value={itemUnit} onChangeText={setItemUnit} />
                      <Field
                        label="Quantity"
                        value={itemQuantity}
                        onChangeText={setItemQuantity}
                        keyboardType="decimal-pad"
                      />
                      <Field
                        label="Category"
                        value={itemCategory}
                        onChangeText={setItemCategory}
                      />
                      <Field
                        label="Unit rate (optional)"
                        value={itemRate}
                        onChangeText={setItemRate}
                        keyboardType="decimal-pad"
                      />
                      {editingItemId ? (
                        <View style={styles.row}>
                          <Action title="Save item" onPress={() => void handleSaveItem()} />
                          <Action
                            title="Cancel"
                            secondary
                            onPress={() => {
                              setEditingItemId("");
                              setEditingItemVersion(null);
                              setItemName("");
                              setItemUnit("");
                              setItemQuantity("");
                              setItemCategory("");
                              setItemRate("");
                            }}
                          />
                        </View>
                      ) : canCreateItem ? (
                        <Action
                          title="Add custom item"
                          onPress={() => void handleAddCustomItem()}
                        />
                      ) : null}
                    </>
                  )}

                  {!boqLoading && !boqError && boqItems.length === 0 ? (
                    <Text style={styles.muted}>This BOQ has no items yet.</Text>
                  ) : null}

                  {boqItems.map((item) => (
                    <View key={item.id} style={styles.boqItem}>
                      <View style={styles.versionHeading}>
                        <Text style={styles.itemTitle}>{item.material_name}</Text>
                        <Text
                          style={
                            item.status === "APPROVED" ? styles.approved : styles.draft
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
                      <View style={styles.row}>
                        {canUpdateItem && item.status !== "APPROVED" ? (
                          <Action
                            title="Edit"
                            secondary
                            onPress={() => beginEditItem(item)}
                          />
                        ) : null}
                        {canApprove && item.status !== "APPROVED" ? (
                          <Action
                            title="Approve"
                            onPress={() => void handleApproveItem(item)}
                          />
                        ) : null}
                      </View>
                    </View>
                  ))}
                </View>
              ) : null}
            </View>
          ))
        )}

        {busy ? (
          <View style={styles.busy}>
            <ActivityIndicator color="#183153" />
            <Text style={styles.muted}>Working…</Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field({
  label,
  value,
  onChangeText,
  keyboardType = "default",
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
}) {
  return (
    <>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
      />
    </>
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

function Action({
  title,
  onPress,
  secondary = false,
}: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
}) {
  return (
    <Pressable
      style={[styles.action, secondary && styles.actionSecondary]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <Text style={[styles.actionText, secondary && styles.actionSecondaryText]}>
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#F4F6F8" },
  page: {flexGrow: 1, padding: 22, paddingTop: 52, paddingBottom: 48, backgroundColor: "#F4F6F8",},
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8",},
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginVertical: 18,},
  section: {color: "#17212F", fontSize: 20, fontWeight: "700", marginTop: 28, marginBottom: 8,},
  label: {color: "#344054", fontSize: 14, fontWeight: "600", marginTop: 14, marginBottom: 7,},
  fieldLabel: {color: "#344054", fontSize: 13, fontWeight: "600", marginTop: 10, marginBottom: 5,},
  input: {backgroundColor: "white", borderColor: "#D0D5DD", borderWidth: 1, borderRadius: 10, padding: 14, fontSize: 16, color: "#17212F",},
  card: {backgroundColor: "white", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 15, marginTop: 10,},
  listCard: {backgroundColor: "white", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 16, marginBottom: 10, marginTop: 8,},
  itemTitle: {flex: 1, color: "#17212F", fontSize: 15, fontWeight: "700", marginRight: 8,},
  muted: { color: "#667085", marginTop: 5, lineHeight: 20 },
  error: { color: "#B42318", marginTop: 12, lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700" },
  versionHeading: {flexDirection: "row", alignItems: "center", justifyContent: "space-between",},
  versionCopy: { flex: 1 },
  versionDetails: {borderTopWidth: 1, borderTopColor: "#E4E7EC", marginTop: 14, paddingTop: 14,},
  summaryBox: {backgroundColor: "#F8FAFC", borderRadius: 10, paddingHorizontal: 12, paddingTop: 4, marginBottom: 12,},
  boqItem: {borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 12,},
  approved: { color: "#067647", fontSize: 11, fontWeight: "700" },
  draft: { color: "#B54708", fontSize: 11, fontWeight: "700" },
  infoRow: {flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 8, borderTopWidth: 1, borderTopColor: "#F0F2F5",},
  infoLabel: { color: "#667085", fontSize: 13, flex: 1 },
  infoValue: {color: "#17212F", fontSize: 13, fontWeight: "600", flex: 1,textAlign: "right",},
  action: {backgroundColor: "#183153", borderRadius: 10, alignItems: "center", padding: 13, marginTop: 10,},
  actionSecondary: {backgroundColor: "white", borderWidth: 1, borderColor: "#D0D5DD",},
  actionText: { color: "white", fontWeight: "700" },
  actionSecondaryText: { color: "#183153" },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  busy: { alignItems: "center", padding: 18, gap: 8 },
})
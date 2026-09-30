import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  Stack,
  router,
  useFocusEffect,
  useLocalSearchParams,
} from "expo-router";
import { restoreSession } from "../../../../../api/client";
import {
  approveChangeOrder,
  cancelChangeOrder,
  createChangeOrder,
  getChangeOrder,
  getProjectChangeOrderSummary,
  listChangeOrders,
  rejectChangeOrder,
} from "../../../../../api/changeOrders";
import {
  listBOQItems,
  listProjectBOQVersions,
} from "../../../../../api/drawingsBoq";
import { getProject } from "../../../../../api/projects";
import type {
  AuthUser,
  BOQItem,
  BOQVersion,
  ChangeOrderDetail,
  ChangeOrderLineItemInput,
  ChangeOrderType,
  Project,
  ProjectChangeOrderSummary,
} from "../../../../../api/types";

type LineDraft = {
  mode: "new" | "adjust";
  description: string;
  unit: string;
  boqItemId: string;
  quantity: string;
  unitRate: string;
};

const newLine = (): LineDraft => ({
  mode: "new",
  description: "",
  unit: "",
  boqItemId: "",
  quantity: "",
  unitRate: "",
});

function money(value: number | string, currency: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);

  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString()} ${currency}`;
  }
}

function formatType(value: ChangeOrderType): string {
  switch (value) {
    case "ADDITION":
      return "Addition";
    case "OMISSION":
      return "Omission";
    case "VARIATION":
      return "Variation";
  }
}

export default function ProjectChangeOrdersScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [orders, setOrders] = useState<ChangeOrderDetail[]>([]);
  const [summary, setSummary] = useState<ProjectChangeOrderSummary | null>(null);
  const [versions, setVersions] = useState<BOQVersion[]>([]);
  const [boqItems, setBoqItems] = useState<BOQItem[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [changeType, setChangeType] =
    useState<ChangeOrderType>("ADDITION");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [clientReference, setClientReference] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([newLine()]);

  const [selectedOrder, setSelectedOrder] =
    useState<ChangeOrderDetail | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const permissionKeys = user?.role.permissions.map((p) => p.key) ?? [];
  const canRead = permissionKeys.includes("change_order:read");
  const canCreate = permissionKeys.includes("change_order:create");
  const canApprove = permissionKeys.includes("change_order:approve");
  const canReadBoq = permissionKeys.includes("drawing:read");

  const load = useCallback(async (refresh = false) => {
    if (!projectId) {
      setError("Project ID is missing.");
      setLoading(false);
      return;
    }

    if (refresh) setRefreshing(true);
    else setLoading(true);

    setError("");
    setNotice("");

    try {
      const currentUser = await restoreSession();
      if (!currentUser) {
        router.replace("/");
        return;
      }

      setUser(currentUser);

      const hasRead = currentUser.role.permissions.some(
        (permission) => permission.key === "change_order:read",
      );

      if (!hasRead) {
        setProject(null);
        setOrders([]);
        setSummary(null);
        setVersions([]);
        setBoqItems([]);
        return;
      }

      const canLoadBoq = currentUser.role.permissions.some(
        (permission) =>
          permission.key === "change_order:create" &&
          currentUser.role.permissions.some(
            (item) => item.key === "drawing:read",
          ),
      );

      const [projectResult, orderRows, summaryResult, versionRows] =
        await Promise.all([
          getProject(projectId),
          listChangeOrders(projectId),
          getProjectChangeOrderSummary(projectId),
          canLoadBoq ? listProjectBOQVersions(projectId) : Promise.resolve([]),
        ]);

      setProject(projectResult);
      setOrders(orderRows);
      setSummary(summaryResult);
      setVersions(versionRows);

      const keepVersion = versionRows.some(
        (version) => version.id === selectedVersionId,
      );
      const nextVersionId = keepVersion
        ? selectedVersionId
        : versionRows.find((version) => version.status === "ACTIVE")?.id ??
          versionRows[0]?.id ??
          "";

      setSelectedVersionId(nextVersionId);

      if (nextVersionId && canLoadBoq) {
        const items = await listBOQItems(nextVersionId);
        setBoqItems(items);
      } else {
        setBoqItems([]);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load project change orders.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId, selectedVersionId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function selectVersion(versionId: string) {
    setSelectedVersionId(versionId);
    setBoqItems([]);
    setError("");

    if (!versionId || !canReadBoq) return;

    try {
      setBoqItems(await listBOQItems(versionId));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load BOQ items.",
      );
    }
  }

  function resetCreateForm() {
    setChangeType("ADDITION");
    setTitle("");
    setDescription("");
    setClientReference("");
    setLines([newLine()]);
  }

  function updateLine(index: number, patch: Partial<LineDraft>) {
    setLines((current) =>
      current.map((line, i) => (i === index ? { ...line, ...patch } : line)),
    );
  }

  function validateAndBuildLines(): ChangeOrderLineItemInput[] | null {
    if (lines.length === 0) {
      setError("Add at least one line item.");
      return null;
    }

    const result: ChangeOrderLineItemInput[] = [];

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      const quantity = Number(line.quantity);
      const unitRate =
        line.unitRate.trim() === "" ? null : Number(line.unitRate);

      if (!line.description.trim() || !line.unit.trim()) {
        setError(`Line ${index + 1}: enter a description and unit.`);
        return null;
      }
      if (!Number.isFinite(quantity)) {
        setError(`Line ${index + 1}: enter a valid quantity.`);
        return null;
      }
      if (unitRate !== null && (!Number.isFinite(unitRate) || unitRate < 0)) {
        setError(`Line ${index + 1}: rate must be zero or greater.`);
        return null;
      }

      if (line.mode === "new") {
        if (quantity <= 0) {
          setError(`Line ${index + 1}: a new BOQ item needs a positive quantity.`);
          return null;
        }
        if (unitRate === null) {
          setError(`Line ${index + 1}: a new BOQ item needs a unit rate.`);
          return null;
        }
        if (changeType === "OMISSION") {
          setError("An omission must adjust an existing BOQ item.");
          return null;
        }

        result.push({
          description: line.description.trim(),
          unit: line.unit.trim(),
          boq_item_id: null,
          quantity,
          unit_rate: unitRate,
        });
      } else {
        if (!line.boqItemId) {
          setError(`Line ${index + 1}: select the BOQ item to adjust.`);
          return null;
        }
        if (quantity === 0) {
          setError(`Line ${index + 1}: an adjustment quantity cannot be zero.`);
          return null;
        }
        if (changeType === "ADDITION" && quantity < 0) {
          setError("An addition must use a positive quantity delta.");
          return null;
        }
        if (changeType === "OMISSION" && quantity > 0) {
          setError("An omission must use a negative quantity delta.");
          return null;
        }

        result.push({
          description: line.description.trim(),
          unit: line.unit.trim(),
          boq_item_id: line.boqItemId,
          quantity,
          unit_rate: unitRate,
        });
      }
    }

    return result;
  }

  async function submitCreate() {
    if (!canCreate || !canReadBoq || !projectId || saving) return;

    if (!selectedVersionId) {
      setError("Select a BOQ version.");
      return;
    }
    if (!title.trim()) {
      setError("Enter a title for the change order.");
      return;
    }

    const lineItems = validateAndBuildLines();
    if (!lineItems) return;

    setSaving(true);
    setError("");

    try {
      await createChangeOrder({
        project_id: projectId,
        boq_version_id: selectedVersionId,
        change_type: changeType,
        title: title.trim(),
        description: description.trim() || null,
        client_reference: clientReference.trim() || null,
        line_items: lineItems,
      });

      setCreateOpen(false);
      resetCreateForm();
      setNotice("Change order draft created.");
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create the change order.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function openDetail(changeOrderId: string) {
    setDetailLoading(true);
    setError("");
    setSelectedOrder(null);

    try {
      setSelectedOrder(await getChangeOrder(changeOrderId));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load change order.",
      );
    } finally {
      setDetailLoading(false);
    }
  }

  async function reloadSelected(changeOrderId: string) {
    await load(true);
    try {
      setSelectedOrder(await getChangeOrder(changeOrderId));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not refresh change order.",
      );
    }
  }

  async function runAction(
    action: "approve" | "reject" | "cancel",
  ) {
    if (!selectedOrder || saving) return;

    const current = selectedOrder;
    setSaving(true);
    setError("");

    try {
      if (action === "approve") {
        await approveChangeOrder(current.id, current.version);
        setNotice("Change order approved; its BOQ changes have been applied.");
      } else if (action === "reject") {
        if (!rejectReason.trim()) {
          setError("Enter a reason for rejecting this change order.");
          return;
        }
        await rejectChangeOrder(
          current.id,
          current.version,
          rejectReason.trim(),
        );
        setRejectOpen(false);
        setRejectReason("");
        setNotice("Change order rejected.");
      } else {
        await cancelChangeOrder(current.id, current.version);
        setNotice("Change order cancelled.");
      }

      await reloadSelected(current.id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Could not ${action} the change order.`,
      );
    } finally {
      setSaving(false);
    }
  }

  function confirmAction(action: "approve" | "cancel") {
    if (!selectedOrder) return;

    const label = action === "approve" ? "approve" : "cancel";
    Alert.alert(
      `${label[0].toUpperCase()}${label.slice(1)} change order?`,
      action === "approve"
        ? "Approving applies its quantity and rate changes to the BOQ."
        : "Only a draft change order can be cancelled.",
      [
        { text: "Keep", style: "cancel" },
        {
          text: label[0].toUpperCase() + label.slice(1),
          style: action === "cancel" ? "destructive" : "default",
          onPress: () => void runAction(action),
        },
      ],
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: "Change Orders" }} />
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading change orders…</Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <Stack.Screen options={{ title: "Change Orders" }} />
        <Text style={styles.title}>Change Orders</Text>
        <Text style={styles.muted}>
          Your role does not have permission to read change orders.
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.page}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => void load(true)}
          tintColor="#183153"
        />
      }
    >
      <Stack.Screen options={{ title: "Change Orders" }} />

      <Text style={styles.eyebrow}>PROJECT</Text>
      <Text style={styles.title}>{project?.name ?? "Change Orders"}</Text>
      {project?.code ? (
        <Text style={styles.muted}>Code: {project.code}</Text>
      ) : null}

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {notice ? <Text style={styles.notice}>{notice}</Text> : null}

      {summary ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Change Order summary</Text>
          <InfoRow label="Approved" value={String(summary.approved_count)} />
          <InfoRow label="Drafts" value={String(summary.draft_count)} />
          <InfoRow
            label="Approved net impact"
            value={money(summary.approved_net_value_impact, summary.currency)}
          />
        </View>
      ) : null}

      {canCreate ? (
        <Pressable
          style={styles.primaryButton}
          accessibilityRole="button"
          onPress={() => {
            setError("");
            setCreateOpen((value) => !value);
          }}
        >
          <Text style={styles.primaryButtonText}>
            {createOpen ? "Close create form" : "＋ Create change order"}
          </Text>
        </Pressable>
      ) : null}

      {createOpen ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>New draft</Text>

          {!canReadBoq ? (
            <Text style={styles.error}>
              Your role needs drawing:read permission to choose a BOQ version
              and its items for a change order.
            </Text>
          ) : versions.length === 0 ? (
            <Text style={styles.muted}>
              No BOQ versions are available for this project.
            </Text>
          ) : (
            <>
              <Text style={styles.label}>BOQ version</Text>
              {versions.map((version) => (
                <Choice
                  key={version.id}
                  label={`${version.label} · ${version.status}`}
                  selected={selectedVersionId === version.id}
                  onPress={() => void selectVersion(version.id)}
                />
              ))}

              <Text style={styles.label}>Change type</Text>
              <View style={styles.row}>
                {(["ADDITION", "OMISSION", "VARIATION"] as const).map(
                  (type) => (
                    <Choice
                      key={type}
                      label={formatType(type)}
                      selected={changeType === type}
                      onPress={() => setChangeType(type)}
                    />
                  ),
                )}
              </View>

              <Field label="Title" value={title} onChangeText={setTitle} />
              <Field
                label="Description (optional)"
                value={description}
                onChangeText={setDescription}
                multiline
              />
              <Field
                label="Client reference (optional)"
                value={clientReference}
                onChangeText={setClientReference}
              />

              <Text style={styles.label}>Line items</Text>
              {lines.map((line, index) => (
                <View key={index} style={styles.lineCard}>
                  <Text style={styles.lineTitle}>Line {index + 1}</Text>
                  <View style={styles.row}>
                    <Choice
                      label="New item"
                      selected={line.mode === "new"}
                      onPress={() =>
                        updateLine(index, {
                          mode: "new",
                          boqItemId: "",
                        })
                      }
                    />
                    <Choice
                      label="Adjust BOQ item"
                      selected={line.mode === "adjust"}
                      onPress={() => updateLine(index, { mode: "adjust" })}
                    />
                  </View>

                  {line.mode === "adjust" ? (
                    <View>
                      <Text style={styles.label}>Existing BOQ item</Text>
                      {boqItems.map((item) => (
                        <Choice
                          key={item.id}
                          label={`${item.material_name} · ${item.quantity} ${item.unit}`}
                          selected={line.boqItemId === item.id}
                          onPress={() =>
                            updateLine(index, {
                              boqItemId: item.id,
                              description: `Adjustment: ${item.material_name}`,
                              unit: item.unit,
                            })
                          }
                        />
                      ))}
                      {boqItems.length === 0 ? (
                        <Text style={styles.muted}>
                          No BOQ items are available for this version.
                        </Text>
                      ) : null}
                    </View>
                  ) : null}

                  <Field
                    label="Description"
                    value={line.description}
                    onChangeText={(value) =>
                      updateLine(index, { description: value })
                    }
                  />
                  <Field
                    label="Unit"
                    value={line.unit}
                    onChangeText={(value) => updateLine(index, { unit: value })}
                  />
                  <Field
                    label={
                      line.mode === "adjust"
                        ? "Quantity change (negative reduces quantity)"
                        : "Quantity"
                    }
                    value={line.quantity}
                    onChangeText={(value) =>
                      updateLine(index, { quantity: value })
                    }
                    keyboardType="decimal-pad"
                  />
                  <Field
                    label={
                      line.mode === "adjust"
                        ? "Rate override (optional)"
                        : "Unit rate"
                    }
                    value={line.unitRate}
                    onChangeText={(value) =>
                      updateLine(index, { unitRate: value })
                    }
                    keyboardType="decimal-pad"
                  />

                  {lines.length > 1 ? (
                    <Pressable
                      onPress={() =>
                        setLines((current) =>
                          current.filter((_, lineIndex) => lineIndex !== index),
                        )
                      }
                    >
                      <Text style={styles.dangerLink}>Remove line</Text>
                    </Pressable>
                  ) : null}
                </View>
              ))}

              <Pressable
                style={styles.secondaryButton}
                onPress={() => setLines((current) => [...current, newLine()])}
              >
                <Text style={styles.secondaryButtonText}>＋ Add line item</Text>
              </Pressable>

              <Pressable
                style={[
                  styles.primaryButton,
                  saving && styles.disabledButton,
                ]}
                disabled={saving || !canReadBoq || versions.length === 0}
                onPress={() => void submitCreate()}
              >
                <Text style={styles.primaryButtonText}>
                  {saving ? "Creating…" : "Create draft"}
                </Text>
              </Pressable>
            </>
          )}
        </View>
      ) : null}

      <Text style={styles.sectionTitle}>Change Orders</Text>

      {orders.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>
            No change orders have been created for this project.
          </Text>
        </View>
      ) : (
        orders.map((order) => (
          <Pressable
            key={order.id}
            style={styles.card}
            accessibilityRole="button"
            onPress={() => void openDetail(order.id)}
          >
            <View style={styles.rowBetween}>
              <Text style={styles.orderTitle}>
                #{order.change_order_number} · {order.title}
              </Text>
              <Text style={styles.status}>{order.status}</Text>
            </View>
            <InfoRow label="Type" value={formatType(order.change_type)} />
            <InfoRow
              label="Value impact"
              value={money(order.value_impact, order.currency)}
            />
            <Text style={styles.link}>Open details ›</Text>
          </Pressable>
        ))
      )}

      <Modal
        visible={detailLoading || selectedOrder !== null}
        animationType="slide"
        onRequestClose={() => {
          setSelectedOrder(null);
          setRejectOpen(false);
          setError("");
        }}
      >
        <ScrollView contentContainerStyle={styles.modalPage}>
          <Text style={styles.sectionTitle}>
            {detailLoading
              ? "Loading change order…"
              : selectedOrder
                ? `Change Order #${selectedOrder.change_order_number}`
                : ""}
          </Text>

          {detailLoading ? (
            <ActivityIndicator size="large" color="#183153" />
          ) : selectedOrder ? (
            <>
              {error ? <Text style={styles.error}>{error}</Text> : null}
              <Text style={styles.orderTitle}>{selectedOrder.title}</Text>
              <InfoRow label="Status" value={selectedOrder.status} />
              <InfoRow
                label="Type"
                value={formatType(selectedOrder.change_type)}
              />
              <InfoRow
                label="Value impact"
                value={money(selectedOrder.value_impact, selectedOrder.currency)}
              />
              {selectedOrder.description ? (
                <Text style={styles.muted}>{selectedOrder.description}</Text>
              ) : null}
              {selectedOrder.client_reference ? (
                <Text style={styles.muted}>
                  Client reference: {selectedOrder.client_reference}
                </Text>
              ) : null}
              {selectedOrder.rejection_reason ? (
                <Text style={styles.error}>
                  Rejection reason: {selectedOrder.rejection_reason}
                </Text>
              ) : null}

              <Text style={styles.sectionTitle}>Line items</Text>
              {selectedOrder.line_items.map((line) => (
                <View key={line.id} style={styles.lineCard}>
                  <Text style={styles.lineTitle}>{line.description}</Text>
                  <InfoRow label="Unit" value={line.unit} />
                  <InfoRow
                    label="Quantity change"
                    value={`${Number(line.quantity) > 0 ? "+" : ""}${line.quantity}`}
                  />
                  <InfoRow
                    label="Unit rate"
                    value={
                      line.unit_rate === null
                        ? "BOQ rate"
                        : money(line.unit_rate, selectedOrder.currency)
                    }
                  />
                  <InfoRow
                    label="Realized impact"
                    value={
                      line.realized_value_impact === null
                        ? "Pending approval"
                        : money(
                            line.realized_value_impact,
                            selectedOrder.currency,
                          )
                    }
                  />
                  {line.created_boq_item_id ? (
                    <Text style={styles.muted}>
                      Approved as a new BOQ item.
                    </Text>
                  ) : null}
                </View>
              ))}

              {selectedOrder.status === "DRAFT" && canApprove && !rejectOpen ? (
                <View style={styles.row}>
                  <ActionButton
                    label="Approve"
                    disabled={saving}
                    onPress={() => confirmAction("approve")}
                  />
                  <ActionButton
                    label="Reject"
                    secondary
                    disabled={saving}
                    onPress={() => {
                      setError("");
                      setRejectReason("");
                      setRejectOpen(true);
                    }}
                  />
                </View>
              ) : null}

              {selectedOrder.status === "DRAFT" && canCreate ? (
                <ActionButton
                  label="Cancel draft"
                  secondary
                  disabled={saving}
                  onPress={() => confirmAction("cancel")}
                />
              ) : null}

              {rejectOpen ? (
                <View style={styles.card}>
                  <Text style={styles.label}>Reason for rejection</Text>
                  <TextInput
                    style={[styles.input, styles.multiline]}
                    value={rejectReason}
                    onChangeText={setRejectReason}
                    multiline
                    textAlignVertical="top"
                  />
                  <ActionButton
                    label={saving ? "Rejecting…" : "Confirm rejection"}
                    disabled={saving || !rejectReason.trim()}
                    onPress={() => void runAction("reject")}
                  />
                  <ActionButton
                    label="Back"
                    secondary
                    disabled={saving}
                    onPress={() => setRejectOpen(false)}
                  />
                </View>
              ) : null}
            </>
          ) : null}

          <ActionButton
            label="Close"
            secondary
            disabled={saving}
            onPress={() => {
              setSelectedOrder(null);
              setRejectOpen(false);
              setError("");
            }}
          />
        </ScrollView>
      </Modal>
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

function Field({
  label,
  value,
  onChangeText,
  keyboardType,
  multiline,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  multiline?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType ?? "default"}
        multiline={multiline}
        textAlignVertical={multiline ? "top" : "center"}
      />
    </View>
  );
}

function Choice({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.choice, selected && styles.choiceSelected]}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
    >
      <Text style={[styles.choiceText, selected && styles.choiceTextSelected]}>
        {selected ? "✓ " : ""}
        {label}
      </Text>
    </Pressable>
  );
}

function ActionButton({
  label,
  disabled,
  secondary,
  onPress,
}: {
  label: string;
  disabled: boolean;
  secondary?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[
        styles.actionButton,
        secondary && styles.secondaryButton,
        disabled && styles.disabledButton,
      ]}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
    >
      <Text
        style={[
          styles.actionButtonText,
          secondary && styles.secondaryButtonText,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 20, paddingTop: 28, paddingBottom: 40, backgroundColor: "#F4F6F8",},
  modalPage: {flexGrow: 1, padding: 20, paddingTop: 40, paddingBottom: 40, backgroundColor: "#F4F6F8",},
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8",},
  eyebrow: { color: "#8A7B67", fontSize: 11, fontWeight: "800", letterSpacing: 1.2,},
  title: {color: "#17212F", fontSize: 25, fontWeight: "700", marginTop: 5,},
  sectionTitle: {color: "#17212F", fontSize: 18, fontWeight: "700", marginTop: 20, marginBottom: 10,},
  card: { backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#E4E7EC", padding: 16, marginTop: 12,},
  lineCard: {backgroundColor: "#F9FAFB", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 14, marginTop: 10,},
  lineTitle: { color: "#17212F", fontSize: 15, fontWeight: "700" },
  orderTitle: {color: "#17212F", fontSize: 16, fontWeight: "700", flexShrink: 1,},
  status: { color: "#183153", fontSize: 11, fontWeight: "800" },
  infoRow: {flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 8, borderTopWidth: 1, borderTopColor: "#F0F2F5",},
  infoLabel: { color: "#667085", fontSize: 13, flex: 1 },
  infoValue: {color: "#17212F", fontSize: 13, fontWeight: "600", flex: 1, textAlign: "right",},
  muted: { color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 6 },
  error: { color: "#B42318", fontSize: 14, lineHeight: 20, marginTop: 10 },
  notice: { color: "#027A48", fontSize: 14, marginTop: 10 },
  label: {color: "#344054", fontSize: 14, fontWeight: "700", marginTop: 13, marginBottom: 7,},
  field: { marginTop: 10 },
  input: {minHeight: 48, borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, backgroundColor: "#FFFFFF", paddingHorizontal: 13, color: "#17212F", fontSize: 15,},
  multiline: { minHeight: 82, paddingTop: 12 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 },
  rowBetween: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10,},
  choice: {minHeight: 42, justifyContent: "center", paddingHorizontal: 12, borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, backgroundColor: "#FFFFFF", marginTop: 7,},
  choiceSelected: { borderColor: "#183153", backgroundColor: "#EAF0F6" },
  choiceText: { color: "#344054", fontSize: 13, fontWeight: "600" },
  choiceTextSelected: { color: "#183153" },
  link: { color: "#183153", fontWeight: "700", marginTop: 12 },
  dangerLink: { color: "#B42318", fontWeight: "700", marginTop: 12 },
  primaryButton: {minHeight: 48, alignItems: "center", justifyContent: "center", backgroundColor: "#183153", borderRadius: 10, padding: 14, marginTop: 14,},
  primaryButtonText: { color: "#FFFFFF", fontWeight: "700" },
  secondaryButton: {minHeight: 46, alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, padding: 13, marginTop: 12,},
  secondaryButtonText: { color: "#183153", fontWeight: "700" },
  actionButton: {minHeight: 44, alignItems: "center", justifyContent: "center", backgroundColor: "#183153", borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, marginTop: 12,},
  actionButtonText: { color: "#FFFFFF", fontWeight: "700" },
  disabledButton: { opacity: 0.55 },
});
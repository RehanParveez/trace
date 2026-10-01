import { useCallback, useState } from "react";
import {ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import {Stack, router, useFocusEffect, useLocalSearchParams,
} from "expo-router";
import { restoreSession } from "../../../../../api/client";
import {getBudgetOrganizationSummary, listProjectBudgets, saveProjectBudget,
} from "../../../../../api/budgets";
import { getProject } from "../../../../../api/projects";
import type {AuthUser, Budget, BudgetCategoryInput, Project,
} from "../../../../../api/types";

type CategoryDraft = {
  name: string;
  amount: string;
};

function money(value: number | string, currency: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${value} ${currency}`;

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

export default function ProjectBudgetScreen() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [currency, setCurrency] = useState("PKR");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [formOpen, setFormOpen] = useState(false);
  const [approvedAmount, setApprovedAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [categories, setCategories] = useState<CategoryDraft[]>([]);

  const permissionKeys = user?.role.permissions.map((p) => p.key) ?? [];
  const canRead = permissionKeys.includes("budget:read");
  const canManage = permissionKeys.includes("budget:manage");

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
        (permission) => permission.key === "budget:read",
      );

      if (!hasRead) {
        setProject(null);
        setBudget(null);
        return;
      }

      const [projectResult, budgetRows, organizationSummary] =
        await Promise.all([
          getProject(projectId),
          listProjectBudgets(projectId),
          getBudgetOrganizationSummary(),
        ]);

      setProject(projectResult);
      setBudget(budgetRows[0] ?? null);
      setCurrency(organizationSummary.currency);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load this project budget.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function openForm() {
    setError("");

    if (budget) {
      setApprovedAmount(String(budget.approved_amount));
      setNotes(budget.notes ?? "");
      setCategories(
        budget.categories.map((category) => ({
          name: category.name,
          amount: String(category.allocated_amount),
        })),
      );
    } else {
      setApprovedAmount("");
      setNotes("");
      setCategories([]);
    }

    setFormOpen(true);
  }

  function updateCategory(index: number, patch: Partial<CategoryDraft>) {
    setCategories((current) =>
      current.map((category, i) =>
        i === index ? { ...category, ...patch } : category,
      ),
    );
  }

  async function submitBudget() {
    if (!canManage || !projectId || saving) return;

    const approved = Number(approvedAmount);
    if (!approvedAmount.trim() || !Number.isFinite(approved) || approved < 0) {
      setError("Enter an approved amount of zero or greater.");
      return;
    }

    const categoryPayload: BudgetCategoryInput[] = [];

    for (let index = 0; index < categories.length; index += 1) {
      const category = categories[index];
      const name = category.name.trim();
      const amountText = category.amount.trim();

      if (!name && !amountText) continue;
      if (!name) {
        setError(`Category ${index + 1}: enter a category name.`);
        return;
      }

      const allocated = Number(amountText);
      if (!amountText || !Number.isFinite(allocated) || allocated < 0) {
        setError(
          `Category ${index + 1}: enter an allocation of zero or greater.`,
        );
        return;
      }

      categoryPayload.push({
        name,
        allocated_amount: allocated,
      });
    }

    setSaving(true);
    setError("");
    setNotice("");

    try {
      await saveProjectBudget(projectId, {
        project_id: projectId,
        approved_amount: approved,
        currency,
        notes: notes.trim() || null,
        categories: categoryPayload,
        ...(budget ? { version: budget.version } : {}),
      });

      setFormOpen(false);
      setNotice(budget ? "Budget updated." : "Budget created.");
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save this budget.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: "Budget" }} />
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading budget…</Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <Stack.Screen options={{ title: "Budget" }} />
        <Text style={styles.title}>Project budget</Text>
        <Text style={styles.muted}>
          Your role does not have permission to read budgets.
        </Text>
      </View>
    );
  }

  const categoryTotal =
    budget?.categories.reduce(
      (sum, category) => sum + Number(category.allocated_amount),
      0,
    ) ?? 0;
  const approvedTotal = Number(budget?.approved_amount ?? 0);
  const allocatedPercent =
    approvedTotal > 0 ? (categoryTotal / approvedTotal) * 100 : 0;

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
      <Stack.Screen options={{ title: "Budget" }} />

      <Text style={styles.eyebrow}>PROJECT BUDGET</Text>
      <Text style={styles.title}>{project?.name ?? "Project budget"}</Text>
      {project?.code ? (
        <Text style={styles.muted}>Code: {project.code}</Text>
      ) : null}

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {notice ? <Text style={styles.notice}>{notice}</Text> : null}

      {budget ? (
        <View style={styles.card}>
          <Text style={styles.label}>Approved budget</Text>
          <Text style={styles.amount}>
            {money(budget.approved_amount, budget.currency)}
          </Text>
          {budget.notes ? <Text style={styles.muted}>{budget.notes}</Text> : null}

          <View style={styles.allocationHeader}>
            <Text style={styles.label}>Category allocation</Text>
            <Text style={styles.share}>
              {allocatedPercent.toFixed(0)}%
            </Text>
          </View>

          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                allocatedPercent > 100 && styles.progressOver,
                { width: `${Math.min(allocatedPercent, 100)}%` },
              ]}
            />
          </View>

          {allocatedPercent > 100 ? (
            <Text style={styles.warning}>
              Allocations exceed the approved budget. The backend permits this;
              review the category amounts.
            </Text>
          ) : null}

          {budget.categories.length === 0 ? (
            <Text style={styles.muted}>No categories have been allocated.</Text>
          ) : (
            budget.categories.map((category) => (
              <View key={category.id} style={styles.categoryRow}>
                <Text style={styles.categoryName}>{category.name}</Text>
                <Text style={styles.categoryAmount}>
                  {money(category.allocated_amount, budget.currency)}
                </Text>
              </View>
            ))
          )}

          <InfoRow label="Currency" value={budget.currency} />
          <InfoRow label="Version" value={String(budget.version)} />
        </View>
      ) : (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>No budget set</Text>
          <Text style={styles.muted}>
            This project does not have an approved budget yet.
          </Text>
        </View>
      )}

      {canManage ? (
        <Pressable
          style={styles.primaryButton}
          accessibilityRole="button"
          onPress={openForm}
        >
          <Text style={styles.primaryButtonText}>
            {budget ? "Update budget" : "Set project budget"}
          </Text>
        </Pressable>
      ) : null}

      {formOpen ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>
            {budget ? "Update budget" : "Set project budget"}
          </Text>
          <Text style={styles.muted}>
            Currency is the organization’s operating currency: {currency}.
          </Text>

          <Field
            label="Approved amount"
            value={approvedAmount}
            onChangeText={setApprovedAmount}
            keyboardType="decimal-pad"
          />
          <Text style={styles.label}>Currency</Text>
          <View style={styles.readOnlyField}>
            <Text style={styles.readOnlyText}>{currency}</Text>
          </View>
          <Field
            label="Notes (optional)"
            value={notes}
            onChangeText={setNotes}
            multiline
          />

          <View style={styles.allocationHeader}>
            <Text style={styles.label}>Category breakdown</Text>
            <Pressable
              accessibilityRole="button"
              onPress={() =>
                setCategories((current) => [
                  ...current,
                  { name: "", amount: "" },
                ])
              }
            >
              <Text style={styles.link}>＋ Add category</Text>
            </Pressable>
          </View>

          {categories.length === 0 ? (
            <Text style={styles.muted}>No categories added.</Text>
          ) : (
            categories.map((category, index) => (
              <View key={index} style={styles.categoryFormRow}>
                <Field
                  label={`Category ${index + 1}`}
                  value={category.name}
                  onChangeText={(value) => updateCategory(index, { name: value })}
                />
                <Field
                  label="Allocated amount"
                  value={category.amount}
                  onChangeText={(value) =>
                    updateCategory(index, { amount: value })
                  }
                  keyboardType="decimal-pad"
                />
                <Pressable
                  accessibilityRole="button"
                  onPress={() =>
                    setCategories((current) =>
                      current.filter((_, categoryIndex) => categoryIndex !== index),
                    )
                  }
                >
                  <Text style={styles.dangerLink}>Remove category</Text>
                </Pressable>
              </View>
            ))
          )}

          <Text style={styles.muted}>
            Updating replaces the full category list. Keep every allocation you
            want to retain in this form.
          </Text>

          <ActionButton
            label={saving ? "Saving…" : budget ? "Save budget changes" : "Create budget"}
            disabled={saving}
            onPress={() => void submitBudget()}
          />
          <ActionButton
            label="Cancel"
            secondary
            disabled={saving}
            onPress={() => setFormOpen(false)}
          />
        </View>
      ) : null}
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

function ActionButton({
  label,
  onPress,
  disabled,
  secondary,
}: {
  label: string;
  onPress: () => void;
  disabled: boolean;
  secondary?: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.actionButton,
        secondary && styles.secondaryButton,
        disabled && styles.disabled,
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
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8",},
  eyebrow: {color: "#8A7B67", fontSize: 11, fontWeight: "800", letterSpacing: 1.2,},
  title: {color: "#17212F", fontSize: 25, fontWeight: "700", marginTop: 5,},
  sectionTitle: {color: "#17212F", fontSize: 18, fontWeight: "700",},
  card: {backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#E4E7EC", padding: 17, marginTop: 16,},
  label: {color: "#344054", fontSize: 14, fontWeight: "700",},
  amount: {color: "#183153", fontSize: 25, fontWeight: "800", marginTop: 5,},
  muted: {color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 7,},
  error: {color: "#B42318", fontSize: 14, lineHeight: 20, marginTop: 12,},
  notice: { color: "#027A48", fontSize: 14, marginTop: 12 },
  warning: { color: "#B54708", fontSize: 13, lineHeight: 19, marginTop: 10 },
  allocationHeader: {flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 18, marginBottom: 8,},
  share: { color: "#183153", fontSize: 13, fontWeight: "800" },
  progressTrack: {height: 8, borderRadius: 8, overflow: "hidden", backgroundColor: "#EAECF0", marginBottom: 10,},
  progressFill: { height: 8, backgroundColor: "#B58A4A" },
  progressOver: { backgroundColor: "#B42318" },
  categoryRow: {flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 11,},
  categoryName: { color: "#344054", fontSize: 14, flex: 1 },
  categoryAmount: { color: "#17212F", fontSize: 14, fontWeight: "700" },
  infoRow: {flexDirection: "row", justifyContent: "space-between", borderTopWidth: 1, borderTopColor: "#F0F2F5", paddingVertical: 9,},
  infoLabel: { color: "#667085", fontSize: 13 },
  infoValue: { color: "#17212F", fontSize: 13, fontWeight: "700" },
  primaryButton: {minHeight: 48, alignItems: "center", justifyContent: "center", borderRadius: 10, backgroundColor: "#183153", padding: 14, marginTop: 14,},
  primaryButtonText: { color: "#FFFFFF", fontWeight: "700" },
  secondaryButton: {backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D0D5DD",},
  secondaryButtonText: { color: "#183153" },
  actionButton: {minHeight: 46, alignItems: "center", justifyContent: "center", borderRadius: 10, backgroundColor: "#183153", padding: 13, marginTop: 12,},
  actionButtonText: { color: "#FFFFFF", fontWeight: "700" },
  disabled: { opacity: 0.55 },
  field: { marginTop: 13 },
  input: {minHeight: 48, borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, backgroundColor: "#FFFFFF", paddingHorizontal: 13, color: "#17212F", fontSize: 15, marginTop: 7,},
  multiline: { minHeight: 82, paddingTop: 12 },
  readOnlyField: {minHeight: 48, justifyContent: "center", borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, backgroundColor: "#F9FAFB", paddingHorizontal: 13, marginTop: 7,},
  readOnlyText: { color: "#667085", fontSize: 15, fontWeight: "600" },
  categoryFormRow: {borderTopWidth: 1, borderTopColor: "#EAECF0", paddingTop: 8, marginTop: 10,},
  link: { color: "#183153", fontWeight: "700" },
  dangerLink: { color: "#B42318", fontWeight: "700", marginTop: 8 },
});
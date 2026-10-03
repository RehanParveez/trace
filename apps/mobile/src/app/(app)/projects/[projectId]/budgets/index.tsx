import { useCallback, useState } from "react";
import {ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import {Stack, router, useFocusEffect, useLocalSearchParams,
} from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../../api/client";
import {getBudgetOrganizationSummary, listProjectBudgets, saveProjectBudget,
} from "../../../../../api/budgets";
import { getProject } from "../../../../../api/projects";
import type {AuthUser, Budget, BudgetCategoryInput, Project,
} from "../../../../../api/types";
import LanguageSwitcher from "../../../../../components/LanguageSwitcher";

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
  amber: "#A96516",
  amberBg: "#F8EDDA",
  red: "#A33A32",
  redBg: "#F9E9E5",
  green: "#26734D",
  greenBg: "#E8F2E9",
};

type CategoryDraft = {
  name: string;
  amount: string;
};

function money(value: number | string, currency: string, locale?: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${value} ${currency}`;

  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString(locale)} ${currency}`;
  }
}

export default function ProjectBudgetScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = i18n.resolvedLanguage || i18n.language;

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

  const permissionKeys = user?.role.permissions.map((permission) => permission.key) ?? [];
  const canRead = permissionKeys.includes("budget:read");
  const canManage = permissionKeys.includes("budget:manage");

  const load = useCallback(
    async (refresh = false) => {
      if (!projectId) {
        setError(t("projectBudget.projectIdMissing"));
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
          err instanceof Error
            ? err.message
            : t("projectBudget.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, t],
  );

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
      current.map((category, categoryIndex) =>
        categoryIndex === index ? { ...category, ...patch } : category,
      ),
    );
  }

  async function submitBudget() {
    if (!canManage || !projectId || saving) return;

    const approved = Number(approvedAmount);
    if (!approvedAmount.trim() || !Number.isFinite(approved) || approved < 0) {
      setError(t("projectBudget.approvedAmountInvalid"));
      return;
    }

    const categoryPayload: BudgetCategoryInput[] = [];

    for (let index = 0; index < categories.length; index += 1) {
      const category = categories[index];
      const name = category.name.trim();
      const amountText = category.amount.trim();

      if (!name && !amountText) continue;
      if (!name) {
        setError(
          t("projectBudget.categoryNameRequired", { index: index + 1 }),
        );
        return;
      }

      const allocated = Number(amountText);
      if (!amountText || !Number.isFinite(allocated) || allocated < 0) {
        setError(
          t("projectBudget.categoryAmountInvalid", { index: index + 1 }),
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
      setNotice(
        budget
          ? t("projectBudget.budgetUpdated")
          : t("projectBudget.budgetCreated"),
      );
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("projectBudget.saveFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  const screenTitle = t("projectBudget.screenTitle");

  if (loading) {
    return (
      <View style={styles.page}>
        <Stack.Screen options={{ title: screenTitle }} />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {screenTitle}
          </Text>
          <LanguageSwitcher />
        </View>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectBudget.loading")}
          </Text>
        </View>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={[styles.page, isUrdu && styles.rtlPage]}>
        <Stack.Screen options={{ title: screenTitle }} />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {screenTitle}
          </Text>
          <LanguageSwitcher />
        </View>
        <View style={styles.messageCard}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("projectBudget.accessUnavailable")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectBudget.accessDenied")}
          </Text>
        </View>
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
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => void load(true)}
          tintColor={C.navy}
          colors={[C.navy]}
        />
      }
    >
      <Stack.Screen options={{ title: screenTitle }} />

      <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
        <View style={styles.headerContent}>
          <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
            {t("projectBudget.eyebrow")}
          </Text>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {project?.name ?? t("projectBudget.projectFallback")}
          </Text>
          {project?.code ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("projectBudget.projectCode", { code: project.code })}
            </Text>
          ) : null}
        </View>
        <LanguageSwitcher />
      </View>

      {error ? (
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error}
        </Text>
      ) : null}
      {notice ? (
        <Text style={[styles.notice, isUrdu && styles.rtlText]}>
          {notice}
        </Text>
      ) : null}

      {budget ? (
        <View style={styles.card}>
          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("projectBudget.approvedBudget")}
          </Text>
          <Text style={styles.amount}>
            {money(budget.approved_amount, budget.currency, locale)}
          </Text>
          {budget.notes ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {budget.notes}
            </Text>
          ) : null}

          <View style={[styles.allocationHeader, isUrdu && styles.rtlRow]}>
            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("projectBudget.categoryAllocation")}
            </Text>
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
            <Text style={[styles.warning, isUrdu && styles.rtlText]}>
              {t("projectBudget.allocationOverBudget")}
            </Text>
          ) : null}

          {budget.categories.length === 0 ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("projectBudget.noCategories")}
            </Text>
          ) : (
            budget.categories.map((category) => (
              <View
                key={category.id}
                style={[styles.categoryRow, isUrdu && styles.rtlRow]}
              >
                <Text
                  style={[styles.categoryName, isUrdu && styles.rtlText]}
                >
                  {category.name}
                </Text>
                <Text style={styles.categoryAmount}>
                  {money(category.allocated_amount, budget.currency, locale)}
                </Text>
              </View>
            ))
          )}

          <InfoRow
            label={t("projectBudget.currency")}
            value={budget.currency}
            isUrdu={isUrdu}
          />
          <InfoRow
            label={t("projectBudget.version")}
            value={String(budget.version)}
            isUrdu={isUrdu}
          />
        </View>
      ) : (
        <View style={styles.messageCard}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("projectBudget.noBudgetTitle")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectBudget.noBudgetHelp")}
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
            {budget
              ? t("projectBudget.updateBudget")
              : t("projectBudget.setBudget")}
          </Text>
        </Pressable>
      ) : null}

      {formOpen ? (
        <View style={styles.card}>
          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {budget
              ? t("projectBudget.updateBudget")
              : t("projectBudget.setBudget")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectBudget.currencyHelp", { currency })}
          </Text>

          <Field
            label={t("projectBudget.approvedAmount")}
            value={approvedAmount}
            onChangeText={setApprovedAmount}
            keyboardType="decimal-pad"
            isUrdu={isUrdu}
          />
          <Text style={[styles.label, isUrdu && styles.rtlText]}>
            {t("projectBudget.currency")}
          </Text>
          <View style={styles.readOnlyField}>
            <Text style={styles.readOnlyText}>{currency}</Text>
          </View>
          <Field
            label={t("projectBudget.notesOptional")}
            value={notes}
            onChangeText={setNotes}
            multiline
            isUrdu={isUrdu}
          />

          <View style={[styles.allocationHeader, isUrdu && styles.rtlRow]}>
            <Text style={[styles.label, isUrdu && styles.rtlText]}>
              {t("projectBudget.categoryBreakdown")}
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() =>
                setCategories((current) => [
                  ...current,
                  { name: "", amount: "" },
                ])
              }
            >
              <Text style={styles.link}>
                {t("projectBudget.addCategory")}
              </Text>
            </Pressable>
          </View>

          {categories.length === 0 ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("projectBudget.noCategoriesAdded")}
            </Text>
          ) : (
            categories.map((category, index) => (
              <View key={index} style={styles.categoryFormRow}>
                <Field
                  label={t("projectBudget.categoryIndex", {
                    index: index + 1,
                  })}
                  value={category.name}
                  onChangeText={(value) =>
                    updateCategory(index, { name: value })
                  }
                  isUrdu={isUrdu}
                />
                <Field
                  label={t("projectBudget.allocatedAmount")}
                  value={category.amount}
                  onChangeText={(value) =>
                    updateCategory(index, { amount: value })
                  }
                  keyboardType="decimal-pad"
                  isUrdu={isUrdu}
                />
                <Pressable
                  accessibilityRole="button"
                  onPress={() =>
                    setCategories((current) =>
                      current.filter(
                        (_, categoryIndex) => categoryIndex !== index,
                      ),
                    )
                  }
                >
                  <Text style={styles.dangerLink}>
                    {t("projectBudget.removeCategory")}
                  </Text>
                </Pressable>
              </View>
            ))
          )}

          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("projectBudget.replaceCategoriesHelp")}
          </Text>

          <ActionButton
            label={
              saving
                ? t("projectBudget.saving")
                : budget
                  ? t("projectBudget.saveChanges")
                  : t("projectBudget.createBudget")
            }
            disabled={saving}
            onPress={() => void submitBudget()}
          />
          <ActionButton
            label={t("projectBudget.cancel")}
            secondary
            disabled={saving}
            onPress={() => setFormOpen(false)}
          />
        </View>
      ) : null}
    </ScrollView>
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
      <Text style={[styles.infoLabel, isUrdu && styles.rtlText]}>
        {label}
      </Text>
      <Text style={[styles.infoValue, isUrdu && styles.rtlText]}>
        {value}
      </Text>
    </View>
  );
}

function Field({
  label,
  value,
  onChangeText,
  keyboardType,
  multiline,
  isUrdu,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  multiline?: boolean;
  isUrdu: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={[styles.label, isUrdu && styles.rtlText]}>{label}</Text>
      <TextInput
        style={[
          styles.input,
          multiline && styles.multiline,
          isUrdu && styles.rtlText,
        ]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType ?? "default"}
        multiline={multiline}
        textAlignVertical={multiline ? "top" : "center"}
        textAlign={isUrdu ? "right" : "left"}
        placeholderTextColor={C.muted}
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
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 16 },
  headerContent: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: C.background, padding: 24 },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 25, fontWeight: "800", marginTop: 5 },
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: "800" },
  card: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, padding: 16, marginTop: 16 },
  messageCard: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, padding: 18, marginTop: 12 },
  label: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  amount: { color: C.navy, fontSize: 26, fontWeight: "800", marginTop: 5 },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 7 },
  error: { color: C.red, backgroundColor: C.redBg, borderWidth: 1, borderColor: "#EAC6C0", borderRadius: 11, fontSize: 13, lineHeight: 19, padding: 12, marginTop: 12 },
  notice: { color: C.green, backgroundColor: C.greenBg, borderWidth: 1, borderColor: "#CEE1D2", borderRadius: 11, fontSize: 13, lineHeight: 19, padding: 12, marginTop: 12 },
  warning: { color: C.amber, backgroundColor: C.amberBg, borderRadius: 10, padding: 11, fontSize: 13, lineHeight: 19, marginTop: 10 },
  allocationHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10, marginTop: 18, marginBottom: 8 },
  share: { color: C.navy, fontSize: 13, fontWeight: "800" },
  progressTrack: { height: 9, borderRadius: 99, overflow: "hidden", backgroundColor: C.surfaceMuted, marginBottom: 10 },
  progressFill: { height: 9, backgroundColor: C.gold },
  progressOver: { backgroundColor: C.red },
  categoryRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 11 },
  categoryName: { color: C.secondary, fontSize: 14, flex: 1 },
  categoryAmount: { color: C.text, fontSize: 14, fontWeight: "800" },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 9 },
  infoLabel: { color: C.secondary, fontSize: 13 },
  infoValue: { color: C.text, fontSize: 13, fontWeight: "800" },
  primaryButton: { minHeight: 48, alignItems: "center", justifyContent: "center", borderRadius: 11, backgroundColor: C.navy, padding: 14, marginTop: 14 },
  primaryButtonText: { color: C.surface, fontSize: 13, fontWeight: "800" },
  secondaryButton: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  secondaryButtonText: { color: C.navy },
  actionButton: { minHeight: 46, alignItems: "center", justifyContent: "center", borderRadius: 11, backgroundColor: C.navy, padding: 13, marginTop: 12 },
  actionButtonText: { color: C.surface, fontSize: 13, fontWeight: "800" },
  disabled: { opacity: 0.5 },
  field: { marginTop: 13 },
  input: { minHeight: 48, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, paddingHorizontal: 13, color: C.text, fontSize: 14, marginTop: 7 },
  multiline: { minHeight: 82, paddingTop: 12 },
  readOnlyField: { minHeight: 48, justifyContent: "center", borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surfaceMuted, paddingHorizontal: 13, marginTop: 7 },
  readOnlyText: { color: C.secondary, fontSize: 14, fontWeight: "700" },
  categoryFormRow: { borderTopWidth: 1, borderTopColor: C.border, paddingTop: 8, marginTop: 10 },
  link: { color: C.navy, fontSize: 13, fontWeight: "800" },
  dangerLink: { color: C.red, fontSize: 13, fontWeight: "800", marginTop: 8 },
});
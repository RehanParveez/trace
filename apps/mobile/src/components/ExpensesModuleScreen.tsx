import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../api/client";
import {
  approveExpense,
  createExpense,
  getExpenseOrganizationSummary,
  getExpenseStatusSummary,
  listExpenses,
  rejectExpense,
} from "../api/expenses";
import { getOrganization } from "../api/organizations";
import { getProject, listProjects } from "../api/projects";
import type {
  AuthUser,
  Expense,
  ExpenseStatus,
  Project,
} from "../api/types";
import LanguageSwitcher from "./LanguageSwitcher";

const PAGE_SIZE = 100;
const STATUSES: Array<ExpenseStatus | "ALL"> = [
  "ALL",
  "PENDING",
  "APPROVED",
  "REJECTED",
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
  green: "#26734D",
  greenBg: "#E8F2E9",
  red: "#A33A32",
  redBg: "#F9E9E5",
};

function localDateString(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isValidDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;

  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const date = new Date(Date.UTC(year, month - 1, day));

  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function formatMoney(value: number | string, currency: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);

  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

export function ExpensesModuleScreen({ projectId }: { projectId?: string }) {
  const { t } = useTranslation();

  const [user, setUser] = useState<AuthUser | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectName, setProjectName] = useState("");
  const [currency, setCurrency] = useState("PKR");
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [statusTotals, setStatusTotals] = useState<
    Partial<Record<ExpenseStatus, number | string>>
  >({});
  const [organizationSummary, setOrganizationSummary] = useState<{
    total_approved_amount: number | string;
    expense_count: number;
  } | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [statusFilter, setStatusFilter] = useState<ExpenseStatus | "ALL">("ALL");
  const [error, setError] = useState("");

  const [selectedProjectId, setSelectedProjectId] = useState(projectId ?? "");
  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [expenseDate, setExpenseDate] = useState(localDateString());
  const [creating, setCreating] = useState(false);

  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  const canRead = permissions.includes("expense:read");
  const canCreate = permissions.includes("expense:create");
  const canApprove = permissions.includes("expense:approve");

  function readableStatus(status: ExpenseStatus): string {
    switch (status) {
      case "PENDING":
        return t("expenses.statusPending");
      case "APPROVED":
        return t("expenses.statusApproved");
      case "REJECTED":
        return t("expenses.statusRejected");
      default:
        return status;
    }
  }

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const currentUser = await restoreSession();
        if (!currentUser) {
          router.replace("/");
          return;
        }
        if (!active) return;

        setUser(currentUser);
        const granted = currentUser.role.permissions.map((item) => item.key);
        setPermissions(granted);

        if (!granted.includes("expense:read")) {
          setExpenses([]);
          setProjects([]);
          setLoading(false);
          return;
        }

        const [expenseRows, summary] = await Promise.all([
          listExpenses({
            project_id: projectId,
            status: statusFilter === "ALL" ? undefined : statusFilter,
            skip: 0,
            limit: PAGE_SIZE,
          }),
          getExpenseStatusSummary(projectId),
        ]);
        if (!active) return;

        setExpenses(expenseRows);
        setStatusTotals(summary.totals);

        const organization = await getOrganization();
        if (!active) return;
        setCurrency(organization.currency || "PKR");

        if (projectId) {
          const project = await getProject(projectId);
          if (!active) return;
          setProjectName(project.name);
          setProjects([project]);
          setSelectedProjectId(projectId);
          setOrganizationSummary(null);
        } else {
          const [projectRows, orgSummary] = await Promise.all([
            listProjects(),
            getExpenseOrganizationSummary(),
          ]);
          if (!active) return;
          setProjects(projectRows);
          setOrganizationSummary(orgSummary);
          setProjectName("");
          setSelectedProjectId((current) => current || projectRows[0]?.id || "");
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : t("expenses.loadFailure"),
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
  }, [projectId, statusFilter, attempt, t]);

  async function handleCreateExpense() {
    const amountValue = Number(amount);
    const targetProjectId = projectId || selectedProjectId;

    if (!targetProjectId) {
      setError(t("expenses.chooseProject"));
      return;
    }
    if (!category.trim() || category.trim().length > 150) {
      setError(t("expenses.categoryLength"));
      return;
    }
    if (!Number.isFinite(amountValue) || amountValue <= 0) {
      setError(t("expenses.amountGreaterThanZero"));
      return;
    }
    if (!isValidDate(expenseDate)) {
      setError(t("expenses.dateFormat"));
      return;
    }

    setCreating(true);
    setError("");

    try {
      await createExpense({
        project_id: targetProjectId,
        category: category.trim(),
        description: description.trim() || null,
        amount: amountValue,
        expense_date: expenseDate,
      });

      setCategory("");
      setDescription("");
      setAmount("");
      setExpenseDate(localDateString());
      setAttempt((value) => value + 1);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("expenses.createFailure"),
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleReview(expense: Expense, decision: "approve" | "reject") {
    if (!canApprove || expense.status !== "PENDING") return;

    setReviewingId(expense.id);
    setError("");

    try {
      const note = reviewNotes[expense.id]?.trim() || null;
      if (decision === "approve") {
        await approveExpense(expense.id, { note });
      } else {
        await rejectExpense(expense.id, { note });
      }
      setReviewNotes((current) => {
        const next = { ...current };
        delete next[expense.id];
        return next;
      });
      setAttempt((value) => value + 1);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("expenses.reviewFailure"),
      );
    } finally {
      setReviewingId(null);
    }
  }

  async function handleLoadMore() {
    if (!canRead || loadingMore || expenses.length < PAGE_SIZE) return;

    setLoadingMore(true);
    setError("");

    try {
      const nextPage = await listExpenses({
        project_id: projectId,
        status: statusFilter === "ALL" ? undefined : statusFilter,
        skip: expenses.length,
        limit: PAGE_SIZE,
      });
      setExpenses((current) => [...current, ...nextPage]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("expenses.loadMoreFailure"),
      );
    } finally {
      setLoadingMore(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={C.navy} />
        <Text style={styles.muted}>{t("expenses.loading")}</Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <Text style={styles.title}>{t("expenses.pageTitle")}</Text>
        <Text style={styles.error}>{t("expenses.accessDenied")}</Text>
      </View>
    );
  }

  const selectedProject = projects.find((item) => item.id === selectedProjectId);

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.headerRow}>
        <View style={styles.headerContent}>
          <Text style={styles.eyebrow}>
            {projectId
              ? t("expenses.eyebrowProject")
              : t("expenses.eyebrowWorkspace")}
          </Text>
          <Text style={styles.title}>
            {projectId
              ? t("expenses.projectExpenses", {
                  name: projectName || t("expenses.projectFallback"),
                })
              : t("expenses.pageTitle")}
          </Text>
        </View>
        <LanguageSwitcher />
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {!projectId && organizationSummary ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>{t("expenses.orgSummary")}</Text>
          <InfoRow
            label={t("expenses.approvedTotal")}
            value={formatMoney(
              organizationSummary.total_approved_amount,
              currency,
            )}
          />
          <InfoRow
            label={t("expenses.expenseRecords")}
            value={String(organizationSummary.expense_count)}
          />
        </View>
      ) : null}

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>{t("expenses.statusTotals")}</Text>
        {(["PENDING", "APPROVED", "REJECTED"] as ExpenseStatus[]).map(
          (status) => (
            <InfoRow
              key={status}
              label={readableStatus(status)}
              value={formatMoney(statusTotals[status] ?? 0, currency)}
            />
          ),
        )}
      </View>

      {canCreate ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>{t("expenses.recordExpense")}</Text>

          {!projectId ? (
            <>
              <Text style={styles.label}>{t("expenses.project")}</Text>
              <Pressable
                style={styles.input}
                onPress={() => setProjectPickerOpen(true)}
                accessibilityRole="button"
              >
                <Text
                  style={selectedProject ? styles.inputText : styles.muted}
                >
                  {selectedProject?.name ?? t("expenses.chooseAProject")}
                </Text>
              </Pressable>
            </>
          ) : null}

          <Text style={styles.label}>{t("expenses.category")}</Text>
          <TextInput
            style={styles.input}
            value={category}
            onChangeText={setCategory}
            maxLength={150}
            placeholder={t("expenses.categoryPlaceholder")}
            placeholderTextColor={C.muted}
          />

          <Text style={styles.label}>{t("expenses.descriptionOptional")}</Text>
          <TextInput
            style={[styles.input, styles.multiline]}
            value={description}
            onChangeText={setDescription}
            multiline
            placeholder={t("expenses.descriptionPlaceholder")}
            placeholderTextColor={C.muted}
          />

          <Text style={styles.label}>
            {t("expenses.amount", { currency })}
          </Text>
          <TextInput
            style={styles.input}
            value={amount}
            onChangeText={setAmount}
            keyboardType="decimal-pad"
            placeholder={t("expenses.amountPlaceholder")}
            placeholderTextColor={C.muted}
          />

          <Text style={styles.label}>{t("expenses.expenseDate")}</Text>
          <TextInput
            style={styles.input}
            value={expenseDate}
            onChangeText={setExpenseDate}
            autoCapitalize="none"
            placeholder={t("expenses.datePlaceholder")}
            placeholderTextColor={C.muted}
          />

          <ActionButton
            label={
              creating ? t("expenses.saving") : t("expenses.recordButton")
            }
            onPress={handleCreateExpense}
            disabled={creating}
          />
        </View>
      ) : null}

      <View style={styles.rowBetween}>
        <Text style={styles.sectionTitle}>{t("expenses.recordsSection")}</Text>
        <Pressable
          onPress={() => setAttempt((value) => value + 1)}
          accessibilityRole="button"
        >
          <Text style={styles.link}>{t("expenses.refresh")}</Text>
        </Pressable>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.filters}>
          {STATUSES.map((status) => (
            <Pressable
              key={status}
              onPress={() => setStatusFilter(status)}
              style={[
                styles.filter,
                statusFilter === status && styles.filterSelected,
              ]}
            >
              <Text
                style={[
                  styles.filterText,
                  statusFilter === status && styles.filterTextSelected,
                ]}
              >
                {status === "ALL"
                  ? t("expenses.statusAll")
                  : readableStatus(status)}
              </Text>
            </Pressable>
          ))}
        </View>
      </ScrollView>

      {expenses.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>{t("expenses.noMatch")}</Text>
        </View>
      ) : (
        expenses.map((expense) => {
          const expenseProject = projects.find(
            (item) => item.id === expense.project_id,
          );

          return (
            <View key={expense.id} style={styles.card}>
              <View style={styles.rowBetween}>
                <Text style={styles.sectionTitle}>{expense.category}</Text>
                <Text
                  style={[
                    styles.status,
                    expense.status === "APPROVED" && styles.statusApproved,
                    expense.status === "REJECTED" && styles.statusRejected,
                  ]}
                >
                  {readableStatus(expense.status)}
                </Text>
              </View>

              {!projectId ? (
                <InfoRow
                  label={t("expenses.project")}
                  value={expenseProject?.name ?? expense.project_id}
                />
              ) : null}
              <InfoRow
                label={t("expenses.amountLabel")}
                value={formatMoney(expense.amount, currency)}
              />
              <InfoRow
                label={t("expenses.dateLabel")}
                value={expense.expense_date}
              />

              {expense.description ? (
                <Text style={styles.bodyText}>{expense.description}</Text>
              ) : null}
              {expense.review_note ? (
                <Text style={styles.muted}>
                  {t("expenses.reviewNote", { note: expense.review_note })}
                </Text>
              ) : null}

              {canApprove && expense.status === "PENDING" ? (
                <View style={styles.reviewArea}>
                  <Text style={styles.label}>
                    {t("expenses.reviewNoteOptional")}
                  </Text>
                  <TextInput
                    style={[styles.input, styles.multiline]}
                    value={reviewNotes[expense.id] ?? ""}
                    onChangeText={(value) =>
                      setReviewNotes((current) => ({
                        ...current,
                        [expense.id]: value,
                      }))
                    }
                    multiline
                    placeholder={t("expenses.reviewNotePlaceholder")}
                    placeholderTextColor={C.muted}
                  />
                  <View style={styles.actions}>
                    <ActionButton
                      label={
                        reviewingId === expense.id
                          ? t("expenses.pleaseWait")
                          : t("expenses.approve")
                      }
                      onPress={() => void handleReview(expense, "approve")}
                      disabled={reviewingId !== null}
                    />
                    <ActionButton
                      label={t("expenses.reject")}
                      onPress={() => void handleReview(expense, "reject")}
                      disabled={reviewingId !== null}
                      secondary
                    />
                  </View>
                </View>
              ) : null}
            </View>
          );
        })
      )}

      {expenses.length >= PAGE_SIZE ? (
        <ActionButton
          label={
            loadingMore ? t("expenses.loadingMore") : t("expenses.loadMore")
          }
          onPress={() => void handleLoadMore()}
          disabled={loadingMore}
          secondary
        />
      ) : null}

      <Modal
        visible={projectPickerOpen}
        transparent
        animationType="slide"
        onRequestClose={() => setProjectPickerOpen(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.sectionTitle}>
              {t("expenses.chooseProjectModal")}
            </Text>
            <ScrollView>
              {projects.map((project) => (
                <Pressable
                  key={project.id}
                  style={styles.projectOption}
                  onPress={() => {
                    setSelectedProjectId(project.id);
                    setProjectPickerOpen(false);
                  }}
                >
                  <Text style={styles.bodyText}>{project.name}</Text>
                </Pressable>
              ))}
              {projects.length === 0 ? (
                <Text style={styles.muted}>{t("expenses.noProjects")}</Text>
              ) : null}
            </ScrollView>
            <ActionButton
              label={t("expenses.close")}
              onPress={() => setProjectPickerOpen(false)}
              secondary
            />
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.muted}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function ActionButton({
  label,
  onPress,
  disabled = false,
  secondary = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  secondary?: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.button,
        secondary && styles.secondaryButton,
        disabled && styles.disabled,
      ]}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
    >
      <Text
        style={[styles.buttonText, secondary && styles.secondaryButtonText]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: C.background },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 18 },
  headerContent: { flex: 1 },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4, textTransform: "uppercase" },
  title: { color: C.text, fontSize: 27, fontWeight: "800", marginTop: 5, letterSpacing: -0.4 },
  card: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, padding: 16, marginBottom: 12 },
  sectionTitle: { color: C.text, fontSize: 17, fontWeight: "800", marginBottom: 8 },
  label: { color: C.secondary, fontSize: 12, fontWeight: "700", marginTop: 13, marginBottom: 7 },
  input: { minHeight: 46, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, color: C.text, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14 },
  inputText: { color: C.text, fontSize: 14 },
  multiline: { minHeight: 78, textAlignVertical: "top" },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 9 },
  infoValue: { flex: 1, textAlign: "right", color: C.text, fontSize: 13, fontWeight: "700" },
  bodyText: { color: C.secondary, lineHeight: 20, marginTop: 8 },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19 },
  error: { color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19, marginBottom: 12 },
  link: { color: C.navy, fontSize: 13, fontWeight: "800" },
  status: { color: C.navy, backgroundColor: C.surfaceMuted, borderRadius: 99, overflow: "hidden", paddingHorizontal: 10, paddingVertical: 6, fontSize: 11, fontWeight: "800" },
  statusApproved: { color: C.green, backgroundColor: C.greenBg },
  statusRejected: { color: C.red, backgroundColor: C.redBg },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 8 },
  filters: { flexDirection: "row", gap: 8, paddingBottom: 12 },
  filter: { minHeight: 38, justifyContent: "center", borderWidth: 1, borderColor: C.border, borderRadius: 99, backgroundColor: C.surface, paddingHorizontal: 13, paddingVertical: 8 },
  filterSelected: { backgroundColor: C.navy, borderColor: C.navy },
  filterText: { color: C.secondary, fontSize: 12, fontWeight: "700" },
  filterTextSelected: { color: C.surface },
  reviewArea: { borderTopWidth: 1, borderTopColor: C.border, marginTop: 12, paddingTop: 4 },
  actions: { gap: 8, marginTop: 10 },
  button: { minHeight: 46, backgroundColor: C.navy, borderRadius: 11, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 12, marginTop: 10 },
  buttonText: { color: C.surface, fontSize: 13, fontWeight: "800", textAlign: "center" },
  secondaryButton: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border },
  secondaryButtonText: { color: C.navy },
  disabled: { opacity: 0.55 },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(8, 13, 24, 0.58)", justifyContent: "center", padding: 20 },
  modalCard: { maxHeight: "80%", backgroundColor: C.surface, borderRadius: 16, borderWidth: 1, borderColor: C.border, padding: 18 },
  projectOption: { paddingVertical: 13, borderBottomWidth: 1, borderBottomColor: C.border },
});
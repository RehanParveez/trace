import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../api/client";
import {getBudgetOrganizationSummary, listBudgetsByProject,
} from "../../../api/budgets";
import { listProjects } from "../../../api/projects";
import type {BudgetOrganizationSummary, BudgetProjectSummary, Project,
} from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

const PAGE_SIZE = 5;

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

export default function BudgetsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = i18n.resolvedLanguage || i18n.language;

  const [projects, setProjects] = useState<Project[]>([]);
  const [budgets, setBudgets] = useState<BudgetProjectSummary[]>([]);
  const [summary, setSummary] = useState<BudgetOrganizationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canRead, setCanRead] = useState<boolean | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      setPageNumber(1);

      try {
        const user = await restoreSession();

        if (!user) {
          router.replace("/");
          return;
        }

        const hasReadPermission = user.role.permissions.some(
          (permission) => permission.key === "budget:read",
        );

        if (!active) return;
        setCanRead(hasReadPermission);

        if (!hasReadPermission) {
          setProjects([]);
          setBudgets([]);
          setSummary(null);
          return;
        }

        const [projectRows, budgetRows, organizationSummary] =
          await Promise.all([
            listProjects(),
            listBudgetsByProject(),
            getBudgetOrganizationSummary(),
          ]);

        if (!active) return;
        setProjects(projectRows);
        setBudgets(budgetRows);
        setSummary(organizationSummary);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : t("budgets.loadFailure"),
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
  }, [attempt, t]);

  function openProject(projectId: string) {
    router.push({
      pathname: "/projects/[projectId]/budgets",
      params: { projectId },
    });
  }

  const budgetByProject = new Map(
    budgets.map((budget) => [budget.project_id, budget]),
  );

  const totalPages = Math.ceil(projects.length / PAGE_SIZE);
  const startIndex = (pageNumber - 1) * PAGE_SIZE;
  const visibleProjects = projects.slice(startIndex, startIndex + PAGE_SIZE);
  const visiblePages = Array.from(
    { length: totalPages },
    (_, index) => index + 1,
  ).filter((page) => Math.abs(page - pageNumber) <= 2);

  return (
    <ScrollView
      contentContainerStyle={[
        styles.page,
        isUrdu && styles.rtlPage,
      ]}
    >
      <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
        <Text style={styles.brand}>{t("budgets.brand")}</Text>
        <LanguageSwitcher />
      </View>

      <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
        {t("budgets.eyebrow")}
      </Text>
      <Text style={[styles.title, isUrdu && styles.rtlText]}>
        {t("budgets.pageTitle")}
      </Text>
      <Text style={[styles.subtitle, isUrdu && styles.rtlText]}>
        {t("budgets.subtitle")}
      </Text>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("budgets.loading")}
          </Text>
        </View>
      ) : error ? (
        <View style={styles.messageCard}>
          <Text style={[styles.error, isUrdu && styles.rtlText]}>
            {error}
          </Text>
          <Pressable
            style={styles.button}
            accessibilityRole="button"
            accessibilityLabel={t("budgets.tryAgain")}
            onPress={() => setAttempt((value) => value + 1)}
          >
            <Text style={styles.buttonText}>{t("budgets.tryAgain")}</Text>
          </Pressable>
        </View>
      ) : canRead === false ? (
        <View style={styles.messageCard}>
          <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
            {t("budgets.accessUnavailable")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("budgets.accessDenied")}
          </Text>
        </View>
      ) : projects.length === 0 ? (
        <View style={styles.messageCard}>
          <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
            {t("budgets.noProjectsTitle")}
          </Text>
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("budgets.noProjectsHelp")}
          </Text>
        </View>
      ) : (
        <>
          {summary ? (
            <View style={styles.summaryCard}>
              <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
                {t("budgets.organizationBudget")}
              </Text>
              <InfoRow
                label={t("budgets.approvedTotal")}
                value={money(
                  summary.total_approved_amount,
                  summary.currency,
                  locale,
                )}
                isUrdu={isUrdu}
              />
              <InfoRow
                label={t("budgets.projectsWithBudgets")}
                value={String(summary.budget_count)}
                isUrdu={isUrdu}
              />
            </View>
          ) : null}

          <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
            {t("budgets.projectBudgets")}
          </Text>

          {visibleProjects.map((project) => {
            const budget = budgetByProject.get(project.id);

            return (
              <Pressable
                key={project.id}
                style={styles.card}
                accessibilityRole="button"
                accessibilityLabel={t("budgets.openBudgetAccessibility", {
                  name: project.name,
                })}
                onPress={() => openProject(project.id)}
              >
                <View style={[styles.row, isUrdu && styles.rtlRow]}>
                  <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                    {project.name}
                  </Text>
                  <Text style={styles.arrow}>{isUrdu ? "‹" : "›"}</Text>
                </View>

                {project.code ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("budgets.code", { code: project.code })}
                  </Text>
                ) : null}

                <Text style={budget ? styles.budgetValue : styles.status}>
                  {budget
                    ? money(budget.approved_amount, budget.currency, locale)
                    : t("budgets.budgetNotSet")}
                </Text>
              </Pressable>
            );
          })}

          {totalPages > 1 ? (
            <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
              <Pressable
                style={[
                  styles.pageNavButton,
                  pageNumber === 1 && styles.disabled,
                ]}
                disabled={pageNumber === 1}
                onPress={() =>
                  setPageNumber((current) => Math.max(1, current - 1))
                }
                accessibilityRole="button"
              >
                <Text style={styles.pageNavText}>
                  {t("budgets.previousPage")}
                </Text>
              </Pressable>

              <View style={[styles.pageNumbers, isUrdu && styles.rtlRow]}>
                {visiblePages.map((page) => (
                  <Pressable
                    key={page}
                    style={[
                      styles.pageNumber,
                      page === pageNumber && styles.pageNumberSelected,
                    ]}
                    disabled={page === pageNumber}
                    onPress={() => setPageNumber(page)}
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
                  pageNumber === totalPages && styles.disabled,
                ]}
                disabled={pageNumber === totalPages}
                onPress={() =>
                  setPageNumber((current) =>
                    Math.min(totalPages, current + 1),
                  )
                }
                accessibilityRole="button"
              >
                <Text style={styles.pageNavText}>{t("budgets.nextPage")}</Text>
              </Pressable>
            </View>
          ) : null}
        </>
      )}
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
      <Text style={[styles.infoLabel, isUrdu && styles.rtlText]}>{label}</Text>
      <Text style={[styles.infoValue, isUrdu && styles.rtlText]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 20 },
  brand: { color: C.navy, fontSize: 16, fontWeight: "800" },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 28, fontWeight: "800", marginTop: 5, letterSpacing: -0.4 },
  subtitle: { color: C.secondary, fontSize: 14, lineHeight: 21, marginTop: 6, marginBottom: 8 },
  summaryCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 3, borderRadius: 15, padding: 16, marginTop: 18, marginBottom: 18 },
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: "800", marginTop: 18, marginBottom: 10 },
  card: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 2, borderRadius: 15, padding: 16, marginTop: 10 },
  messageCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 15, padding: 18, marginTop: 18 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10 },
  cardTitle: { color: C.text, fontSize: 16, fontWeight: "800", flexShrink: 1 },
  arrow: { color: C.muted, fontSize: 25 },
  budgetValue: { color: C.navy, fontSize: 15, fontWeight: "800", marginTop: 12 },
  status: { color: C.muted, fontSize: 13, fontWeight: "700", marginTop: 12 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 9 },
  infoLabel: { color: C.secondary, fontSize: 13, flex: 1 },
  infoValue: { color: C.text, fontSize: 13, fontWeight: "800", flex: 1, textAlign: "right" },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  error: { color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19 },
  center: { alignItems: "center", padding: 28, gap: 12 },
  button: { backgroundColor: C.navy, borderRadius: 11, paddingHorizontal: 14, paddingVertical: 13, alignItems: "center", marginTop: 16 },
  buttonText: { color: C.surface, fontSize: 13, fontWeight: "800" },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 16, padding: 10, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13 },
  pageNavButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: C.surfaceMuted },
  pageNavText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pageNumbers: { flexDirection: "row", alignItems: "center", gap: 5 },
  pageNumber: { minWidth: 36, height: 36, alignItems: "center", justifyContent: "center", borderRadius: 9, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  pageNumberSelected: { backgroundColor: C.navy, borderColor: C.navy },
  pageNumberText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  pageNumberTextSelected: { color: C.surface },
  disabled: { opacity: 0.45 },
});
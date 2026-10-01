import { useEffect, useState } from "react";
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { router } from "expo-router";
import { restoreSession } from "../../../api/client";
import { getBudgetOrganizationSummary, listBudgetsByProject } from "../../../api/budgets";
import { listProjects } from "../../../api/projects";
import type {BudgetOrganizationSummary, BudgetProjectSummary, Project,
} from "../../../api/types";

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

export default function BudgetsScreen() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [budgets, setBudgets] = useState<BudgetProjectSummary[]>([]);
  const [summary, setSummary] = useState<BudgetOrganizationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canRead, setCanRead] = useState<boolean | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");

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
            err instanceof Error ? err.message : "Could not load budgets.",
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
  }, [attempt]);

  function openProject(projectId: string) {
    router.push({
      pathname: "/projects/[projectId]/budgets",
      params: { projectId },
    });
  }

  const budgetByProject = new Map(
    budgets.map((budget) => [budget.project_id, budget]),
  );

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.brand}>Trace</Text>
      <Text style={styles.title}>Budgets</Text>
      <Text style={styles.subtitle}>
        Approved project budgets and category allocations.
      </Text>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#183153" />
          <Text style={styles.muted}>Loading budgets…</Text>
        </View>
      ) : error ? (
        <View style={styles.card}>
          <Text style={styles.error}>{error}</Text>
          <Pressable
            style={styles.button}
            accessibilityRole="button"
            onPress={() => setAttempt((value) => value + 1)}
          >
            <Text style={styles.buttonText}>Try again</Text>
          </Pressable>
        </View>
      ) : canRead === false ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Access unavailable</Text>
          <Text style={styles.muted}>
            Your role does not have permission to read budgets.
          </Text>
        </View>
      ) : projects.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>No projects available</Text>
          <Text style={styles.muted}>
            Create or join a project before setting its budget.
          </Text>
        </View>
      ) : (
        <>
          {summary ? (
            <View style={styles.summaryCard}>
              <Text style={styles.sectionTitle}>Organization budget</Text>
              <InfoRow
                label="Approved total"
                value={money(
                  summary.total_approved_amount,
                  summary.currency,
                )}
              />
              <InfoRow
                label="Projects with budgets"
                value={String(summary.budget_count)}
              />
            </View>
          ) : null}

          <Text style={styles.sectionTitle}>Project budgets</Text>

          {projects.map((project) => {
            const budget = budgetByProject.get(project.id);

            return (
              <Pressable
                key={project.id}
                style={styles.card}
                accessibilityRole="button"
                accessibilityLabel={`Open budget for ${project.name}`}
                onPress={() => openProject(project.id)}
              >
                <View style={styles.row}>
                  <Text style={styles.cardTitle}>{project.name}</Text>
                  <Text style={styles.arrow}>›</Text>
                </View>

                {project.code ? (
                  <Text style={styles.muted}>Code: {project.code}</Text>
                ) : null}

                <Text style={budget ? styles.budgetValue : styles.status}>
                  {budget
                    ? money(budget.approved_amount, budget.currency)
                    : "Budget not set"}
                </Text>
              </Pressable>
            );
          })}
        </>
      )}
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

const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 24, paddingTop: 30, paddingBottom: 40, backgroundColor: "#F4F6F8",},
  brand: { color: "#183153", fontSize: 16, fontWeight: "700" },
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginTop: 6,},
  subtitle: {color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 6,},
  summaryCard: {backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E4E7EC", borderRadius: 14, padding: 18, marginTop: 22,},
  sectionTitle: {color: "#17212F", fontSize: 18, fontWeight: "700", marginTop: 22, marginBottom: 10,},
  card: {backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E4E7EC", borderRadius: 14, padding: 18, marginTop: 10,},
  row: {flexDirection: "row", justifyContent: "space-between", alignItems: "center",},
  cardTitle: { color: "#17212F", fontSize: 16, fontWeight: "700" },
  arrow: { color: "#667085", fontSize: 25 },
  budgetValue: {color: "#183153", fontSize: 15, fontWeight: "700", marginTop: 12,},
  status: {color: "#667085", fontSize: 14, fontWeight: "600", marginTop: 12,},
  infoRow: {flexDirection: "row", justifyContent: "space-between", paddingVertical: 9, borderTopWidth: 1, borderTopColor: "#F0F2F5",},
  infoLabel: { color: "#667085", fontSize: 14 },
  infoValue: { color: "#17212F", fontWeight: "700" },
  muted: { color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 6 },
  error: { color: "#B42318", fontSize: 14, lineHeight: 20 },
  center: { alignItems: "center", padding: 28, gap: 12 },
  button: {backgroundColor: "#183153", borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16,},
  buttonText: { color: "#FFFFFF", fontWeight: "700" },
});
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getRunMetrics } from "../../../../api/runInsight";
import type { RunBudget, RunMetrics } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import {budgetLabel, fallbackReasonText, formatCount, formatDurationMs, formatMb, formatSeconds, percentOf, runFailureInfo,
} from "../../../../features/drawingsBoq/runInsightText";
import { usePolling } from "../../../../features/drawingsBoq/usePolling";
import { Action, Badge, COLORS, InfoRow, ui } from "../../../../features/drawingsBoq/ui";

const ACTIVE = new Set(["QUEUED", "RUNNING", "STAGED", "PROMOTED"]);

const COUNT_KEYS: [string, string, string][] = [
  ["elements", "insight.counts.elements", "Elements read"],
  ["accepted", "insight.counts.accepted", "Measured"],
  ["rejected", "insight.counts.rejected", "Rejected"],
  ["solids", "insight.counts.solids", "Solids"],
  ["ledger_rows", "insight.counts.ledger", "Ledger rows"],
  ["deductions", "insight.counts.deductions", "Deductions"],
  ["bar_marks", "insight.counts.barMarks", "Bar marks"],
  ["warnings", "insight.counts.warnings", "Warnings"],
];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function Bar({ pct, color }: { pct: number; color?: string }) {
  return (
    <View style={ui.progressTrack}>
      <View style={[ui.progressFill, { width: `${Math.max(2, Math.min(100, pct))}%`, backgroundColor: color ?? COLORS.navy }]} />
    </View>
  );
}

function budgetValue(unit: string, value: number | null) {
  if (value === null) return "—";
  return unit === "MB" ? formatMb(value) : formatSeconds(value);
}

export default function RunMetricsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; runId?: string }>();
  const runId = first(params.runId);

  const [metrics, setMetrics] = useState<RunMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!runId) return true;
    const next = await getRunMetrics(runId);
    setMetrics(next);
    setError("");
    return !ACTIVE.has(next.status);
  }, [runId]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }
        await load();
      } catch (err) {
        if (!cancelled) setError(describeError(err, tx("insight.metrics.loadFailure", "Could not load the run metrics.")));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };

  }, [load]);

  usePolling(load, !!metrics && ACTIVE.has(metrics.status), 4000);

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const a = metrics?.allocation ?? {};
  const stageTotal = (metrics?.stages ?? []).reduce((sum, s) => sum + (s.duration_ms ?? 0), 0);
  const failure = metrics?.failure ? runFailureInfo(tx, metrics.failure.code) : null;
  const fallback = fallbackReasonText(tx, a.fallback_reason);
  const total = Number(a.participating ?? 0);
  const reused = Number(a.reused ?? 0);
  const recomputed = Number(a.recompute ?? 0);

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("insight.metrics.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("insight.metrics.title", "Run metrics")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {metrics ? (
          <>
            <View style={ui.summaryBox}>
              <InfoRow label={tx("insight.metrics.status", "Status")} value={metrics.status} isUrdu={isUrdu} />
              <InfoRow
                label={tx("insight.metrics.mode", "Mode")}
                value={metrics.mode === "INCREMENTAL" ? tx("insight.metrics.partial", "Partial update") : tx("insight.metrics.full", "Full calculation")}
                isUrdu={isUrdu}
              />
              <InfoRow label={tx("insight.metrics.duration", "Total time")} value={formatDurationMs(metrics.duration_ms)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.metrics.memory", "Peak memory")} value={formatMb(metrics.peak_rss_mb)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.metrics.attempts", "Attempts")} value={String(metrics.attempts)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.metrics.engine", "Engine version")} value={metrics.engine_version} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.metrics.run", "Run")} value={metrics.run_id.slice(0, 8)} isUrdu={isUrdu} />
            </View>

            {failure && metrics.failure ? (
              <View style={ui.card}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{failure.title}</Text>
                <Text style={[ui.error, isUrdu && ui.rtlText]}>
                  {metrics.failure.stage
                    ? tx("insight.metrics.failedAt", "It stopped at the “{{stage}}” stage.", { stage: metrics.failure.stage })
                    : failure.hint}
                </Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{metrics.failure.message}</Text>
              </View>
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.metrics.limits", "Limits")}</Text>
            {metrics.budgets.length === 0 ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("insight.metrics.limitsPending", "Time and memory are checked against their limits once a run has completed.")}
              </Text>
            ) : (
              metrics.budgets.map((budget: RunBudget) => {
                const pct = percentOf(budget.actual ?? 0, budget.limit);
                return (
                  <View key={budget.name} style={ui.card}>
                    <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                      <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{budgetLabel(tx, budget.name)}</Text>
                      <Badge
                        label={
                          budget.ok === null
                            ? tx("insight.metrics.notMeasured", "Not measured")
                            : budget.ok
                              ? tx("insight.metrics.within", "Within limit")
                              : tx("insight.metrics.over", "Over limit")
                        }
                        tone={budget.ok === null ? "neutral" : budget.ok ? "good" : "bad"}
                      />
                    </View>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {`${budgetValue(budget.unit, budget.actual)} / ${budgetValue(budget.unit, budget.limit)}`}
                    </Text>
                    <Bar pct={pct} color={budget.ok === false ? COLORS.red : pct >= 80 ? COLORS.amber : COLORS.green} />
                  </View>
                );
              })
            )}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.metrics.allocation", "What was recalculated")}</Text>
            {metrics.mode !== "INCREMENTAL" ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {fallback ?? tx("insight.metrics.fullAll", "Every element was calculated in this run.")}
              </Text>
            ) : (
              <View style={ui.card}>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("insight.metrics.reusedSummary", "{{reused}} of {{total}} elements reused from the earlier run; {{recomputed}} recalculated.", {
                    reused: formatCount(reused),
                    total: formatCount(total),
                    recomputed: formatCount(recomputed),
                  })}
                </Text>
                <Bar pct={total > 0 ? (reused / total) * 100 : 0} color={COLORS.green} />
                <InfoRow label={tx("insight.metrics.added", "New elements")} value={formatCount(a.added ?? 0)} isUrdu={isUrdu} />
                <InfoRow label={tx("insight.metrics.modified", "Changed elements")} value={formatCount(a.modified ?? 0)} isUrdu={isUrdu} />
                <InfoRow label={tx("insight.metrics.removed", "Removed elements")} value={formatCount(a.removed ?? 0)} isUrdu={isUrdu} />
                <InfoRow
                  label={tx("insight.metrics.neighbours", "Recalculated as neighbours")}
                  value={formatCount(a.affected_by_neighbourhood ?? 0)}
                  isUrdu={isUrdu}
                />
                {Number(a.order_flips ?? 0) + Number(a.remap_misses ?? 0) > 0 ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {tx(
                      "insight.metrics.extra",
                      "{{flips}} recalculated because the order of overlapping elements changed, {{misses}} because their earlier result could not be carried over.",
                      { flips: formatCount(a.order_flips ?? 0), misses: formatCount(a.remap_misses ?? 0) },
                    )}
                  </Text>
                ) : null}
              </View>
            )}
            {metrics.baseline_run_id ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("insight.metrics.baseline", "Built on run {{id}}", { id: metrics.baseline_run_id.slice(0, 8) })}
              </Text>
            ) : null}

            {metrics.verify ? (
              <>
                <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.metrics.verify", "Check against a full calculation")}</Text>
                <Badge
                  label={
                    metrics.verify.matched
                      ? tx("insight.metrics.verifyMatched", "Identical to the full calculation")
                      : tx("insight.metrics.verifyMismatch", "Differences found, full result kept")
                  }
                  tone={metrics.verify.matched ? "good" : "bad"}
                />
                {!metrics.verify.matched
                  ? (metrics.verify.problems ?? []).map((problem, index) => (
                      <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{String(problem)}</Text>
                    ))
                  : null}
              </>
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.metrics.stages", "Time and memory by stage")}</Text>
            {metrics.stages.length === 0 ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("insight.metrics.noStages", "No stage timings recorded yet.")}</Text>
            ) : (
              metrics.stages.map((stage) => {
                const share = stageTotal > 0 && stage.duration_ms !== null ? (stage.duration_ms / stageTotal) * 100 : 0;
                return (
                  <View key={stage.stage} style={ui.boqItem}>
                    <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                      <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{stage.stage.replaceAll("_", " ")}</Text>
                      <Text style={[ui.muted, isUrdu && ui.rtlText]}>{stage.status}</Text>
                    </View>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {`${formatDurationMs(stage.duration_ms)} · ${formatMb(stage.peak_rss_mb)}`}
                    </Text>
                    <Bar pct={share} />
                  </View>
                );
              })
            )}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.metrics.counts", "What the run produced")}</Text>
            <View style={ui.summaryBox}>
              {COUNT_KEYS.filter(([key]) => metrics.counts[key] !== undefined).map(([key, i18nKey, label]) => (
                <InfoRow key={key} label={tx(i18nKey, label)} value={formatCount(metrics.counts[key])} isUrdu={isUrdu} />
              ))}
            </View>

            <Action
              title={tx("insight.metrics.refresh", "Refresh")}
              secondary
              isUrdu={isUrdu}
              onPress={() => void load().catch((err) => setError(describeError(err, tx("insight.metrics.loadFailure", "Could not load the run metrics."))))}
            />
          </>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
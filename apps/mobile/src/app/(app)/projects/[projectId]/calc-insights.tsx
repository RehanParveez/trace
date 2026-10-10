import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getCalcUsage, getOrgMetrics } from "../../../../api/runInsight";
import type { CalcUsage, OrgCalcMetrics } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import {formatCount, formatSeconds, formatShare, formatWindow, percentOf,
} from "../../../../features/drawingsBoq/runInsightText";
import { Action, COLORS, InfoRow, ui } from "../../../../features/drawingsBoq/ui";

const WINDOWS = [7, 30, 90];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <View style={ui.progressTrack}>
      <View style={[ui.progressFill, { width: `${Math.max(2, Math.min(100, pct))}%`, backgroundColor: color }]} />
    </View>
  );
}

function usageColor(pct: number) {
  return pct >= 100 ? COLORS.red : pct >= 80 ? COLORS.amber : COLORS.green;
}

export default function CalcInsightsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [days, setDays] = useState(30);
  const [metrics, setMetrics] = useState<OrgCalcMetrics | null>(null);
  const [usage, setUsage] = useState<CalcUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (window: number) => {
    setLoading(true);
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      const [m, u] = await Promise.all([getOrgMetrics(window), getCalcUsage()]);
      setMetrics(m);
      setUsage(u);
      setError("");
    } catch (err) {
      setError(describeError(err, tx("insight.org.loadFailure", "Could not load calculation insights.")));
    } finally {
      setLoading(false);
    }

  }, []);

  useEffect(() => {
    void load(days);
  }, [days, load]);

  const quota = usage?.quota ?? null;
  const quotaPct = quota ? percentOf(quota.used, quota.limit) : 0;
  const concurrentPct = usage ? percentOf(usage.concurrent.active, usage.concurrent.limit) : 0;

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("insight.org.back", "Back to drawings & BOQ")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("insight.org.title", "Calculation insights")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {WINDOWS.map((value) => (
            <Action
              key={value}
              title={tx("insight.org.days", "{{count}} days", { count: value })}
              secondary={days !== value}
              isUrdu={isUrdu}
              onPress={() => setDays(value)}
            />
          ))}
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {loading ? <ActivityIndicator color={COLORS.navy} /> : null}

        {usage ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.org.usage", "Plan usage")}</Text>
            <View style={ui.card}>
              <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("insight.org.quota", "Calculation runs in your plan")}</Text>
              {quota ? (
                <>
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {quota.limit === null
                      ? tx("insight.org.quotaUnlimited", "{{used}} used. No limit on your plan.", { used: formatCount(quota.used) })
                      : tx("insight.org.quotaLimited", "{{used}} of {{limit}} used, {{left}} left.", {
                          used: formatCount(quota.used),
                          limit: formatCount(quota.limit),
                          left: formatCount(quota.remaining ?? 0),
                        })}
                  </Text>
                  {quota.limit !== null ? <Bar pct={quotaPct} color={usageColor(quotaPct)} /> : null}
                </>
              ) : (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("insight.org.noQuota", "No plan limit is set.")}</Text>
              )}
            </View>

            <View style={ui.card}>
              <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("insight.org.concurrent", "Running at the same time")}</Text>
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {usage.concurrent.limit > 0
                  ? tx("insight.org.concurrentLimited", "{{active}} of {{limit}} allowed.", {
                      active: usage.concurrent.active,
                      limit: usage.concurrent.limit,
                    })
                  : tx("insight.org.concurrentOpen", "{{active}} running. No limit.", { active: usage.concurrent.active })}
              </Text>
              {usage.concurrent.limit > 0 ? <Bar pct={concurrentPct} color={usageColor(concurrentPct)} /> : null}
            </View>

            {usage.rate_limits.length > 0 ? (
              <View style={ui.card}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("insight.org.rate", "Start rate limits")}</Text>
                {usage.rate_limits.map((win) => (
                  <InfoRow
                    key={win.window_seconds}
                    label={tx("insight.org.rateWindow", "Per {{window}}", { window: formatWindow(win.window_seconds) })}
                    value={tx("insight.org.rateValue", "{{used}} of {{limit}}, resets in {{reset}}", {
                      used: win.used,
                      limit: win.limit,
                      reset: formatSeconds(win.resets_in_seconds),
                    })}
                    isUrdu={isUrdu}
                  />
                ))}
              </View>
            ) : null}
          </>
        ) : null}

        {metrics ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>
              {tx("insight.org.last", "Last {{count}} days", { count: metrics.window_days })}
            </Text>
            <View style={ui.summaryBox}>
              <InfoRow label={tx("insight.org.runs", "Runs")} value={formatCount(metrics.runs_total)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.org.active", "Running now")} value={formatCount(metrics.active_now)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.org.elements", "Elements processed")} value={formatCount(metrics.elements_processed)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.org.warnings", "Warnings raised")} value={formatCount(metrics.warnings_total)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.org.partial", "Finished as partial updates")} value={formatShare(metrics.incremental_share)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.org.p50", "Typical time (median)")} value={formatSeconds(metrics.duration_seconds.p50)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.org.p95", "Slow runs (95th percentile)")} value={formatSeconds(metrics.duration_seconds.p95)} isUrdu={isUrdu} />
              <InfoRow label={tx("insight.org.max", "Longest")} value={formatSeconds(metrics.duration_seconds.max)} isUrdu={isUrdu} />
            </View>

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.org.byStatus", "Runs by outcome")}</Text>
            <View style={ui.summaryBox}>
              {Object.entries(metrics.runs_by_status).map(([status, count]) => (
                <InfoRow key={status} label={status} value={formatCount(count)} isUrdu={isUrdu} />
              ))}
              {Object.keys(metrics.runs_by_status).length === 0 ? (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("insight.org.noRuns", "No runs in this period.")}</Text>
              ) : null}
            </View>

            {Object.keys(metrics.failure_codes).length > 0 ? (
              <>
                <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.org.failures", "Why runs failed")}</Text>
                <View style={ui.summaryBox}>
                  {Object.entries(metrics.failure_codes).map(([code, count]) => (
                    <InfoRow key={code} label={code} value={formatCount(count)} isUrdu={isUrdu} />
                  ))}
                </View>
              </>
            ) : null}

            {metrics.slowest_runs.length > 0 ? (
              <>
                <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("insight.org.slowest", "Slowest runs")}</Text>
                {metrics.slowest_runs.map((run) => (
                  <Pressable
                    key={run.run_id}
                    style={ui.boqItem}
                    onPress={() =>
                      router.push({
                        pathname: "/projects/[projectId]/run-metrics",
                        params: { projectId: run.project_id || projectId || "", runId: run.run_id },
                      })
                    }
                  >
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                      {`${formatSeconds(run.duration_seconds)} · ${run.mode === "INCREMENTAL" ? tx("insight.org.modePartial", "Partial") : tx("insight.org.modeFull", "Full")}`}
                    </Text>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {tx("insight.org.slowestRow", "{{elements}} elements · run {{id}}. Tap for details.", {
                        elements: formatCount(run.elements),
                        id: run.run_id.slice(0, 8),
                      })}
                    </Text>
                  </Pressable>
                ))}
              </>
            ) : null}
          </>
        ) : null}

        <Action
          title={tx("insight.org.refresh", "Refresh")}
          secondary
          isUrdu={isUrdu}
          onPress={() => void load(days)}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
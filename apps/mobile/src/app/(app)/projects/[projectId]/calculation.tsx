import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Switch, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {buildBoqFromRun, getCalculationRun, listProjectCalculationRuns, listRunStages, startCalculationRun,
} from "../../../../api/boqEngine";
import type { CalculationRun, RunStage } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { usePolling } from "../../../../features/drawingsBoq/usePolling";
import {classifyStartError, runFailureInfo, startErrorGuidance,
  type StartRunError,
} from "../../../../features/drawingsBoq/runInsightText";
import { Action, Badge, COLORS, InfoRow, ui } from "../../../../features/drawingsBoq/ui";

const TERMINAL = new Set(["COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED"]);

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function CalculationScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [run, setRun] = useState<CalculationRun | null>(null);
  const [stages, setStages] = useState<RunStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [waitedForBoq, setWaitedForBoq] = useState(0);
  const [forceFull, setForceFull] = useState(false);
  const [verify, setVerify] = useState(false);
  const [startError, setStartError] = useState<StartRunError | null>(null);
  const [reusedNotice, setReusedNotice] = useState(false);

  const canRun = hasPerm(permissions, PERM.CALC_RUN);
  const boqStats = run?.stats?.boq as Record<string, string> | undefined;
  const boqError = run?.stats?.boq_error as string | undefined;
  const runDone = run ? TERMINAL.has(run.status) : false;
  const waitingForBoq =
    run?.status === "COMPLETED" && !boqStats && !boqError && waitedForBoq < 20;
  const polling = !!run && (!runDone || waitingForBoq);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      if (!projectId) {
        setError(tx("calculation.projectMissing", "Project not found."));
        setLoading(false);
        return;
      }
      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }
        if (cancelled) return;
        setPermissions(user.role.permissions.map((p) => p.key));

        try {
          const runs = await listProjectCalculationRuns(projectId, 1);
          if (!cancelled && runs.length > 0) {
            setRun(runs[0]);
            setStages(await listRunStages(runs[0].id));
          }
        } catch {
        }
      } catch (err) {
        if (!cancelled) setError(describeError(err, tx("calculation.loadFailure", "Could not load.")));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const refresh = useCallback(async () => {
    if (!run) return true;
    const [next, nextStages] = await Promise.all([
      getCalculationRun(run.id),
      listRunStages(run.id),
    ]);
    setRun(next);
    setStages(nextStages);
    if (next.status === "COMPLETED") {
      setWaitedForBoq((count) => count + 1);
    }
    const done = TERMINAL.has(next.status);
    const boqReady = !!next.stats?.boq || !!next.stats?.boq_error;
    return done && (next.status !== "COMPLETED" || boqReady);
  }, [run]);

  usePolling(refresh, polling, 3000);

  async function handleStart() {
    if (!projectId) return;
    setBusy(true);
    setError("");
    setWaitedForBoq(0);
    try {
      setStartError(null);
      setReusedNotice(false);
      const started = await startCalculationRun(projectId, {
        force_full: forceFull,
        verify: verify && !forceFull,
      });
      if (started.status === "COMPLETED") setReusedNotice(true);
      setRun(started);
      setStages(await listRunStages(started.id));
    } catch (err) {
      setStartError(classifyStartError(err, tx("calculation.startFailure", "Could not start the calculation.")));
    } finally {
      setBusy(false);
    }
  }

  async function handleRebuild() {
    if (!run) return;
    setBusy(true);
    setError("");
    try {
      await buildBoqFromRun(run.id);
      setRun(await getCalculationRun(run.id));
    } catch (err) {
      setError(describeError(err, tx("calculation.buildFailure", "Could not build the BOQ.")));
    } finally {
      setBusy(false);
    }
  }

  function openBoq(versionId: string) {
    if (!projectId) return;
    router.replace({
      pathname: "/projects/[projectId]/boq-version",
      params: { projectId, versionId },
    });
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>
                {tx("calculation.back", "Back to drawings & BOQ")}
              </Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>
              {tx("calculation.title", "Calculation")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {canRun ? (
          <View style={ui.card}>
            <View style={[ui.heading, isUrdu && ui.rtlRow]}>
              <View style={ui.headerCopy}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                  {tx("calculation.forceFull", "Recalculate everything")}
                </Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx(
                    "calculation.forceFullHint",
                    "Normally a run reuses the earlier result for elements that did not change. Turn this on to calculate every element again.",
                  )}
                </Text>
              </View>
              <Switch value={forceFull} onValueChange={(value) => { setForceFull(value); if (value) setVerify(false); }} />
            </View>
            <View style={[ui.heading, isUrdu && ui.rtlRow]}>
              <View style={ui.headerCopy}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                  {tx("calculation.verify", "Check against a full calculation")}
                </Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx(
                    "calculation.verifyHint",
                    "After a partial update, also run the full calculation and compare. Slower. If they differ, the full result is kept.",
                  )}
                </Text>
              </View>
              <Switch value={verify && !forceFull} disabled={forceFull} onValueChange={setVerify} />
            </View>
          </View>
        ) : null}

        {reusedNotice ? (
          <Text style={[ui.notice, isUrdu && ui.rtlText]}>
            {tx(
              "calculation.reused",
              "Nothing changed since the last calculation, so its result is shown. Turn on “Recalculate everything” to run it again.",
            )}
          </Text>
        ) : null}

        {startError ? (
          <View style={ui.card}>
            <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
              {startErrorGuidance(tx, startError.kind).title}
            </Text>
            {startErrorGuidance(tx, startError.kind).hint ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>{startErrorGuidance(tx, startError.kind).hint}</Text>
            ) : null}
            {startError.message ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{startError.message}</Text> : null}
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {startError.retryable ? (
                <Action
                  title={tx("calculation.tryAgain", "Try again")}
                  secondary
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => void handleStart()}
                />
              ) : null}
              <Action
                title={tx("calculation.dismiss", "Dismiss")}
                secondary
                isUrdu={isUrdu}
                onPress={() => setStartError(null)}
              />
            </View>
          </View>
        ) : null}

        {canRun ? (
          <Action
            title={
              run && !runDone
                ? tx("calculation.running", "Calculation in progress")
                : tx("calculation.start", "Start calculation")
            }
            disabled={busy || (!!run && !runDone)}
            isUrdu={isUrdu}
            onPress={() => void handleStart()}
          />
        ) : (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("calculation.noPermission", "You do not have permission to start calculations.")}
          </Text>
        )}

        {run ? (
          <View style={ui.card}>
            <View style={[ui.heading, isUrdu && ui.rtlRow]}>
              <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                {tx(`calculation.status.${run.status.toLowerCase()}`, run.status)}
              </Text>
              <Badge
                label={`${Math.round(run.progress_pct)}%`}
                tone={
                  run.status === "FAILED"
                    ? "bad"
                    : run.status === "COMPLETED"
                      ? "good"
                      : "warn"
                }
              />
            </View>

            <View style={ui.progressTrack}>
              <View style={[ui.progressFill, { width: `${Math.max(2, Math.min(100, run.progress_pct))}%` }]} />
            </View>

            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Badge
                label={
                  run.mode === "INCREMENTAL"
                    ? tx("calculation.modeIncremental", "Partial update")
                    : tx("calculation.modeFull", "Full calculation")
                }
                tone={run.mode === "INCREMENTAL" ? "good" : "neutral"}
              />
              {run.attempts && run.attempts > 1 ? (
                <Badge label={tx("calculation.attempts", "Tried {{count}} times", { count: run.attempts })} tone="warn" />
              ) : null}
            </View>

            {run.status === "FAILED" ? (
              <>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{runFailureInfo(tx, run.error_code).title}</Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{runFailureInfo(tx, run.error_code).hint}</Text>
                {run.error_code ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{run.error_code}</Text> : null}
              </>
            ) : null}

            {run.error_message ? (
              <Text style={[ui.error, isUrdu && ui.rtlText]}>{run.error_message}</Text>
            ) : null}

            {run.status === "FAILED" && canRun && runFailureInfo(tx, run.error_code).retry ? (
              <Action
                title={tx("calculation.runAgain", "Run again")}
                secondary
                disabled={busy}
                isUrdu={isUrdu}
                onPress={() => void handleStart()}
              />
            ) : null}

            <Action
              title={tx("calculation.metrics", "Run metrics")}
              secondary
              isUrdu={isUrdu}
              onPress={() =>
                router.push({
                  pathname: "/projects/[projectId]/run-metrics",
                  params: { projectId: run.project_id, runId: run.id },
                })
              }
            />

            {stages.length > 0 ? (
              <View style={ui.summaryBox}>
                {stages.map((stage) => (
                  <InfoRow
                    key={stage.stage}
                    label={stage.stage.replaceAll("_", " ")}
                    value={stage.status}
                    isUrdu={isUrdu}
                  />
                ))}
              </View>
            ) : null}

            {waitingForBoq ? (
              <View style={ui.busy}>
                <ActivityIndicator color={COLORS.navy} />
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("calculation.buildingBoq", "Building the BOQ…")}
                </Text>
              </View>
            ) : null}

            {boqStats ? (
              <>
                <View style={ui.summaryBox}>
                  <InfoRow label={tx("calculation.created", "Items created")} value={String(boqStats.items_created ?? "0")} isUrdu={isUrdu} />
                  <InfoRow label={tx("calculation.updated", "Items updated")} value={String(boqStats.items_updated ?? "0")} isUrdu={isUrdu} />
                  <InfoRow label={tx("calculation.openIssues", "Open review issues")} value={String(boqStats.open_issues ?? "0")} isUrdu={isUrdu} />
                </View>
                {boqStats.boq_version_id ? (
                  <Action
                    title={tx("calculation.openBoq", "Open BOQ")}
                    isUrdu={isUrdu}
                    onPress={() => openBoq(String(boqStats.boq_version_id))}
                  />
                ) : null}
              </>
            ) : null}

            {boqError ? (
              <>
                <Text style={[ui.error, isUrdu && ui.rtlText]}>{boqError}</Text>
                {canRun ? (
                  <Action
                    title={tx("calculation.retryBuild", "Retry BOQ build")}
                    secondary
                    disabled={busy}
                    isUrdu={isUrdu}
                    onPress={() => void handleRebuild()}
                  />
                ) : null}
              </>
            ) : null}
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
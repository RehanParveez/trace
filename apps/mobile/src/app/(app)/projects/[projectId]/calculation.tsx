import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
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
      const started = await startCalculationRun(projectId);
      setRun(started);
      setStages(await listRunStages(started.id));
    } catch (err) {
      setError(describeError(err, tx("calculation.startFailure", "Could not start the calculation.")));
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

            {run.error_message ? (
              <Text style={[ui.error, isUrdu && ui.rtlText]}>{run.error_message}</Text>
            ) : null}

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
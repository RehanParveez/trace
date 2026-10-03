import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from "react-native";
import { router, Stack, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../api/client";
import {bulkRecordLabourAttendance, createLabourAdvance, createLabourDeployment, createLabourPayment, createLabourSource, createLabourWorker, getLabourBalance, getLabourDaySummary, getLabourSummary, listLabourAdvances,
  listLabourAttendance, listLabourDeployments, listLabourPayments, listLabourSources, listLabourWorkers, updateLabourDeployment, updateLabourSource, updateLabourWorker,
} from "../api/labour";
import { getProject } from "../api/projects";
import type {LabourAdvance, LabourDayAttendanceSummary, LabourDeployment, LabourPayment, LabourSource, LabourSourceType, LabourSummary, LabourWhtCategory, LabourWorker, Project,
} from "../api/types";
import LanguageSwitcher from "./LanguageSwitcher";

const C = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#FBF8F2",
  navy: "#080D18",
  navySoft: "#18283B",
  gold: "#D9A441",
  goldDark: "#B98626",
  text: "#191410",
  secondary: "#5C5347",
  muted: "#8C806E",
  border: "#E4D9C4",
  borderStrong: "#D4C7AD",
  green: "#24744A",
  greenBg: "#EAF4EC",
  amber: "#8A5A0A",
  amberBg: "#FFF3D8",
  red: "#A33C32",
  redBg: "#FBECE9",
} as const;

type Section =
  | "directory"
  | "overview"
  | "deployments"
  | "attendance"
  | "finance";

type SourceForm = {
  id?: string;
  name: string;
  source_type: LabourSourceType;
  contact_name: string;
  contact_phone: string;
  is_active_taxpayer: boolean;
  notes: string;
  is_active: boolean;
};

type WorkerForm = {
  id?: string;
  source_id: string;
  name: string;
  trade: string;
  cnic: string;
  phone: string;
  default_daily_rate: string;
  is_active: boolean;
};

const today = () => {
  const date = new Date();
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
};

const firstOfMonth = () => `${today().slice(0, 7)}-01`;

function permissionsFor(user: Awaited<ReturnType<typeof restoreSession>>) {
  return user?.role?.permissions?.map((permission) => permission.key) ?? [];
}

export function LabourScreen({ section }: { section: Section }) {
  const { t } = useTranslation();
  const params = useLocalSearchParams<{ projectId?: string | string[] }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [permissions, setPermissions] = useState<string[]>([]);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [project, setProject] = useState<Project | null>(null);
  const [sources, setSources] = useState<LabourSource[]>([]);
  const [workers, setWorkers] = useState<LabourWorker[]>([]);
  const [deployments, setDeployments] = useState<LabourDeployment[]>([]);
  const [attendance, setAttendance] = useState<
    Awaited<ReturnType<typeof listLabourAttendance>>
  >([]);
  const [daySummary, setDaySummary] = useState<LabourDayAttendanceSummary | null>(
    null
  );
  const [advances, setAdvances] = useState<LabourAdvance[]>([]);
  const [payments, setPayments] = useState<LabourPayment[]>([]);
  const [summary, setSummary] = useState<LabourSummary | null>(null);
  const [balance, setBalance] = useState<number | string | null>(null);

  const [periodStart, setPeriodStart] = useState(firstOfMonth);
  const [periodEnd, setPeriodEnd] = useState(today);
  const [attendanceDate, setAttendanceDate] = useState(today);
  const [attendanceValues, setAttendanceValues] = useState<Record<string, string>>({});

  const [sourceModal, setSourceModal] = useState(false);
  const [workerModal, setWorkerModal] = useState(false);
  const [sourceForm, setSourceForm] = useState<SourceForm | null>(null);
  const [workerForm, setWorkerForm] = useState<WorkerForm | null>(null);

  const [sourceId, setSourceId] = useState("");
  const [workerId, setWorkerId] = useState("");
  const [trade, setTrade] = useState("");
  const [dailyRate, setDailyRate] = useState("");
  const [deploymentStartDate, setDeploymentStartDate] = useState(today);

  const [advanceAmount, setAdvanceAmount] = useState("");
  const [advanceDate, setAdvanceDate] = useState(today);
  const [advanceNotes, setAdvanceNotes] = useState("");

  const [paymentPeriodStart, setPaymentPeriodStart] = useState("");
  const [paymentPeriodEnd, setPaymentPeriodEnd] = useState(today);
  const [grossWage, setGrossWage] = useState("");
  const [advanceRecovery, setAdvanceRecovery] = useState("0");
  const [paymentDate, setPaymentDate] = useState(today);
  const [whtCategory, setWhtCategory] = useState<LabourWhtCategory | "">("");
  const [paymentNotes, setPaymentNotes] = useState("");
  const [lastPayment, setLastPayment] = useState<LabourPayment | null>(null);

  const canRead = permissions.includes("labour:read");
  const canManage = permissions.includes("labour:manage");
  const canManagePayments = permissions.includes("labour:payment_manage");

  const titleKey =
    section === "directory"
      ? "labour.directoryTitle"
      : section === "overview"
      ? "labour.overviewTitle"
      : section === "deployments"
      ? "labour.deploymentsTitle"
      : section === "attendance"
      ? "labour.attendanceTitle"
      : "labour.financeTitle";

  const title = t(titleKey);

  const load = useCallback(
    async (refresh = false) => {
      if (refresh) setRefreshing(true);
      else setLoading(true);
      setError("");

      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }

        const granted = permissionsFor(user);
        setPermissions(granted);
        setSessionChecked(true);

        if (!granted.includes("labour:read")) return;

        if (section === "directory") {
          const [sourceRows, workerRows] = await Promise.all([
            listLabourSources(),
            listLabourWorkers(),
          ]);
          setSources(sourceRows);
          setWorkers(workerRows);
          return;
        }

        if (!projectId) {
          setError(t("labour.projectIdMissing"));
          return;
        }

        const projectResult = await getProject(projectId);
        setProject(projectResult);

        if (section === "overview") {
          setSummary(await getLabourSummary(projectId, periodStart, periodEnd));
          return;
        }

        if (section === "deployments") {
          const [sourceRows, workerRows, deploymentRows] = await Promise.all([
            listLabourSources(),
            listLabourWorkers(),
            listLabourDeployments(projectId),
          ]);
          setSources(sourceRows);
          setWorkers(workerRows);
          setDeployments(deploymentRows);
          return;
        }

        if (section === "attendance") {
          const [deploymentRows, attendanceRows, day] = await Promise.all([
            listLabourDeployments(projectId),
            listLabourAttendance(projectId, attendanceDate, attendanceDate),
            getLabourDaySummary(projectId, attendanceDate),
          ]);
          setDeployments(deploymentRows);
          setAttendance(attendanceRows);
          setDaySummary(day);

          const existingValues: Record<string, string> = {};
          attendanceRows.forEach((record) => {
            existingValues[record.deployment_id] = String(record.units_present);
          });
          setAttendanceValues(existingValues);
          return;
        }

        const [sourceRows, advanceRows, paymentRows, summaryResult] =
          await Promise.all([
            listLabourSources(),
            listLabourAdvances(projectId),
            listLabourPayments(projectId),
            getLabourSummary(projectId, periodStart, periodEnd),
          ]);
        setSources(sourceRows);
        setAdvances(advanceRows);
        setPayments(paymentRows);
        setSummary(summaryResult);

        const selectedSource =
          sourceRows.find((source) => source.id === sourceId && source.is_active) ??
          sourceRows.find((source) => source.is_active);

        if (selectedSource) {
          setSourceId(selectedSource.id);
          const result = await getLabourBalance(projectId, selectedSource.id);
          setBalance(result.outstanding_advance_balance);
        } else {
          setBalance(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t("labour.loadFailure"));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [section, projectId, periodStart, periodEnd, attendanceDate, sourceId, t]
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("labour.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  function openNewSource() {
    setSourceForm({
      name: "",
      source_type: "CONTRACTOR",
      contact_name: "",
      contact_phone: "",
      is_active_taxpayer: false,
      notes: "",
      is_active: true,
    });
    setSourceModal(true);
  }

  function openEditSource(source: LabourSource) {
    setSourceForm({
      id: source.id,
      name: source.name,
      source_type: source.source_type,
      contact_name: source.contact_name ?? "",
      contact_phone: source.contact_phone ?? "",
      is_active_taxpayer: source.is_active_taxpayer,
      notes: source.notes ?? "",
      is_active: source.is_active,
    });
    setSourceModal(true);
  }

  async function saveSource() {
    if (!sourceForm?.name.trim()) {
      setError(t("labour.sourceNameRequired"));
      return;
    }

    const payload = {
      name: sourceForm.name.trim(),
      contact_name: sourceForm.contact_name.trim() || null,
      contact_phone: sourceForm.contact_phone.trim() || null,
      is_active_taxpayer: sourceForm.is_active_taxpayer,
      notes: sourceForm.notes.trim() || null,
      is_active: sourceForm.is_active,
    };

    await run(async () => {
      if (sourceForm.id) {
        await updateLabourSource(sourceForm.id, payload);
      } else {
        await createLabourSource({
          ...payload,
          source_type: sourceForm.source_type,
        });
      }
      setSourceModal(false);
    });
  }

  function openNewWorker() {
    setWorkerForm({
      source_id: sources.find((source) => source.is_active)?.id ?? "",
      name: "",
      trade: "",
      cnic: "",
      phone: "",
      default_daily_rate: "",
      is_active: true,
    });
    setWorkerModal(true);
  }

  function openEditWorker(worker: LabourWorker) {
    setWorkerForm({
      id: worker.id,
      source_id: worker.source_id,
      name: worker.name,
      trade: worker.trade,
      cnic: worker.cnic ?? "",
      phone: worker.phone ?? "",
      default_daily_rate:
        worker.default_daily_rate == null ? "" : String(worker.default_daily_rate),
      is_active: worker.is_active,
    });
    setWorkerModal(true);
  }

  async function saveWorker() {
    if (!workerForm?.source_id || !workerForm.name.trim() || !workerForm.trade.trim()) {
      setError(t("labour.workerSourceNameTradeRequired"));
      return;
    }

    const base = {
      name: workerForm.name.trim(),
      trade: workerForm.trade.trim(),
      cnic: workerForm.cnic.trim() || null,
      phone: workerForm.phone.trim() || null,
      default_daily_rate:
        workerForm.default_daily_rate === ""
          ? null
          : Number(workerForm.default_daily_rate),
      is_active: workerForm.is_active,
    };

    await run(async () => {
      if (workerForm.id) {
        await updateLabourWorker(workerForm.id, base);
      } else {
        await createLabourWorker({
          ...base,
          source_id: workerForm.source_id,
        });
      }
      setWorkerModal(false);
    });
  }

  async function submitAttendance() {
    if (!projectId || !canManage) return;

    const entries = activeDeployments
      .filter((deployment) => attendanceValues[deployment.id] !== undefined)
      .map((deployment) => ({
        deployment_id: deployment.id,
        attendance_date: attendanceDate,
        units_present: Number(attendanceValues[deployment.id]),
      }));

    if (entries.length === 0) {
      setError(t("labour.attendanceAtLeastOne"));
      return;
    }

    await run(() => bulkRecordLabourAttendance(projectId, entries));
  }

  async function submitAdvance() {
    if (!projectId || !canManagePayments || !sourceId) return;
    if (!advanceDate.match(/^\d{4}-\d{2}-\d{2}$/) || Number(advanceAmount) <= 0) {
      setError(t("labour.advancePositiveDate"));
      return;
    }

    await run(() =>
      createLabourAdvance(projectId, {
        source_id: sourceId,
        worker_id: workerId || null,
        amount: Number(advanceAmount),
        advance_date: advanceDate,
        notes: advanceNotes.trim() || null,
      })
    );
    setAdvanceAmount("");
    setAdvanceNotes("");
  }

  async function submitPayment() {
    if (!projectId || !canManagePayments || !sourceId) return;
    if (
      !paymentPeriodStart.match(/^\d{4}-\d{2}-\d{2}$/) ||
      !paymentPeriodEnd.match(/^\d{4}-\d{2}-\d{2}$/) ||
      !paymentDate.match(/^\d{4}-\d{2}-\d{2}$/) ||
      paymentPeriodEnd < paymentPeriodStart
    ) {
      setError(t("labour.paymentValidDates"));
      return;
    }
    if (Number(grossWage) < 0 || Number(advanceRecovery) < 0) {
      setError(t("labour.wageAdvanceNotNegative"));
      return;
    }

    await run(async () => {
      const result = await createLabourPayment(projectId, {
        source_id: sourceId,
        worker_id: workerId || null,
        period_start: paymentPeriodStart,
        period_end: paymentPeriodEnd,
        gross_wage_amount: Number(grossWage),
        advance_recovered_amount: Number(advanceRecovery || 0),
        payment_date: paymentDate,
        wht_category: whtCategory || null,
        notes: paymentNotes.trim() || null,
      });
      setLastPayment(result);
    });

    setGrossWage("");
    setAdvanceRecovery("0");
    setPaymentNotes("");
  }

  const activeDeployments = deployments.filter(
    (deployment) => deployment.status === "ACTIVE"
  );
  const activeSources = sources.filter((source) => source.is_active);
  const workersForSource = workers.filter(
    (worker) => worker.source_id === sourceId && worker.is_active
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <LanguageSwitcher />
        <ActivityIndicator size="large" color={C.navy} />
        <Text style={styles.muted}>
          {t("labour.loading", { section: title.toLowerCase() })}
        </Text>
      </View>
    );
  }

  if (sessionChecked && !canRead) {
    return (
      <View style={styles.page}>
        <LanguageSwitcher />
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.error}>{t("labour.accessDenied")}</Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title }} />
      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => void load(true)} />
        }
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.topBar}>
          <Pressable style={styles.backPressable} onPress={() => router.back()}>
            <Text style={styles.link}>
              ‹  {section === "directory"
                ? t("labour.back")
                : project?.name ?? t("labour.overviewTitle")}
            </Text>
          </Pressable>

          <LanguageSwitcher />
        </View>

        <Text style={styles.title}>{title}</Text>
        {project ? <Text style={styles.muted}>{project.name}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}

        {section === "directory" ? (
          <>
            <Section title={t("labour.sourcesSection")}>
              {canManage ? (
                <Action label={t("labour.addSource")} onPress={openNewSource} />
              ) : null}
              {sources.map((source) => (
                <View key={source.id} style={styles.card}>
                  <Text style={styles.itemTitle}>{source.name}</Text>
                  <Text style={styles.muted}>
                    {source.source_type === "CONTRACTOR"
                      ? t("labour.contractor")
                      : t("labour.directWorkforce")}{" "}
                    · {source.is_active ? t("labour.active") : t("labour.inactive")}
                  </Text>
                  {source.contact_name || source.contact_phone ? (
                    <Text style={styles.muted}>
                      {[source.contact_name, source.contact_phone]
                        .filter(Boolean)
                        .join(" · ")}
                    </Text>
                  ) : null}
                  {canManage ? (
                    <Action
                      label={t("labour.editSource")}
                      onPress={() => openEditSource(source)}
                    />
                  ) : null}
                </View>
              ))}
            </Section>

            <Section title={t("labour.workersSection")}>
              {canManage ? (
                <Action
                  label={t("labour.addWorker")}
                  onPress={openNewWorker}
                  disabled={activeSources.length === 0}
                />
              ) : null}
              {workers.map((worker) => (
                <View key={worker.id} style={styles.card}>
                  <Text style={styles.itemTitle}>{worker.name}</Text>
                  <Text style={styles.muted}>
                    {worker.trade} ·{" "}
                    {sources.find((source) => source.id === worker.source_id)?.name ??
                      t("labour.sourceFallback")}
                  </Text>
                  <Text style={styles.muted}>
                    {worker.is_active ? t("labour.active") : t("labour.inactive")}
                    {worker.default_daily_rate == null
                      ? ""
                      : ` · ${t("labour.dailyRateLabel", {
                          rate: worker.default_daily_rate,
                        })}`}
                  </Text>
                  {canManage ? (
                    <Action
                      label={t("labour.editWorker")}
                      onPress={() => openEditWorker(worker)}
                    />
                  ) : null}
                </View>
              ))}
            </Section>
          </>
        ) : null}

        {section === "overview" ? (
          <>
            <Section title={t("labour.summaryPeriod")}>
              <Field
                label={t("labour.periodStart")}
                value={periodStart}
                onChangeText={setPeriodStart}
              />
              <Field
                label={t("labour.periodEnd")}
                value={periodEnd}
                onChangeText={setPeriodEnd}
              />
              <Action
                label={t("labour.refreshSummary")}
                onPress={() => void load(true)}
              />
            </Section>
            {summary ? (
              <Section title={t("labour.labourSummary")}>
                <Info
                  label={t("labour.accruedCost")}
                  value={`${summary.currency} ${summary.total_accrued_cost}`}
                />
                <Info
                  label={t("labour.advancesGiven")}
                  value={`${summary.currency} ${summary.total_advances_given}`}
                />
                <Info
                  label={t("labour.advanceRecovered")}
                  value={`${summary.currency} ${summary.total_payments_made}`}
                />
                <Info
                  label={t("labour.outstandingAdvance")}
                  value={`${summary.currency} ${summary.outstanding_advance_balance}`}
                />
                {summary.cost_by_trade.map((row) => (
                  <Info
                    key={row.trade}
                    label={t("labour.tradeAccrued", { trade: row.trade })}
                    value={`${summary.currency} ${row.cost}`}
                  />
                ))}
              </Section>
            ) : null}
            <RouteLink
              projectId={projectId}
              route="deployments"
              label={t("labour.linkDeployments")}
            />
            <RouteLink
              projectId={projectId}
              route="attendance"
              label={t("labour.linkAttendance")}
            />
            <RouteLink
              projectId={projectId}
              route="finance"
              label={t("labour.linkFinance")}
            />
          </>
        ) : null}

        {section === "deployments" ? (
          <>
            {canManage ? (
              <Section title={t("labour.deployLabour")}>
                <Text style={styles.label}>{t("labour.source")}</Text>
                <ChoiceList
                  values={activeSources.map((item) => [item.id, item.name])}
                  selected={sourceId}
                  onSelect={(value) => {
                    setSourceId(value);
                    setWorkerId("");
                  }}
                />
                <Text style={styles.label}>{t("labour.namedWorkerOptional")}</Text>
                <Choice
                  label={t("labour.headcountCrew")}
                  selected={!workerId}
                  onPress={() => setWorkerId("")}
                />
                {workers
                  .filter(
                    (worker) => worker.source_id === sourceId && worker.is_active
                  )
                  .map((worker) => (
                    <Choice
                      key={worker.id}
                      label={`${worker.name} · ${worker.trade}`}
                      selected={worker.id === workerId}
                      onPress={() => setWorkerId(worker.id)}
                    />
                  ))}
                <Field
                  label={t("labour.trade")}
                  value={trade}
                  onChangeText={setTrade}
                />
                <Field
                  label={t("labour.dailyRate")}
                  value={dailyRate}
                  onChangeText={setDailyRate}
                  keyboardType="decimal-pad"
                />
                <Field
                  label={t("labour.startDate")}
                  value={deploymentStartDate}
                  onChangeText={setDeploymentStartDate}
                />
                <Action
                  label={busy ? t("labour.saving") : t("labour.deploy")}
                  disabled={
                    busy || !sourceId || !trade.trim() || Number(dailyRate) <= 0
                  }
                  onPress={() => {
                    if (!projectId) return;
                    void run(() =>
                      createLabourDeployment(projectId, {
                        source_id: sourceId,
                        worker_id: workerId || null,
                        trade: trade.trim(),
                        daily_rate: Number(dailyRate),
                        start_date: deploymentStartDate,
                      })
                    );
                  }}
                />
              </Section>
            ) : null}

            <Section title={t("labour.projectDeployments")}>
              {deployments.map((deployment) => (
                <View key={deployment.id} style={styles.card}>
                  <Text style={styles.itemTitle}>{deployment.trade}</Text>
                  <Text style={styles.muted}>
                    {sources.find((source) => source.id === deployment.source_id)
                      ?.name ?? t("labour.sourceFallback")}
                    {deployment.worker_id
                      ? ` · ${
                          workers.find((worker) => worker.id === deployment.worker_id)
                            ?.name ?? t("labour.workerFallback")
                        }`
                      : ` · ${t("labour.headcount")}`}
                  </Text>
                  <Text style={styles.muted}>
                    {t("labour.rateToCurrent", {
                      rate: deployment.daily_rate,
                      start: deployment.start_date,
                      end: deployment.end_date ?? t("labour.current"),
                      status:
                        deployment.status === "ACTIVE"
                          ? t("labour.active")
                          : t("labour.inactive"),
                    })}
                  </Text>
                  {canManage && deployment.status === "ACTIVE" ? (
                    <Action
                      label={t("labour.endToday")}
                      disabled={busy}
                      onPress={() =>
                        projectId
                          ? void run(() =>
                              updateLabourDeployment(projectId, deployment.id, {
                                status: "ENDED",
                                end_date: today(),
                              })
                            )
                          : undefined
                      }
                    />
                  ) : null}
                </View>
              ))}
              {deployments.length === 0 ? (
                <Text style={styles.muted}>{t("labour.noDeployments")}</Text>
              ) : null}
            </Section>
          </>
        ) : null}

        {section === "attendance" ? (
          <>
            <Section title={t("labour.attendanceDate")}>
              <Field
                label={t("labour.date")}
                value={attendanceDate}
                onChangeText={setAttendanceDate}
              />
              <Action
                label={t("labour.loadDate")}
                onPress={() => void load(true)}
              />
              {daySummary ? (
                <Info
                  label={t("labour.totalPresentUnits")}
                  value={String(daySummary.total_present)}
                />
              ) : null}
              {daySummary?.by_trade.map((row) => (
                <Info
                  key={row.trade}
                  label={t("labour.tradePresentUnits", { trade: row.trade })}
                  value={String(row.cost)}
                />
              ))}
            </Section>

            <Section title={t("labour.recordAttendance")}>
              {activeDeployments.map((deployment) => {
                const namedWorker = deployment.worker_id != null;
                const workerName = workers.find(
                  (worker) => worker.id === deployment.worker_id
                )?.name;
                return (
                  <View key={deployment.id} style={styles.card}>
                    <Text style={styles.itemTitle}>
                      {deployment.trade}
                      {namedWorker
                        ? ` · ${workerName ?? t("labour.workerFallback")}`
                        : ` · ${t("labour.headcount")}`}
                    </Text>
                    <Text style={styles.muted}>
                      {namedWorker
                        ? t("labour.namedUnitsHelp")
                        : t("labour.headcountUnitsHelp")}
                    </Text>
                    <Field
                      label={t("labour.unitsPresent")}
                      value={attendanceValues[deployment.id] ?? ""}
                      onChangeText={(value) =>
                        setAttendanceValues((current) => ({
                          ...current,
                          [deployment.id]: value,
                        }))
                      }
                      keyboardType="decimal-pad"
                      editable={canManage}
                    />
                  </View>
                );
              })}
              {activeDeployments.length === 0 ? (
                <Text style={styles.muted}>
                  {t("labour.createActiveDeploymentFirst")}
                </Text>
              ) : null}
              {canManage && activeDeployments.length > 0 ? (
                <Action
                  label={busy ? t("labour.saving") : t("labour.saveAttendance")}
                  disabled={busy}
                  onPress={() => void submitAttendance()}
                />
              ) : null}
            </Section>
          </>
        ) : null}

        {section === "finance" ? (
          <>
            <Section title={t("labour.financeSummary")}>
              <Field
                label={t("labour.periodStartShort")}
                value={periodStart}
                onChangeText={setPeriodStart}
              />
              <Field
                label={t("labour.periodEndShort")}
                value={periodEnd}
                onChangeText={setPeriodEnd}
              />
              <Action
                label={t("labour.refreshFinance")}
                onPress={() => void load(true)}
              />
              {summary ? (
                <>
                  <Info
                    label={t("labour.accruedLabourCost")}
                    value={`${summary.currency} ${summary.total_accrued_cost}`}
                  />
                  <Info
                    label={t("labour.advancesGiven")}
                    value={`${summary.currency} ${summary.total_advances_given}`}
                  />
                  <Info
                    label={t("labour.advanceRecovered")}
                    value={`${summary.currency} ${summary.total_payments_made}`}
                  />
                  <Info
                    label={t("labour.outstandingAdvance")}
                    value={`${summary.currency} ${summary.outstanding_advance_balance}`}
                  />
                </>
              ) : null}
              {balance != null ? (
                <Info
                  label={t("labour.selectedSourceBalance", {
                    currency: summary?.currency ?? "PKR",
                  })}
                  value={String(balance)}
                />
              ) : null}
            </Section>

            {canManagePayments ? (
              <>
                <Section title={t("labour.recordAdvance")}>
                  <Text style={styles.label}>{t("labour.activeSource")}</Text>
                  <ChoiceList
                    values={activeSources.map((item) => [item.id, item.name])}
                    selected={sourceId}
                    onSelect={(value) => {
                      setSourceId(value);
                      setWorkerId("");
                    }}
                  />
                  <Text style={styles.label}>{t("labour.workerOptional")}</Text>
                  <Choice
                    label={t("labour.sourceLevel")}
                    selected={!workerId}
                    onPress={() => setWorkerId("")}
                  />
                  {workersForSource.map((worker) => (
                    <Choice
                      key={worker.id}
                      label={worker.name}
                      selected={worker.id === workerId}
                      onPress={() => setWorkerId(worker.id)}
                    />
                  ))}
                  <Field
                    label={t("labour.positiveAmount")}
                    value={advanceAmount}
                    onChangeText={setAdvanceAmount}
                    keyboardType="decimal-pad"
                  />
                  <Field
                    label={t("labour.advanceDate")}
                    value={advanceDate}
                    onChangeText={setAdvanceDate}
                  />
                  <Field
                    label={t("labour.notes")}
                    value={advanceNotes}
                    onChangeText={setAdvanceNotes}
                    multiline
                  />
                  <Action
                    label={t("labour.recordAdvance")}
                    disabled={busy || !sourceId || Number(advanceAmount) <= 0}
                    onPress={() => void submitAdvance()}
                  />
                </Section>

                <Section title={t("labour.recordWagePayment")}>
                  <Text style={styles.label}>{t("labour.activeSource")}</Text>
                  <ChoiceList
                    values={activeSources.map((item) => [item.id, item.name])}
                    selected={sourceId}
                    onSelect={(value) => {
                      setSourceId(value);
                      setWorkerId("");
                      setWhtCategory("");
                    }}
                  />
                  <Text style={styles.label}>{t("labour.workerOptional")}</Text>
                  <Choice
                    label={t("labour.sourceLevel")}
                    selected={!workerId}
                    onPress={() => setWorkerId("")}
                  />
                  {workersForSource.map((worker) => (
                    <Choice
                      key={worker.id}
                      label={worker.name}
                      selected={worker.id === workerId}
                      onPress={() => setWorkerId(worker.id)}
                    />
                  ))}
                  <Field
                    label={t("labour.periodStartFull")}
                    value={paymentPeriodStart}
                    onChangeText={setPaymentPeriodStart}
                  />
                  <Field
                    label={t("labour.periodEndFull")}
                    value={paymentPeriodEnd}
                    onChangeText={setPaymentPeriodEnd}
                  />
                  <Field
                    label={t("labour.grossWageAmount")}
                    value={grossWage}
                    onChangeText={setGrossWage}
                    keyboardType="decimal-pad"
                  />
                  <Field
                    label={t("labour.advanceRecovery")}
                    value={advanceRecovery}
                    onChangeText={setAdvanceRecovery}
                    keyboardType="decimal-pad"
                  />
                  <Field
                    label={t("labour.paymentDate")}
                    value={paymentDate}
                    onChangeText={setPaymentDate}
                  />

                  {sources.find((source) => source.id === sourceId)?.source_type ===
                  "CONTRACTOR" ? (
                    <>
                      <Text style={styles.label}>{t("labour.whtCategory")}</Text>
                      <Choice
                        label={t("labour.noWht")}
                        selected={!whtCategory}
                        onPress={() => setWhtCategory("")}
                      />
                      {([
                        "GOODS_SUPPLY",
                        "SERVICES",
                        "CONTRACTS_EXECUTION",
                      ] as LabourWhtCategory[]).map((category) => (
                        <Choice
                          key={category}
                          label={t(`labour.whtCategories.${category}`)}
                          selected={whtCategory === category}
                          onPress={() => setWhtCategory(category)}
                        />
                      ))}
                    </>
                  ) : null}

                  <Field
                    label={t("labour.notes")}
                    value={paymentNotes}
                    onChangeText={setPaymentNotes}
                    multiline
                  />
                  <Action
                    label={t("labour.recordPayment")}
                    disabled={
                      busy || !sourceId || !paymentPeriodStart || !grossWage
                    }
                    onPress={() => void submitPayment()}
                  />
                  {lastPayment ? (
                    <View style={styles.card}>
                      <Text style={styles.itemTitle}>
                        {t("labour.paymentRecorded")}
                      </Text>
                      <Info
                        label={t("labour.whtRate")}
                        value={
                          lastPayment.wht_rate_percentage == null
                            ? t("labour.none")
                            : `${lastPayment.wht_rate_percentage}%`
                        }
                      />
                      <Info
                        label={t("labour.whtDeducted")}
                        value={String(lastPayment.wht_deducted_amount)}
                      />
                      <Info
                        label={t("labour.netPaid")}
                        value={String(lastPayment.net_paid_amount)}
                      />
                    </View>
                  ) : null}
                </Section>
              </>
            ) : (
              <Text style={styles.muted}>{t("labour.noPaymentPermission")}</Text>
            )}

            <Section title={t("labour.advancesSection")}>
              {advances.map((item) => (
                <View key={item.id} style={styles.card}>
                  <Text style={styles.itemTitle}>
                    {sources.find((source) => source.id === item.source_id)?.name ??
                      t("labour.sourceFallback")}
                  </Text>
                  <Text style={styles.muted}>
                    {item.advance_date} · {item.amount}
                  </Text>
                  {item.notes ? (
                    <Text style={styles.muted}>{item.notes}</Text>
                  ) : null}
                </View>
              ))}
              {advances.length === 0 ? (
                <Text style={styles.muted}>{t("labour.noAdvances")}</Text>
              ) : null}
            </Section>

            <Section title={t("labour.paymentsSection")}>
              {payments.map((item) => (
                <View key={item.id} style={styles.card}>
                  <Text style={styles.itemTitle}>
                    {sources.find((source) => source.id === item.source_id)?.name ??
                      t("labour.sourceFallback")}
                  </Text>
                  <Text style={styles.muted}>
                    {item.period_start} – {item.period_end}
                  </Text>
                  <Info
                    label={t("labour.grossWages")}
                    value={String(item.gross_wage_amount)}
                  />
                  <Info
                    label={t("labour.advanceRecovered")}
                    value={String(item.advance_recovered_amount)}
                  />
                  <Info
                    label={t("labour.whtDeducted")}
                    value={String(item.wht_deducted_amount)}
                  />
                  <Info
                    label={t("labour.netPaid")}
                    value={String(item.net_paid_amount)}
                  />
                  {item.notes ? (
                    <Text style={styles.muted}>{item.notes}</Text>
                  ) : null}
                </View>
              ))}
              {payments.length === 0 ? (
                <Text style={styles.muted}>{t("labour.noPayments")}</Text>
              ) : null}
            </Section>
          </>
        ) : null}
      </ScrollView>

      <EditSourceModal
        visible={sourceModal}
        form={sourceForm}
        setForm={setSourceForm}
        onClose={() => setSourceModal(false)}
        onSave={() => void saveSource()}
        busy={busy}
      />
      <EditWorkerModal
        visible={workerModal}
        form={workerForm}
        setForm={setWorkerForm}
        sources={activeSources}
        onClose={() => setWorkerModal(false)}
        onSave={() => void saveWorker()}
        busy={busy}
      />
    </>
  );
}

function Section({
  title,
  children,
}: React.PropsWithChildren<{ title: string }>) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Field({
  label,
  value,
  onChangeText,
  keyboardType,
  multiline = false,
  editable = true,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad" | "number-pad" | "phone-pad";
  multiline?: boolean;
  editable?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        multiline={multiline}
        editable={editable}
        placeholder={label}
        autoCapitalize="sentences"
      />
    </View>
  );
}

function Action({
  label,
  onPress,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      style={[styles.button, disabled && styles.buttonDisabled]}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
    >
      <Text style={styles.buttonText}>{label}</Text>
    </Pressable>
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
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
    >
      <Text style={[styles.choiceText, selected && styles.choiceTextSelected]}>
        {selected ? "✓ " : ""}
        {label}
      </Text>
    </Pressable>
  );
}

function ChoiceList({
  values,
  selected,
  onSelect,
}: {
  values: [string, string][];
  selected: string;
  onSelect: (value: string) => void;
}) {
  return (
    <View style={styles.choiceList}>
      {values.map(([value, label]) => (
        <Choice
          key={value}
          label={label}
          selected={selected === value}
          onPress={() => onSelect(value)}
        />
      ))}
    </View>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.muted}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function RouteLink({
  projectId,
  route,
  label,
}: {
  projectId?: string;
  route: "deployments" | "attendance" | "finance";
  label: string;
}) {
  if (!projectId) return null;
  return (
    <Pressable
      style={styles.secondaryButton}
      onPress={() =>
        router.push({
          pathname: `/projects/[projectId]/labour/${route}`,
          params: { projectId },
        })
      }
      accessibilityRole="button"
    >
      <Text style={styles.secondaryButtonText}>{label}  ›</Text>
    </Pressable>
  );
}

function EditSourceModal({
  visible,
  form,
  setForm,
  onClose,
  onSave,
  busy,
}: {
  visible: boolean;
  form: SourceForm | null;
  setForm: React.Dispatch<React.SetStateAction<SourceForm | null>>;
  onClose: () => void;
  onSave: () => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  if (!form) return null;
  const patch = (value: Partial<SourceForm>) =>
    setForm((current) => (current ? { ...current, ...value } : current));

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <ScrollView
        contentContainerStyle={styles.modal}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>
          {form.id ? t("labour.editSourceTitle") : t("labour.addSourceTitle")}
        </Text>
        <Field
          label={t("labour.name")}
          value={form.name}
          onChangeText={(name) => patch({ name })}
        />
        {!form.id ? (
          <>
            <Text style={styles.label}>{t("labour.sourceType")}</Text>
            <Choice
              label={t("labour.contractor")}
              selected={form.source_type === "CONTRACTOR"}
              onPress={() => patch({ source_type: "CONTRACTOR" })}
            />
            <Choice
              label={t("labour.directWorkforce")}
              selected={form.source_type === "DIRECT"}
              onPress={() => patch({ source_type: "DIRECT" })}
            />
          </>
        ) : null}
        <Field
          label={t("labour.contactName")}
          value={form.contact_name}
          onChangeText={(contact_name) => patch({ contact_name })}
        />
        <Field
          label={t("labour.contactPhone")}
          value={form.contact_phone}
          onChangeText={(contact_phone) => patch({ contact_phone })}
          keyboardType="phone-pad"
        />
        <Field
          label={t("labour.notes")}
          value={form.notes}
          onChangeText={(notes) => patch({ notes })}
          multiline
        />
        <Toggle
          label={t("labour.activeTaxpayer")}
          value={form.is_active_taxpayer}
          onValueChange={(is_active_taxpayer) => patch({ is_active_taxpayer })}
        />
        {form.id ? (
          <Toggle
            label={t("labour.sourceActive")}
            value={form.is_active}
            onValueChange={(is_active) => patch({ is_active })}
          />
        ) : null}
        <Action
          label={busy ? t("labour.saving") : t("labour.saveSource")}
          disabled={busy || !form.name.trim()}
          onPress={onSave}
        />
        <Action
          label={t("labour.cancel")}
          disabled={busy}
          onPress={onClose}
        />
      </ScrollView>
    </Modal>
  );
}

function EditWorkerModal({
  visible,
  form,
  setForm,
  sources,
  onClose,
  onSave,
  busy,
}: {
  visible: boolean;
  form: WorkerForm | null;
  setForm: React.Dispatch<React.SetStateAction<WorkerForm | null>>;
  sources: LabourSource[];
  onClose: () => void;
  onSave: () => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  if (!form) return null;
  const patch = (value: Partial<WorkerForm>) =>
    setForm((current) => (current ? { ...current, ...value } : current));

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <ScrollView
        contentContainerStyle={styles.modal}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>
          {form.id ? t("labour.editWorkerTitle") : t("labour.addWorkerTitle")}
        </Text>
        {!form.id ? (
          <>
            <Text style={styles.label}>{t("labour.source")}</Text>
            {sources.map((source) => (
              <Choice
                key={source.id}
                label={source.name}
                selected={form.source_id === source.id}
                onPress={() => patch({ source_id: source.id })}
              />
            ))}
          </>
        ) : null}
        <Field
          label={t("labour.name")}
          value={form.name}
          onChangeText={(name) => patch({ name })}
        />
        <Field
          label={t("labour.trade")}
          value={form.trade}
          onChangeText={(trade) => patch({ trade })}
        />
        <Field
          label={t("labour.cnic")}
          value={form.cnic}
          onChangeText={(cnic) => patch({ cnic })}
          keyboardType="number-pad"
        />
        <Field
          label={t("labour.phone")}
          value={form.phone}
          onChangeText={(phone) => patch({ phone })}
          keyboardType="phone-pad"
        />
        <Field
          label={t("labour.defaultDailyRateOptional")}
          value={form.default_daily_rate}
          onChangeText={(default_daily_rate) => patch({ default_daily_rate })}
          keyboardType="decimal-pad"
        />
        {form.id ? (
          <Toggle
            label={t("labour.workerActive")}
            value={form.is_active}
            onValueChange={(is_active) => patch({ is_active })}
          />
        ) : null}
        <Action
          label={busy ? t("labour.saving") : t("labour.saveWorker")}
          disabled={
            busy || !form.source_id || !form.name.trim() || !form.trade.trim()
          }
          onPress={onSave}
        />
        <Action
          label={t("labour.cancel")}
          disabled={busy}
          onPress={onClose}
        />
      </ScrollView>
    </Modal>
  );
}

function Toggle({
  label,
  value,
  onValueChange,
}: {
  label: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
}) {
  return (
    <View style={styles.toggle}>
      <Text style={styles.label}>{label}</Text>
      <Switch value={value} onValueChange={onValueChange} />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, paddingHorizontal: 18, paddingTop: 21, paddingBottom: 44, backgroundColor: C.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 20, backgroundColor: C.background },
  topBar: { minHeight: 42, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10 },
  backPressable: { minHeight: 40, justifyContent: "center", paddingVertical: 7, paddingRight: 10, flexShrink: 1 },
  title: { color: C.text, fontSize: 28, fontWeight: "800", letterSpacing: -0.5, marginTop: 7, marginBottom: 12 },
  section: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, padding: 16, marginTop: 14 },
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: "800", marginBottom: 10 },
  card: { backgroundColor: C.surface, borderColor: C.border, borderWidth: 1, borderRadius: 13, padding: 14, marginTop: 10 },
  itemTitle: { color: C.text, fontSize: 16, fontWeight: "800" },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 5 },
  error: { color: C.red, backgroundColor: C.redBg, borderWidth: 1, borderColor: "#EAC6C0", borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19, marginTop: 10 },
  link: { color: C.navy, fontSize: 13, fontWeight: "700" },
  label: { color: C.secondary, fontSize: 11, fontWeight: "700", letterSpacing: 0.3, marginTop: 10, marginBottom: 5 },
  field: { marginTop: 7 },
  input: { minHeight: 46, borderWidth: 1, borderColor: C.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: C.surface, color: C.text, fontSize: 14 },
  multiline: { minHeight: 82, textAlignVertical: "top" },
  button: { minHeight: 47, borderRadius: 11, backgroundColor: C.navy, paddingHorizontal: 14, paddingVertical: 12, alignItems: "center", justifyContent: "center", marginTop: 10 },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: C.surface, fontSize: 13, fontWeight: "800" },
  secondaryButton: { minHeight: 48, borderRadius: 10, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface, padding: 14, marginTop: 10 },
  secondaryButtonText: { color: C.navy, textAlign: "center", fontWeight: "800", fontSize: 13 },
  choiceList: { gap: 7, marginTop: 6 },
  choice: { borderWidth: 1, borderColor: C.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, marginTop: 6, backgroundColor: C.surface },
  choiceSelected: { borderColor: C.gold, backgroundColor: C.surfaceMuted },
  choiceText: { color: C.secondary, fontWeight: "600", fontSize: 13 },
  choiceTextSelected: { color: C.navy },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 10, paddingVertical: 8, borderTopWidth: 1, borderTopColor: "#F0E9DC" },
  infoValue: { color: C.text, fontSize: 13, fontWeight: "700", textAlign: "right", flexShrink: 1 },
  toggle: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 8 },
  modal: { flexGrow: 1, backgroundColor: C.background, paddingHorizontal: 18, paddingTop: 42, paddingBottom: 40 },
});
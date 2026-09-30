import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from "react-native";
import { router, Stack, useLocalSearchParams } from "expo-router";
import { restoreSession } from "../api/client";
import {bulkRecordLabourAttendance, createLabourAdvance, createLabourDeployment, createLabourPayment, createLabourSource, createLabourWorker, getLabourBalance, getLabourDaySummary, getLabourSummary,
  listLabourAdvances,  listLabourAttendance, listLabourDeployments, listLabourPayments, listLabourSources, listLabourWorkers, updateLabourDeployment, updateLabourSource, updateLabourWorker,
} from "../api/labour";
import { getProject } from "../api/projects";
import type {LabourAdvance, LabourDayAttendanceSummary, LabourDeployment, LabourPayment, LabourSource, LabourSourceType, LabourSummary, LabourWhtCategory, LabourWorker, Project,
} from "../api/types";

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
    null,
  );
  const [advances, setAdvances] = useState<LabourAdvance[]>([]);
  const [payments, setPayments] = useState<LabourPayment[]>([]);
  const [summary, setSummary] = useState<LabourSummary | null>(null);
  const [balance, setBalance] = useState<number | string | null>(null);

  const [periodStart, setPeriodStart] = useState(firstOfMonth);
  const [periodEnd, setPeriodEnd] = useState(today);
  const [attendanceDate, setAttendanceDate] = useState(today);
  const [attendanceValues, setAttendanceValues] = useState<
    Record<string, string>
  >({});

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
          setError("Project ID is missing from this route.");
          return;
        }

        const projectResult = await getProject(projectId);
        setProject(projectResult);

        if (section === "overview") {
          setSummary(
            await getLabourSummary(projectId, periodStart, periodEnd),
          );
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
        setError(err instanceof Error ? err.message : "Could not load Labour.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [section, projectId, periodStart, periodEnd, attendanceDate, sourceId],
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
      setError(err instanceof Error ? err.message : "The action failed.");
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
      setError("Source name is required.");
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
        worker.default_daily_rate == null
          ? ""
          : String(worker.default_daily_rate),
      is_active: worker.is_active,
    });
    setWorkerModal(true);
  }

  async function saveWorker() {
    if (
      !workerForm?.source_id ||
      !workerForm.name.trim() ||
      !workerForm.trade.trim()
    ) {
      setError("Choose a source and enter the worker name and trade.");
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
      setError("Enter attendance for at least one deployment.");
      return;
    }

    await run(() => bulkRecordLabourAttendance(projectId, entries));
  }

  async function submitAdvance() {
    if (!projectId || !canManagePayments || !sourceId) return;
    if (!advanceDate.match(/^\d{4}-\d{2}-\d{2}$/) || Number(advanceAmount) <= 0) {
      setError("Enter a positive advance and a date in YYYY-MM-DD format.");
      return;
    }

    await run(() =>
      createLabourAdvance(projectId, {
        source_id: sourceId,
        worker_id: workerId || null,
        amount: Number(advanceAmount),
        advance_date: advanceDate,
        notes: advanceNotes.trim() || null,
      }),
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
      setError("Enter valid dates and ensure the period end is on or after its start.");
      return;
    }
    if (Number(grossWage) < 0 || Number(advanceRecovery) < 0) {
      setError("Wage and advance recovery amounts cannot be negative.");
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
    (deployment) => deployment.status === "ACTIVE",
  );
  const activeSources = sources.filter((source) => source.is_active);
  const workersForSource = workers.filter(
    (worker) => worker.source_id === sourceId && worker.is_active,
  );
  const title =
    section === "directory"
      ? "Labour directory"
      : section === "overview"
        ? "Labour"
        : section === "deployments"
          ? "Deployments"
          : section === "attendance"
            ? "Attendance"
            : "Labour finance";

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading {title.toLowerCase()}…</Text>
      </View>
    );
  }

  if (sessionChecked && !canRead) {
    return (
      <View style={styles.page}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.error}>
          Your organization role does not allow you to view Labour.
        </Text>
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
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>
            ‹  {section === "directory" ? "Back" : project?.name ?? "Project"}
          </Text>
        </Pressable>

        <Text style={styles.title}>{title}</Text>
        {project ? <Text style={styles.muted}>{project.name}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}

        {section === "directory" ? (
          <>
            <Section title="Labour sources">
              {canManage ? (
                <Action label="＋ Add source" onPress={openNewSource} />
              ) : null}
              {sources.map((source) => (
                <View key={source.id} style={styles.card}>
                  <Text style={styles.itemTitle}>{source.name}</Text>
                  <Text style={styles.muted}>
                    {source.source_type} · {source.is_active ? "Active" : "Inactive"}
                  </Text>
                  {source.contact_name || source.contact_phone ? (
                    <Text style={styles.muted}>
                      {[source.contact_name, source.contact_phone]
                        .filter(Boolean)
                        .join(" · ")}
                    </Text>
                  ) : null}
                  {canManage ? (
                    <Action label="Edit source" onPress={() => openEditSource(source)} />
                  ) : null}
                </View>
              ))}
            </Section>

            <Section title="Workers">
              {canManage ? (
                <Action
                  label="＋ Add worker"
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
                      "Source"}
                  </Text>
                  <Text style={styles.muted}>
                    {worker.is_active ? "Active" : "Inactive"}
                    {worker.default_daily_rate == null
                      ? ""
                      : ` · Daily rate ${worker.default_daily_rate}`}
                  </Text>
                  {canManage ? (
                    <Action label="Edit worker" onPress={() => openEditWorker(worker)} />
                  ) : null}
                </View>
              ))}
            </Section>
          </>
        ) : null}

        {section === "overview" ? (
          <>
            <Section title="Summary period">
              <Field label="Period start (YYYY-MM-DD)" value={periodStart}
                onChangeText={setPeriodStart} />
              <Field label="Period end (YYYY-MM-DD)" value={periodEnd}
                onChangeText={setPeriodEnd} />
              <Action label="Refresh summary" onPress={() => void load(true)} />
            </Section>
            {summary ? (
              <Section title="Labour summary">
                <Info label="Accrued cost" value={`${summary.currency} ${summary.total_accrued_cost}`} />
                <Info label="Advances given" value={`${summary.currency} ${summary.total_advances_given}`} />
                <Info label="Advance recovered" value={`${summary.currency} ${summary.total_payments_made}`} />
                <Info label="Outstanding advance balance" value={`${summary.currency} ${summary.outstanding_advance_balance}`} />
                {summary.cost_by_trade.map((row) => (
                  <Info key={row.trade} label={`${row.trade} accrued`} value={`${summary.currency} ${row.cost}`} />
                ))}
              </Section>
            ) : null}
            <RouteLink projectId={projectId} route="deployments" label="Deployments" />
            <RouteLink projectId={projectId} route="attendance" label="Attendance" />
            <RouteLink projectId={projectId} route="finance" label="Advances & payments" />
          </>
        ) : null}

        {section === "deployments" ? (
          <>
            {canManage ? (
              <Section title="Deploy labour">
                <Text style={styles.label}>Source</Text>
                <ChoiceList
                  values={activeSources.map((item) => [item.id, item.name])}
                  selected={sourceId}
                  onSelect={(value) => {
                    setSourceId(value);
                    setWorkerId("");
                  }}
                />
                <Text style={styles.label}>Named worker (optional; leave blank for headcount)</Text>
                <Choice label="Headcount crew" selected={!workerId}
                  onPress={() => setWorkerId("")} />
                {workers
                  .filter((worker) => worker.source_id === sourceId && worker.is_active)
                  .map((worker) => (
                    <Choice key={worker.id} label={`${worker.name} · ${worker.trade}`}
                      selected={worker.id === workerId} onPress={() => setWorkerId(worker.id)} />
                  ))}
                <Field label="Trade" value={trade} onChangeText={setTrade} />
                <Field label="Daily rate" value={dailyRate} onChangeText={setDailyRate}
                  keyboardType="decimal-pad" />
                <Field label="Start date (YYYY-MM-DD)" value={deploymentStartDate}
                  onChangeText={setDeploymentStartDate} />
                <Action
                  label={busy ? "Saving…" : "Deploy"}
                  disabled={busy || !sourceId || !trade.trim() || Number(dailyRate) <= 0}
                  onPress={() => {
                    if (!projectId) return;
                    void run(() =>
                      createLabourDeployment(projectId, {
                        source_id: sourceId,
                        worker_id: workerId || null,
                        trade: trade.trim(),
                        daily_rate: Number(dailyRate),
                        start_date: deploymentStartDate,
                      }),
                    );
                  }}
                />
              </Section>
            ) : null}

            <Section title="Project deployments">
              {deployments.map((deployment) => (
                <View key={deployment.id} style={styles.card}>
                  <Text style={styles.itemTitle}>{deployment.trade}</Text>
                  <Text style={styles.muted}>
                    {sources.find((source) => source.id === deployment.source_id)?.name ??
                      "Source"}
                    {deployment.worker_id
                      ? ` · ${workers.find((worker) => worker.id === deployment.worker_id)?.name ?? "Worker"}`
                      : " · Headcount"}
                  </Text>
                  <Text style={styles.muted}>
                    Rate {deployment.daily_rate} · {deployment.start_date} to{" "}
                    {deployment.end_date ?? "current"} · {deployment.status}
                  </Text>
                  {canManage && deployment.status === "ACTIVE" ? (
                    <Action
                      label="End today"
                      disabled={busy}
                      onPress={() =>
                        projectId
                          ? void run(() =>
                              updateLabourDeployment(projectId, deployment.id, {
                                status: "ENDED",
                                end_date: today(),
                              }),
                            )
                          : undefined
                      }
                    />
                  ) : null}
                </View>
              ))}
              {deployments.length === 0 ? (
                <Text style={styles.muted}>No deployments for this project yet.</Text>
              ) : null}
            </Section>
          </>
        ) : null}

        {section === "attendance" ? (
          <>
            <Section title="Attendance date">
              <Field label="Date (YYYY-MM-DD)" value={attendanceDate}
                onChangeText={setAttendanceDate} />
              <Action label="Load date" onPress={() => void load(true)} />
              {daySummary ? (
                <Info label="Total present units" value={String(daySummary.total_present)} />
              ) : null}
              {daySummary?.by_trade.map((row) => (
                <Info key={row.trade} label={`${row.trade} present units`} value={String(row.cost)} />
              ))}
            </Section>

            <Section title="Record attendance">
              {activeDeployments.map((deployment) => {
                const namedWorker = deployment.worker_id != null;
                const workerName = workers.find(
                  (worker) => worker.id === deployment.worker_id,
                )?.name;
                return (
                  <View key={deployment.id} style={styles.card}>
                    <Text style={styles.itemTitle}>
                      {deployment.trade}
                      {namedWorker ? ` · ${workerName ?? "Worker"}` : " · Headcount"}
                    </Text>
                    <Text style={styles.muted}>
                      {namedWorker
                        ? "Enter 0 (absent), 0.5 (half day), or 1 (present)."
                        : "Enter headcount units from 0 to 9999."}
                    </Text>
                    <Field
                      label="Units present"
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
                <Text style={styles.muted}>Create an active deployment first.</Text>
              ) : null}
              {canManage && activeDeployments.length > 0 ? (
                <Action
                  label={busy ? "Saving…" : "Save attendance"}
                  disabled={busy}
                  onPress={() => void submitAttendance()}
                />
              ) : null}
            </Section>
          </>
        ) : null}

        {section === "finance" ? (
          <>
            <Section title="Finance summary">
              <Field label="Period start" value={periodStart} onChangeText={setPeriodStart} />
              <Field label="Period end" value={periodEnd} onChangeText={setPeriodEnd} />
              <Action label="Refresh finance" onPress={() => void load(true)} />
              {summary ? (
                <>
                  <Info label="Accrued labour cost" value={`${summary.currency} ${summary.total_accrued_cost}`} />
                  <Info label="Advances given" value={`${summary.currency} ${summary.total_advances_given}`} />
                  <Info label="Advance recovered" value={`${summary.currency} ${summary.total_payments_made}`} />
                  <Info label="Outstanding advance balance" value={`${summary.currency} ${summary.outstanding_advance_balance}`} />
                </>
              ) : null}
              {balance != null ? (
                <Info label={`Selected source balance (${summary?.currency ?? "PKR"})`} value={String(balance)} />
              ) : null}
            </Section>

            {canManagePayments ? (
              <>
                <Section title="Record advance">
                  <Text style={styles.label}>Active source</Text>
                  <ChoiceList
                    values={activeSources.map((item) => [item.id, item.name])}
                    selected={sourceId}
                    onSelect={(value) => {
                      setSourceId(value);
                      setWorkerId("");
                    }}
                  />
                  <Text style={styles.label}>Worker (optional)</Text>
                  <Choice label="Source level" selected={!workerId}
                    onPress={() => setWorkerId("")} />
                  {workersForSource.map((worker) => (
                    <Choice key={worker.id} label={worker.name}
                      selected={worker.id === workerId} onPress={() => setWorkerId(worker.id)} />
                  ))}
                  <Field label="Positive amount" value={advanceAmount}
                    onChangeText={setAdvanceAmount} keyboardType="decimal-pad" />
                  <Field label="Advance date (YYYY-MM-DD)" value={advanceDate}
                    onChangeText={setAdvanceDate} />
                  <Field label="Notes" value={advanceNotes} onChangeText={setAdvanceNotes}
                    multiline />
                  <Action label="Record advance" disabled={busy || !sourceId || Number(advanceAmount) <= 0}
                    onPress={() => void submitAdvance()} />
                </Section>

                <Section title="Record wage payment">
                  <Text style={styles.label}>Active source</Text>
                  <ChoiceList
                    values={activeSources.map((item) => [item.id, item.name])}
                    selected={sourceId}
                    onSelect={(value) => {
                      setSourceId(value);
                      setWorkerId("");
                      setWhtCategory("");
                    }}
                  />
                  <Text style={styles.label}>Worker (optional)</Text>
                  <Choice label="Source level" selected={!workerId}
                    onPress={() => setWorkerId("")} />
                  {workersForSource.map((worker) => (
                    <Choice key={worker.id} label={worker.name}
                      selected={worker.id === workerId} onPress={() => setWorkerId(worker.id)} />
                  ))}
                  <Field label="Period start (YYYY-MM-DD)" value={paymentPeriodStart}
                    onChangeText={setPaymentPeriodStart} />
                  <Field label="Period end (YYYY-MM-DD)" value={paymentPeriodEnd}
                    onChangeText={setPaymentPeriodEnd} />
                  <Field label="Gross wage amount" value={grossWage}
                    onChangeText={setGrossWage} keyboardType="decimal-pad" />
                  <Field label="Advance recovery" value={advanceRecovery}
                    onChangeText={setAdvanceRecovery} keyboardType="decimal-pad" />
                  <Field label="Payment date (YYYY-MM-DD)" value={paymentDate}
                    onChangeText={setPaymentDate} />

                  {sources.find((source) => source.id === sourceId)?.source_type ===
                  "CONTRACTOR" ? (
                    <>
                      <Text style={styles.label}>Withholding tax category</Text>
                      <Choice label="No WHT" selected={!whtCategory}
                        onPress={() => setWhtCategory("")} />
                      {(
                        [
                          "GOODS_SUPPLY",
                          "SERVICES",
                          "CONTRACTS_EXECUTION",
                        ] as LabourWhtCategory[]
                      ).map((category) => (
                        <Choice key={category} label={category.replaceAll("_", " ")}
                          selected={whtCategory === category}
                          onPress={() => setWhtCategory(category)} />
                      ))}
                    </>
                  ) : null}

                  <Field label="Notes" value={paymentNotes}
                    onChangeText={setPaymentNotes} multiline />
                  <Action label="Record payment"
                    disabled={busy || !sourceId || !paymentPeriodStart || !grossWage}
                    onPress={() => void submitPayment()} />
                  {lastPayment ? (
                    <View style={styles.card}>
                      <Text style={styles.itemTitle}>Payment recorded</Text>
                      <Info label="WHT rate" value={lastPayment.wht_rate_percentage == null ? "None" : `${lastPayment.wht_rate_percentage}%`} />
                      <Info label="WHT deducted" value={String(lastPayment.wht_deducted_amount)} />
                      <Info label="Net paid" value={String(lastPayment.net_paid_amount)} />
                    </View>
                  ) : null}
                </Section>
              </>
            ) : (
              <Text style={styles.muted}>
                Your role cannot record Labour advances or wage payments.
              </Text>
            )}

            <Section title="Advances">
              {advances.map((item) => (
                <View key={item.id} style={styles.card}>
                  <Text style={styles.itemTitle}>
                    {sources.find((source) => source.id === item.source_id)?.name ??
                      "Source"}
                  </Text>
                  <Text style={styles.muted}>
                    {item.advance_date} · {item.amount}
                  </Text>
                  {item.notes ? <Text style={styles.muted}>{item.notes}</Text> : null}
                </View>
              ))}
              {advances.length === 0 ? (
                <Text style={styles.muted}>No advances recorded for this project.</Text>
              ) : null}
            </Section>

            <Section title="Payments">
              {payments.map((item) => (
                <View key={item.id} style={styles.card}>
                  <Text style={styles.itemTitle}>
                    {sources.find((source) => source.id === item.source_id)?.name ??
                      "Source"}
                  </Text>
                  <Text style={styles.muted}>
                    {item.period_start} – {item.period_end}
                  </Text>
                  <Info label="Gross wages" value={String(item.gross_wage_amount)} />
                  <Info label="Advance recovered" value={String(item.advance_recovered_amount)} />
                  <Info label="WHT deducted" value={String(item.wht_deducted_amount)} />
                  <Info label="Net paid" value={String(item.net_paid_amount)} />
                  {item.notes ? <Text style={styles.muted}>{item.notes}</Text> : null}
                </View>
              ))}
              {payments.length === 0 ? (
                <Text style={styles.muted}>No wage payments recorded for this project.</Text>
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

function Section({ title, children }: React.PropsWithChildren<{ title: string }>) {
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
  if (!form) return null;
  const patch = (value: Partial<SourceForm>) =>
    setForm((current) => (current ? { ...current, ...value } : current));

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <ScrollView contentContainerStyle={styles.modal} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>{form.id ? "Edit source" : "Add source"}</Text>
        <Field label="Name" value={form.name} onChangeText={(name) => patch({ name })} />
        {!form.id ? (
          <>
            <Text style={styles.label}>Source type</Text>
            <Choice label="Contractor" selected={form.source_type === "CONTRACTOR"}
              onPress={() => patch({ source_type: "CONTRACTOR" })} />
            <Choice label="Direct workforce" selected={form.source_type === "DIRECT"}
              onPress={() => patch({ source_type: "DIRECT" })} />
          </>
        ) : null}
        <Field label="Contact name" value={form.contact_name}
          onChangeText={(contact_name) => patch({ contact_name })} />
        <Field label="Contact phone" value={form.contact_phone}
          onChangeText={(contact_phone) => patch({ contact_phone })}
          keyboardType="phone-pad" />
        <Field label="Notes" value={form.notes} onChangeText={(notes) => patch({ notes })}
          multiline />
        <Toggle label="Active taxpayer" value={form.is_active_taxpayer}
          onValueChange={(is_active_taxpayer) => patch({ is_active_taxpayer })} />
        {form.id ? (
          <Toggle label="Source active" value={form.is_active}
            onValueChange={(is_active) => patch({ is_active })} />
        ) : null}
        <Action label={busy ? "Saving…" : "Save source"} disabled={busy || !form.name.trim()}
          onPress={onSave} />
        <Action label="Cancel" disabled={busy} onPress={onClose} />
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
  if (!form) return null;
  const patch = (value: Partial<WorkerForm>) =>
    setForm((current) => (current ? { ...current, ...value } : current));

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <ScrollView contentContainerStyle={styles.modal} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>{form.id ? "Edit worker" : "Add worker"}</Text>
        {!form.id ? (
          <>
            <Text style={styles.label}>Source</Text>
            {sources.map((source) => (
              <Choice key={source.id} label={source.name}
                selected={form.source_id === source.id}
                onPress={() => patch({ source_id: source.id })} />
            ))}
          </>
        ) : null}
        <Field label="Name" value={form.name} onChangeText={(name) => patch({ name })} />
        <Field label="Trade" value={form.trade} onChangeText={(trade) => patch({ trade })} />
        <Field label="CNIC" value={form.cnic} onChangeText={(cnic) => patch({ cnic })}
          keyboardType="number-pad" />
        <Field label="Phone" value={form.phone} onChangeText={(phone) => patch({ phone })}
          keyboardType="phone-pad" />
        <Field label="Default daily rate (optional)" value={form.default_daily_rate}
          onChangeText={(default_daily_rate) => patch({ default_daily_rate })}
          keyboardType="decimal-pad" />
        {form.id ? (
          <Toggle label="Worker active" value={form.is_active}
            onValueChange={(is_active) => patch({ is_active })} />
        ) : null}
        <Action label={busy ? "Saving…" : "Save worker"}
          disabled={busy || !form.source_id || !form.name.trim() || !form.trade.trim()}
          onPress={onSave} />
        <Action label="Cancel" disabled={busy} onPress={onClose} />
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
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 44, backgroundColor: "#F4F6F8" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8" },
  title: { color: "#17212F", fontSize: 26, fontWeight: "800", marginTop: 18, marginBottom: 12 },
  section: { backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, borderColor: "#E4E7EC", padding: 16, marginTop: 14 },
  sectionTitle: { color: "#17212F", fontSize: 18, fontWeight: "700", marginBottom: 10 },
  card: { backgroundColor: "#FFFFFF", borderColor: "#E4E7EC", borderWidth: 1, borderRadius: 12, padding: 14, marginTop: 10 },
  itemTitle: { color: "#17212F", fontSize: 16, fontWeight: "700" },
  muted: { color: "#667085", fontSize: 14, lineHeight: 20, marginTop: 5 },
  error: { color: "#B42318", fontSize: 14, lineHeight: 20, marginTop: 10 },
  link: { color: "#183153", fontWeight: "700" },
  label: { color: "#344054", fontSize: 14, fontWeight: "600", marginTop: 10, marginBottom: 5 },
  field: { marginTop: 7 },
  input: { minHeight: 48, borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "#FFFFFF", color: "#17212F", fontSize: 15 },
  multiline: { minHeight: 88, textAlignVertical: "top" },
  button: { minHeight: 46, borderRadius: 10, backgroundColor: "#183153", paddingHorizontal: 14, paddingVertical: 12, alignItems: "center", justifyContent: "center", marginTop: 10 },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },
  secondaryButton: { minHeight: 50, borderRadius: 10, borderWidth: 1, borderColor: "#D0D5DD", backgroundColor: "#FFFFFF", padding: 14, marginTop: 10 },
  secondaryButtonText: { color: "#183153", textAlign: "center", fontWeight: "700" },
  choiceList: { gap: 7, marginTop: 6 },
  choice: { borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 9, paddingHorizontal: 12, paddingVertical: 10, marginTop: 6, backgroundColor: "#FFFFFF" },
  choiceSelected: { borderColor: "#183153", backgroundColor: "#EAF0F6" },
  choiceText: { color: "#344054", fontWeight: "600" },
  choiceTextSelected: { color: "#183153" },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 10, paddingVertical: 8, borderTopWidth: 1, borderTopColor: "#F0F2F5" },
  infoValue: { color: "#17212F", fontSize: 14, fontWeight: "700", textAlign: "right", flexShrink: 1 },
  toggle: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 8 },
  modal: { flexGrow: 1, backgroundColor: "#F4F6F8", padding: 20, paddingTop: 42, paddingBottom: 40 },
});
import { useCallback, useState } from "react";
import {ActivityIndicator, Alert, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from "react-native";
import {Stack, router, useFocusEffect, useLocalSearchParams,
} from "expo-router";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { restoreSession } from "../../../../../api/client";
import { getProject } from "../../../../../api/projects";
import {cancelSubcontractorBill, createAgreementAdvance, createAgreementBill, createAgreementPayment, downloadSubcontractorBillPdf, downloadSubcontractorBillXlsx, getAgreement, getAgreementLedger,
  getSubcontractorBill, issueSubcontractorBill, listAgreementAdvances, listAgreementBills, listAgreementPayments, updateAgreement,
} from "../../../../../api/subcontractors";
import type {AuthUser, Project, SubcontractAgreementDetail, SubcontractAgreementStatus, SubcontractorAdvance, SubcontractorBill, SubcontractorBillCreatePayload, SubcontractorBillDetail, SubcontractorLedger,
  SubcontractorPayment,
} from "../../../../../api/types";

type FormName = "agreement" | "bill" | "advance" | "payment" | null;
type Percentages = Record<string, string>;

const today = () => new Date().toISOString().slice(0, 10);

export default function SubcontractAgreementScreen() {
  const params = useLocalSearchParams<{
    projectId?: string;
    agreementId?: string;
  }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;
  const agreementId = Array.isArray(params.agreementId)
    ? params.agreementId[0]
    : params.agreementId;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [agreement, setAgreement] =
    useState<SubcontractAgreementDetail | null>(null);
  const [bills, setBills] = useState<SubcontractorBill[]>([]);
  const [advances, setAdvances] = useState<SubcontractorAdvance[]>([]);
  const [payments, setPayments] = useState<SubcontractorPayment[]>([]);
  const [ledger, setLedger] = useState<SubcontractorLedger | null>(null);
  const [percentages, setPercentages] = useState<Percentages>({});
  const [selectedBill, setSelectedBill] =
    useState<SubcontractorBillDetail | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sharingBillId, setSharingBillId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormName>(null);

  const [agreementEndDate, setAgreementEndDate] = useState("");
  const [agreementStatus, setAgreementStatus] =
    useState<SubcontractAgreementStatus>("ACTIVE");
  const [agreementRetention, setAgreementRetention] = useState("");

  const [periodStart, setPeriodStart] = useState(today());
  const [periodEnd, setPeriodEnd] = useState(today());
  const [billRetention, setBillRetention] = useState("");
  const [billRetentionCap, setBillRetentionCap] = useState("");
  const [deductions, setDeductions] = useState("0");
  const [deductionNote, setDeductionNote] = useState("");
  const [retentionByGuarantee, setRetentionByGuarantee] = useState(false);
  const [salesTaxAuthority, setSalesTaxAuthority] = useState("");
  const [billNotes, setBillNotes] = useState("");

  const [advanceAmount, setAdvanceAmount] = useState("");
  const [advanceDate, setAdvanceDate] = useState(today());
  const [advanceNotes, setAdvanceNotes] = useState("");

  const [paymentBillId, setPaymentBillId] = useState("");
  const [grossAmount, setGrossAmount] = useState("");
  const [advanceRecovered, setAdvanceRecovered] = useState("0");
  const [whtCategory, setWhtCategory] = useState("");
  const [paymentDate, setPaymentDate] = useState(today());
  const [paymentNotes, setPaymentNotes] = useState("");

  const permissionKeys =
    user?.role.permissions.map((permission) => permission.key) ?? [];
  const canRead = permissionKeys.includes("subcontractor:read");
  const canManage = permissionKeys.includes("subcontractor:manage");
  const canManagePayments = permissionKeys.includes(
    "subcontractor:payment_manage",
  );

  const load = useCallback(async (refresh = false) => {
    try {
      if (refresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      if (!projectId || !agreementId) {
        throw new Error("Project or agreement ID is missing.");
      }

      const currentUser = await restoreSession();
      if (!currentUser) {
        router.replace("/");
        return;
      }
      setUser(currentUser);

      if (
        !currentUser.role.permissions.some(
          (permission) => permission.key === "subcontractor:read",
        )
      ) {
        setAgreement(null);
        setProject(null);
        setBills([]);
        setAdvances([]);
        setPayments([]);
        setLedger(null);
        return;
      }

      const [
        agreementResult,
        billRows,
        advanceRows,
        paymentRows,
        ledgerResult,
        projectResult,
      ] = await Promise.all([
        getAgreement(agreementId),
        listAgreementBills(agreementId),
        listAgreementAdvances(agreementId),
        listAgreementPayments(agreementId),
        getAgreementLedger(agreementId),
        getProject(projectId),
      ]);

      if (agreementResult.project_id !== projectId) {
        throw new Error("This agreement does not belong to the selected project.");
      }

      setAgreement(agreementResult);
      setProject(projectResult);
      setBills(billRows);
      setAdvances(advanceRows);
      setPayments(paymentRows);
      setLedger(ledgerResult);
      setAgreementStatus(agreementResult.status);
      setAgreementRetention(
        String(agreementResult.default_retention_percentage),
      );

      const latestIssued = billRows
        .filter((bill) => bill.status === "ISSUED")
        .sort((a, b) => b.created_at.localeCompare(a.created_at))[0];

      if (latestIssued) {
        const latestDetail = await getSubcontractorBill(latestIssued.id);
        const nextPercentages: Percentages = {};
        for (const line of latestDetail.line_items) {
          nextPercentages[line.agreement_item_id] = String(
            line.cumulative_percentage,
          );
        }
        setPercentages(nextPercentages);
      } else {
        setPercentages(
          Object.fromEntries(
            agreementResult.items.map((item) => [item.id, "0"]),
          ),
        );
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load this agreement.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId, agreementId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function openAgreementForm() {
    if (!agreement) return;
    setAgreementEndDate(agreement.end_date ?? "");
    setAgreementStatus(agreement.status);
    setAgreementRetention(
      String(agreement.default_retention_percentage),
    );
    setError(null);
    setForm("agreement");
  }

  function openBillForm() {
    if (!agreement) return;
    setPeriodStart(today());
    setPeriodEnd(today());
    setBillRetention("");
    setBillRetentionCap("");
    setDeductions("0");
    setDeductionNote("");
    setRetentionByGuarantee(false);
    setSalesTaxAuthority("");
    setBillNotes("");
    setError(null);
    setForm("bill");
  }

  async function saveAgreementChanges() {
    if (!agreement) return;

    const retentionValue = Number(agreementRetention);
    if (
      !Number.isFinite(retentionValue) ||
      retentionValue < 0 ||
      retentionValue > 100
    ) {
      setError("Retention must be between 0 and 100.");
      return;
    }
    if (
      agreementEndDate &&
      !/^\d{4}-\d{2}-\d{2}$/.test(agreementEndDate)
    ) {
      setError("Enter the end date as YYYY-MM-DD.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await updateAgreement(agreement.id, {
        version: agreement.version,
        ...(agreementEndDate ? { end_date: agreementEndDate } : {}),
        status: agreementStatus,
        default_retention_percentage: retentionValue,
      });
      setForm(null);
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not update the agreement. Reload and retry if it changed.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function saveDraftBill() {
    if (!agreement) return;

    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(periodStart) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(periodEnd) ||
      periodEnd < periodStart
    ) {
      setError("Enter a valid bill period; the end date must not precede the start date.");
      return;
    }
    if (!agreement.items.length) {
      setError("This agreement has no billable items.");
      return;
    }

    const measurements = agreement.items.map((item) => ({
      agreement_item_id: item.id,
      cumulative_percentage: Number(percentages[item.id] ?? 0),
    }));

    if (
      measurements.some(
        (measurement) =>
          !Number.isFinite(measurement.cumulative_percentage) ||
          measurement.cumulative_percentage < 0 ||
          measurement.cumulative_percentage > 100,
      )
    ) {
      setError("Each cumulative percentage must be between 0 and 100.");
      return;
    }

    const optionalRetention = billRetention.trim()
      ? Number(billRetention)
      : null;
    const optionalCap = billRetentionCap.trim()
      ? Number(billRetentionCap)
      : null;

    if (
      (optionalRetention !== null &&
        (optionalRetention < 0 || optionalRetention > 100)) ||
      (optionalCap !== null && (optionalCap < 0 || optionalCap > 100))
    ) {
      setError("Retention and retention cap must be between 0 and 100.");
      return;
    }

    const payload: SubcontractorBillCreatePayload = {
      agreement_id: agreement.id,
      period_start: periodStart,
      period_end: periodEnd,
      retention_percentage: optionalRetention,
      retention_cap_percentage: optionalCap,
      other_deductions_amount: Number(deductions || 0),
      other_deductions_note: deductionNote.trim() || null,
      retention_secured_by_guarantee: retentionByGuarantee,
      sales_tax_authority: salesTaxAuthority
        ? (salesTaxAuthority as "PRA" | "SRB" | "KPRA" | "BRA" | "ICT")
        : null,
      notes: billNotes.trim() || null,
      measurements: agreement.items.map((item) => ({
       agreement_item_id: item.id,
       cumulative_percentage: Number(percentages[item.id] ?? 0),
      })),
    };

    if (
      !Number.isFinite(payload.other_deductions_amount) ||
      payload.other_deductions_amount < 0
    ) {
      setError("Other deductions must be zero or greater.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const created = await createAgreementBill(agreement.id, payload);
      setForm(null);
      setSelectedBill(created);
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not generate the draft bill.",
      );
    } finally {
      setSaving(false);
    }
  }

  function confirmBillAction(
    bill: SubcontractorBill,
    action: "issue" | "cancel",
  ) {
    const actionLabel = action === "issue" ? "Issue" : "Cancel";
    Alert.alert(
      `${actionLabel} bill #${bill.bill_number}?`,
      action === "issue"
        ? "This will issue the current draft bill."
        : "This will cancel this bill.",
      [
        { text: "Keep", style: "cancel" },
        {
          text: actionLabel,
          style: action === "cancel" ? "destructive" : "default",
          onPress: () => void performBillAction(bill, action),
        },
      ],
    );
  }

  async function performBillAction(
    bill: SubcontractorBill,
    action: "issue" | "cancel",
  ) {
    setSaving(true);
    setError(null);
    try {
      if (action === "issue") {
        await issueSubcontractorBill(bill.id, bill.version);
      } else {
        await cancelSubcontractorBill(bill.id, bill.version);
      }
      setSelectedBill(null);
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The bill changed or the action could not be completed. Reload and retry.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function openBill(billId: string) {
    setError(null);
    try {
      setSelectedBill(await getSubcontractorBill(billId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load bill details.");
    }
  }

  async function shareBillExport(
    billId: string,
    format: "pdf" | "xlsx",
  ) {
    setSharingBillId(billId);
    setError(null);
    try {
      const bytes =
        format === "pdf"
          ? await downloadSubcontractorBillPdf(billId)
          : await downloadSubcontractorBillXlsx(billId);

      const extension = format;
      const file = new File(
        Paths.cache,
        `subcontractor-bill-${billId}.${extension}`,
      );
      file.create({ overwrite: true });
      file.write(new Uint8Array(bytes));

      if (!(await Sharing.isAvailableAsync())) {
        throw new Error("File sharing is not available on this device.");
      }

      await Sharing.shareAsync(file.uri, {
        mimeType:
          format === "pdf"
            ? "application/pdf"
            : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        dialogTitle: `Share bill ${extension.toUpperCase()}`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not export this bill.");
    } finally {
      setSharingBillId(null);
    }
  }

  async function saveAdvance() {
    if (!agreement) return;
    const amount = Number(advanceAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Advance amount must be greater than zero.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(advanceDate)) {
      setError("Enter the advance date as YYYY-MM-DD.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await createAgreementAdvance(agreement.id, {
        amount,
        advance_date: advanceDate,
        notes: advanceNotes.trim() || null,
      });
      setForm(null);
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record advance.");
    } finally {
      setSaving(false);
    }
  }

  async function savePayment() {
    if (!agreement) return;
    const gross = Number(grossAmount);
    const recovered = Number(advanceRecovered || 0);
    if (!Number.isFinite(gross) || gross <= 0) {
      setError("Gross payment must be greater than zero.");
      return;
    }
    if (!Number.isFinite(recovered) || recovered < 0) {
      setError("Advance recovery must be zero or greater.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(paymentDate)) {
      setError("Enter the payment date as YYYY-MM-DD.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const result = await createAgreementPayment(agreement.id, {
        bill_id: paymentBillId || null,
        gross_amount: gross,
        advance_recovered_amount: recovered,
        wht_category: whtCategory
          ? (whtCategory as "GOODS_SUPPLY" | "SERVICES" | "CONTRACTS_EXECUTION")
          : null,
        payment_date: paymentDate,
        notes: paymentNotes.trim() || null,
      });

      setForm(null);
      await load(true);
      Alert.alert(
        "Payment recorded",
        `WHT deducted: ${result.wht_deducted_amount} · Net paid: ${result.net_paid_amount}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record payment.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: "Subcontract agreement" }} />
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading agreement…</Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: "Subcontract agreement" }} />
        <Text style={styles.title}>Access unavailable</Text>
        <Text style={styles.muted}>
          Your role cannot view subcontractor agreements.
        </Text>
      </View>
    );
  }

  if (error && !agreement) {
    return (
      <View style={styles.page}>
        <Stack.Screen options={{ title: "Subcontract agreement" }} />
        <Text style={styles.error}>{error}</Text>
        <Action label="Try again" onPress={() => void load()} />
      </View>
    );
  }

  if (!agreement) return null;

  return (
    <>
      <Stack.Screen
        options={{
          title: project?.name
            ? `${project.name} · Subcontract`
            : "Subcontract agreement",
        }}
      />

      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => void load(true)}
          />
        }
      >
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  Project subcontractors</Text>
        </Pressable>

        <Text style={styles.eyebrow}>{project?.name ?? "PROJECT"}</Text>
        <Text style={styles.title}>{agreement.scope_description}</Text>
        <Text style={styles.status}>{agreement.status.replaceAll("_", " ")}</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Card title="Agreement">
          <Info label="Contract value" value={money(agreement.contract_value, ledger?.currency)} />
          <Info label="Start date" value={agreement.start_date} />
          <Info label="End date" value={agreement.end_date ?? "Not set"} />
          <Info label="Default retention" value={`${agreement.default_retention_percentage}%`} />
          <Info label="Items" value={String(agreement.items.length)} />
          {agreement.notes ? <Text style={styles.muted}>{agreement.notes}</Text> : null}
          {canManage ? (
            <Action label="Edit agreement settings" onPress={openAgreementForm} />
          ) : null}
        </Card>

        <Card title="Ledger">
          <Info label="Total billed" value={money(ledger?.total_billed, ledger?.currency)} />
          <Info label="Total paid" value={money(ledger?.total_paid, ledger?.currency)} />
          <Info label="Outstanding bill balance" value={money(ledger?.outstanding_bill_balance, ledger?.currency)} />
          <Info label="Advances given" value={money(ledger?.total_advances_given, ledger?.currency)} />
          <Info label="Outstanding advance balance" value={money(ledger?.outstanding_advance_balance, ledger?.currency)} />
        </Card>

        <Card title="Contract items">
          {agreement.items.map((item) => (
            <View key={item.id} style={styles.item}>
              <Text style={styles.cardTitle}>{item.description}</Text>
              <Text style={styles.muted}>
                {item.quantity} {item.unit} · Rate {money(item.rate, ledger?.currency)}
              </Text>
            </View>
          ))}
        </Card>

        <Card title="Bills">
          {canManage ? (
            <Action label="Generate draft bill" primary onPress={openBillForm} />
          ) : null}
          {bills.length === 0 ? (
            <Text style={styles.muted}>No bills for this agreement.</Text>
          ) : bills.map((bill) => (
            <View key={bill.id} style={styles.item}>
              <Text style={styles.cardTitle}>
                Bill #{bill.bill_number} · {bill.status}
              </Text>
              <Text style={styles.muted}>
                {bill.period_start} to {bill.period_end}
              </Text>
              <Info label="Gross this period" value={money(bill.gross_value_this_period, bill.currency)} />
              <Info label="Retention" value={money(bill.retention_this_period, bill.currency)} />
              <Info label="Net payable" value={money(bill.net_payable, bill.currency)} />
              <Info label="Tax" value={money(bill.sales_tax_amount, bill.currency)} />
              <Info label="Total due" value={money(bill.total_amount_due, bill.currency)} />
              <Action label="View bill details" onPress={() => void openBill(bill.id)} />
              <View style={styles.buttonRow}>
                <Action
                  label={sharingBillId === bill.id ? "Preparing PDF…" : "Share PDF"}
                  disabled={sharingBillId !== null}
                  onPress={() => void shareBillExport(bill.id, "pdf")}
                />
                <Action
                  label={sharingBillId === bill.id ? "Preparing Excel…" : "Share Excel"}
                  disabled={sharingBillId !== null}
                  onPress={() => void shareBillExport(bill.id, "xlsx")}
                />
              </View>
              {canManage && bill.status === "DRAFT" ? (
                <Action
                  label="Issue bill"
                  primary
                  disabled={saving}
                  onPress={() => confirmBillAction(bill, "issue")}
                />
              ) : null}
              {canManage && bill.status !== "CANCELLED" ? (
                <Action
                  label="Cancel bill"
                  danger
                  disabled={saving}
                  onPress={() => confirmBillAction(bill, "cancel")}
                />
              ) : null}
            </View>
          ))}
        </Card>

        {selectedBill ? (
          <Card title={`Bill #${selectedBill.bill_number} details`}>
            <Info label="Status" value={selectedBill.status} />
            {selectedBill.line_items.map((line) => (
              <View key={line.id} style={styles.item}>
                <Text style={styles.cardTitle}>{line.description}</Text>
                <Info
                  label="Cumulative progress"
                  value={`${line.cumulative_percentage}%`}
                />
                <Info
                  label="This period"
                  value={money(line.this_period_value, selectedBill.currency)}
                />
                <Info
                  label="Cumulative value"
                  value={money(line.cumulative_value, selectedBill.currency)}
                />
              </View>
            ))}
            <Action label="Close details" onPress={() => setSelectedBill(null)} />
          </Card>
        ) : null}

        <Card title="Advances">
          {canManagePayments ? (
            <Action label="Record advance" onPress={() => {
              setAdvanceAmount("");
              setAdvanceDate(today());
              setAdvanceNotes("");
              setError(null);
              setForm("advance");
            }} />
          ) : null}
          {advances.length === 0 ? (
            <Text style={styles.muted}>No advances recorded.</Text>
          ) : advances.map((advance) => (
            <View key={advance.id} style={styles.item}>
              <Info label={advance.advance_date} value={money(advance.amount, ledger?.currency)} />
              {advance.notes ? <Text style={styles.muted}>{advance.notes}</Text> : null}
            </View>
          ))}
        </Card>

        <Card title="Payments">
          {canManagePayments ? (
            <Action label="Record payment" onPress={() => {
              setPaymentBillId("");
              setGrossAmount("");
              setAdvanceRecovered("0");
              setWhtCategory("");
              setPaymentDate(today());
              setPaymentNotes("");
              setError(null);
              setForm("payment");
            }} />
          ) : null}
          {payments.length === 0 ? (
            <Text style={styles.muted}>No payments recorded.</Text>
          ) : payments.map((payment) => (
            <View key={payment.id} style={styles.item}>
              <Info label={payment.payment_date} value={money(payment.net_paid_amount, ledger?.currency)} />
              <Info label="Gross" value={money(payment.gross_amount, ledger?.currency)} />
              <Info label="Advance recovered" value={money(payment.advance_recovered_amount, ledger?.currency)} />
              <Info label="WHT deducted" value={money(payment.wht_deducted_amount, ledger?.currency)} />
              {payment.notes ? <Text style={styles.muted}>{payment.notes}</Text> : null}
            </View>
          ))}
        </Card>
      </ScrollView>

      <Modal
        visible={form !== null}
        animationType="slide"
        onRequestClose={() => setForm(null)}
      >
        <ScrollView contentContainerStyle={styles.page}>
          {form === "agreement" ? (
            <>
              <Text style={styles.title}>Agreement settings</Text>
              <Field
                label="End date (YYYY-MM-DD, leave blank to keep current)"
                value={agreementEndDate}
                onChangeText={setAgreementEndDate}
              />
              <Text style={styles.label}>Status</Text>
              <View style={styles.buttonRow}>
                {(["ACTIVE", "COMPLETED", "TERMINATED"] as const).map((value) => (
                  <Action
                    key={value}
                    label={agreementStatus === value ? `✓ ${value}` : value}
                    onPress={() => setAgreementStatus(value)}
                  />
                ))}
              </View>
              <Field
                label="Default retention percentage"
                value={agreementRetention}
                onChangeText={setAgreementRetention}
                keyboardType="decimal-pad"
              />
              <Action
                label={saving ? "Saving…" : "Save agreement"}
                primary
                disabled={saving}
                onPress={() => void saveAgreementChanges()}
              />
            </>
          ) : null}

          {form === "bill" ? (
            <>
              <Text style={styles.title}>Generate draft bill</Text>
              <Field label="Period start (YYYY-MM-DD)" value={periodStart} onChangeText={setPeriodStart} />
              <Field label="Period end (YYYY-MM-DD)" value={periodEnd} onChangeText={setPeriodEnd} />

              <Text style={styles.sectionTitle}>Cumulative progress by item</Text>
              {agreement.items.map((item) => (
                <Field
                  key={item.id}
                  label={`${item.description} (%)`}
                  value={percentages[item.id] ?? "0"}
                  onChangeText={(value) =>
                    setPercentages((current) => ({ ...current, [item.id]: value }))
                  }
                  keyboardType="decimal-pad"
                />
              ))}

              <Field label="Retention override % (optional)" value={billRetention} onChangeText={setBillRetention} keyboardType="decimal-pad" />
              <Field label="Retention cap % (optional)" value={billRetentionCap} onChangeText={setBillRetentionCap} keyboardType="decimal-pad" />
              <Field label="Other deductions" value={deductions} onChangeText={setDeductions} keyboardType="decimal-pad" />
              <Field label="Deduction note (optional)" value={deductionNote} onChangeText={setDeductionNote} multiline />

              <View style={styles.switchRow}>
                <Text style={styles.body}>Retention secured by guarantee</Text>
                <Switch
                  value={retentionByGuarantee}
                  onValueChange={setRetentionByGuarantee}
                />
              </View>

              <Text style={styles.label}>Sales-tax authority (optional)</Text>
              <View style={styles.buttonRow}>
                {["", "PRA", "SRB", "KPRA", "BRA", "ICT"].map((value) => (
                  <Action
                    key={value || "none"}
                    label={salesTaxAuthority === value ? `✓ ${value || "None"}` : value || "None"}
                    onPress={() => setSalesTaxAuthority(value)}
                  />
                ))}
              </View>

              <Field label="Bill notes (optional)" value={billNotes} onChangeText={setBillNotes} multiline />
              <Action
                label={saving ? "Generating…" : "Generate draft"}
                primary
                disabled={saving}
                onPress={() => void saveDraftBill()}
              />
            </>
          ) : null}

          {form === "advance" ? (
            <>
              <Text style={styles.title}>Record advance</Text>
              <Field label="Amount" value={advanceAmount} onChangeText={setAdvanceAmount} keyboardType="decimal-pad" />
              <Field label="Date (YYYY-MM-DD)" value={advanceDate} onChangeText={setAdvanceDate} />
              <Field label="Notes (optional)" value={advanceNotes} onChangeText={setAdvanceNotes} multiline />
              <Action label={saving ? "Saving…" : "Record advance"} primary disabled={saving} onPress={() => void saveAdvance()} />
            </>
          ) : null}

          {form === "payment" ? (
            <>
              <Text style={styles.title}>Record payment</Text>
              <Text style={styles.label}>Bill (optional)</Text>
              <Action label={paymentBillId ? "Clear selected bill" : "No bill selected"} onPress={() => setPaymentBillId("")} />
              {bills.filter((bill) => bill.status === "ISSUED").map((bill) => (
                <Action
                  key={bill.id}
                  label={paymentBillId === bill.id ? `✓ Bill #${bill.bill_number}` : `Bill #${bill.bill_number}`}
                  onPress={() => setPaymentBillId(bill.id)}
                />
              ))}
              <Field label="Gross amount" value={grossAmount} onChangeText={setGrossAmount} keyboardType="decimal-pad" />
              <Field label="Advance recovery" value={advanceRecovered} onChangeText={setAdvanceRecovered} keyboardType="decimal-pad" />
              <Text style={styles.label}>Withholding category (optional)</Text>
              <View style={styles.buttonRow}>
                {[
                  ["", "None"],
                  ["GOODS_SUPPLY", "Goods"],
                  ["SERVICES", "Services"],
                  ["CONTRACTS_EXECUTION", "Contracts"],
                ].map(([value, label]) => (
                  <Action
                    key={value || "none"}
                    label={whtCategory === value ? `✓ ${label}` : label}
                    onPress={() => setWhtCategory(value)}
                  />
                ))}
              </View>
              <Field label="Payment date (YYYY-MM-DD)" value={paymentDate} onChangeText={setPaymentDate} />
              <Field label="Notes (optional)" value={paymentNotes} onChangeText={setPaymentNotes} multiline />
              <Action label={saving ? "Saving…" : "Record payment"} primary disabled={saving} onPress={() => void savePayment()} />
            </>
          ) : null}

          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Action label="Close" disabled={saving} onPress={() => setForm(null)} />
        </ScrollView>
      </Modal>
    </>
  );
}

function money(value: number | string | null | undefined, currency?: string) {
  if (value == null) return "—";
  return `${currency ? `${currency} ` : ""}${Number(value).toLocaleString()}`;
}

function Card(props: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.card}>
      <Text style={styles.sectionTitle}>{props.title}</Text>
      {props.children}
    </View>
  );
}

function Info(props: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.muted}>{props.label}</Text>
      <Text style={styles.body}>{props.value}</Text>
    </View>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  multiline?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{props.label}</Text>
      <TextInput
        style={[styles.input, props.multiline && styles.multiline]}
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType={props.keyboardType ?? "default"}
        multiline={props.multiline}
      />
    </View>
  );
}

function Action(props: {
  label: string;
  onPress: () => void;
  primary?: boolean;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={props.disabled}
      onPress={props.onPress}
      style={[
        styles.button,
        props.primary && styles.primaryButton,
        props.danger && styles.dangerButton,
        props.disabled && styles.disabled,
      ]}
    >
      <Text
        style={[
          styles.buttonText,
          props.primary && styles.primaryText,
          props.danger && styles.dangerText,
        ]}
      >
        {props.label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 18, gap: 12, backgroundColor: "#F4F6F8" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 10, backgroundColor: "#F4F6F8" },
  eyebrow: { color: "#8A7B67", fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  title: { color: "#17212F", fontSize: 22, fontWeight: "800" },
  sectionTitle: { color: "#17212F", fontSize: 17, fontWeight: "800", marginBottom: 4 },
  cardTitle: { color: "#17212F", fontSize: 15, fontWeight: "800" },
  status: { color: "#183153", fontSize: 12, fontWeight: "800" },
  body: { color: "#17212F", fontSize: 14 },
  muted: { color: "#667085", fontSize: 13 },
  label: { color: "#344054", fontSize: 13, fontWeight: "700" },
  link: { color: "#183153", fontWeight: "700" },
  error: { color: "#B42318", fontSize: 14, paddingVertical: 5 },
  card: { backgroundColor: "#FFFFFF", borderRadius: 13, borderWidth: 1, borderColor: "#D8DEE6", padding: 15, gap: 9 },
  item: { borderTopWidth: 1, borderTopColor: "#EAECF0", paddingTop: 10, gap: 7 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10 },
  field: { gap: 5 },
  input: { minHeight: 43, borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 9, backgroundColor: "#FFFFFF", paddingHorizontal: 11, color: "#17212F" },
  multiline: { minHeight: 74, textAlignVertical: "top", paddingTop: 9 },
  buttonRow: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  switchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  button: { minHeight: 41, borderWidth: 1, borderColor: "#D0D5DD", backgroundColor: "#FFFFFF", borderRadius: 9, alignItems: "center", justifyContent: "center", paddingHorizontal: 12 },
  buttonText: { color: "#183153", fontSize: 13, fontWeight: "700" },
  primaryButton: { backgroundColor: "#183153", borderColor: "#183153" },
  primaryText: { color: "#FFFFFF" },
  dangerButton: { borderColor: "#FDA29B" },
  dangerText: { color: "#B42318" },
  disabled: { opacity: 0.5 },
});
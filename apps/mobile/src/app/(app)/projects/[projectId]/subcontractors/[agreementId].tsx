import { useCallback, useState } from "react";
import {ActivityIndicator, Alert, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from "react-native";
import {Stack, router, useFocusEffect, useLocalSearchParams,
} from "expo-router";
import { useTranslation } from "react-i18next";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import LanguageSwitcher from "../../../../../components/LanguageSwitcher";
import { restoreSession } from "../../../../../api/client";
import { getProject } from "../../../../../api/projects";
import {cancelSubcontractorBill, createAgreementAdvance, createAgreementBill, createAgreementPayment, downloadSubcontractorBillPdf, downloadSubcontractorBillXlsx, getAgreement, getAgreementLedger,
  getSubcontractorBill, issueSubcontractorBill, listAgreementAdvances, listAgreementBills, listAgreementPayments, updateAgreement,
} from "../../../../../api/subcontractors";
import type {AuthUser, Project, SubcontractAgreementDetail, SubcontractAgreementStatus, SubcontractorAdvance, SubcontractorBill, SubcontractorBillCreatePayload, SubcontractorBillDetail, SubcontractorLedger,
  SubcontractorPayment,
} from "../../../../../api/types";

const PAGE_SIZE = 3;

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
  amber: "#A96516",
  amberBg: "#F8EDDA",
  red: "#A33A32",
  redBg: "#F9E9E5",
};

type FormName = "agreement" | "bill" | "advance" | "payment" | null;
type Percentages = Record<string, string>;

const today = () => new Date().toISOString().slice(0, 10);

export default function SubcontractAgreementScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

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

  const [billsPage, setBillsPage] = useState(1);
  const [advancesPage, setAdvancesPage] = useState(1);
  const [paymentsPage, setPaymentsPage] = useState(1);

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

  const load = useCallback(
    async (refresh = false) => {
      try {
        if (refresh) setRefreshing(true);
        else setLoading(true);
        setError(null);

        if (!projectId || !agreementId) {
          throw new Error(t("subcontractAgreement.idsMissing"));
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
          throw new Error(t("subcontractAgreement.projectMismatch"));
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
        setBillsPage(1);
        setAdvancesPage(1);
        setPaymentsPage(1);

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
          err instanceof Error
            ? err.message
            : t("subcontractAgreement.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, agreementId, t],
  );

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
      setError(t("subcontractAgreement.retentionRange"));
      return;
    }
    if (
      agreementEndDate &&
      !/^\d{4}-\d{2}-\d{2}$/.test(agreementEndDate)
    ) {
      setError(t("subcontractAgreement.endDateFormat"));
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
          : t("subcontractAgreement.updateFailure"),
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
      setError(t("subcontractAgreement.billPeriodInvalid"));
      return;
    }
    if (!agreement.items.length) {
      setError(t("subcontractAgreement.noBillableItems"));
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
      setError(t("subcontractAgreement.cumulativePercentageRange"));
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
      setError(t("subcontractAgreement.retentionAndCapRange"));
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
      setError(t("subcontractAgreement.deductionsRange"));
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
        err instanceof Error
          ? err.message
          : t("subcontractAgreement.billCreateFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  function confirmBillAction(
    bill: SubcontractorBill,
    action: "issue" | "cancel",
  ) {
    const actionLabel = t(`subcontractAgreement.billAction.${action}`);
    Alert.alert(
      t("subcontractAgreement.billActionTitle", {
        action: actionLabel,
        number: bill.bill_number,
      }),
      t(`subcontractAgreement.billActionMessage.${action}`),
      [
        { text: t("subcontractAgreement.keep"), style: "cancel" },
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
          : t("subcontractAgreement.billActionFailure"),
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
      setError(
        err instanceof Error
          ? err.message
          : t("subcontractAgreement.billDetailFailure"),
      );
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

      const file = new File(
        Paths.cache,
        `subcontractor-bill-${billId}.${format}`,
      );
      file.create({ overwrite: true });
      file.write(new Uint8Array(bytes));

      if (!(await Sharing.isAvailableAsync())) {
        throw new Error(t("subcontractAgreement.sharingUnavailable"));
      }

      await Sharing.shareAsync(file.uri, {
        mimeType:
          format === "pdf"
            ? "application/pdf"
            : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        dialogTitle: t("subcontractAgreement.shareBillTitle", {
          format: format.toUpperCase(),
        }),
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("subcontractAgreement.exportFailure"),
      );
    } finally {
      setSharingBillId(null);
    }
  }

  async function saveAdvance() {
    if (!agreement) return;
    const amount = Number(advanceAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError(t("subcontractAgreement.advanceAmountPositive"));
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(advanceDate)) {
      setError(t("subcontractAgreement.advanceDateFormat"));
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
      setError(
        err instanceof Error
          ? err.message
          : t("subcontractAgreement.advanceFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  async function savePayment() {
    if (!agreement) return;
    const gross = Number(grossAmount);
    const recovered = Number(advanceRecovered || 0);
    if (!Number.isFinite(gross) || gross <= 0) {
      setError(t("subcontractAgreement.grossPaymentPositive"));
      return;
    }
    if (!Number.isFinite(recovered) || recovered < 0) {
      setError(t("subcontractAgreement.advanceRecoveryRange"));
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(paymentDate)) {
      setError(t("subcontractAgreement.paymentDateFormat"));
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
          ? (whtCategory as
              | "GOODS_SUPPLY"
              | "SERVICES"
              | "CONTRACTS_EXECUTION")
          : null,
        payment_date: paymentDate,
        notes: paymentNotes.trim() || null,
      });

      setForm(null);
      await load(true);
      Alert.alert(
        t("subcontractAgreement.paymentRecorded"),
        t("subcontractAgreement.paymentResult", {
          deducted: result.wht_deducted_amount,
          net: result.net_paid_amount,
        }),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("subcontractAgreement.paymentFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  const billsTotalPages = Math.ceil(bills.length / PAGE_SIZE);
  const advancesTotalPages = Math.ceil(advances.length / PAGE_SIZE);
  const paymentsTotalPages = Math.ceil(payments.length / PAGE_SIZE);
  const visibleBills = bills.slice(
    (billsPage - 1) * PAGE_SIZE,
    billsPage * PAGE_SIZE,
  );
  const visibleAdvances = advances.slice(
    (advancesPage - 1) * PAGE_SIZE,
    advancesPage * PAGE_SIZE,
  );
  const visiblePayments = payments.slice(
    (paymentsPage - 1) * PAGE_SIZE,
    paymentsPage * PAGE_SIZE,
  );

  const currentFormTitle = form
    ? t(`subcontractAgreement.formTitle.${form}`)
    : "";

  if (loading) {
    return (
      <View style={[styles.page, isUrdu && styles.rtlPage]}>
        <Stack.Screen
          options={{ title: t("subcontractAgreement.screenTitle") }}
        />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("subcontractAgreement.screenTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.navy} />
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("subcontractAgreement.loading")}
          </Text>
        </View>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={[styles.page, isUrdu && styles.rtlPage]}>
        <Stack.Screen
          options={{ title: t("subcontractAgreement.screenTitle") }}
        />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("subcontractAgreement.screenTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("subcontractAgreement.accessDenied")}
        </Text>
      </View>
    );
  }

  if (error && !agreement) {
    return (
      <View style={[styles.page, isUrdu && styles.rtlPage]}>
        <Stack.Screen
          options={{ title: t("subcontractAgreement.screenTitle") }}
        />
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Text style={[styles.title, isUrdu && styles.rtlText]}>
            {t("subcontractAgreement.screenTitle")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
        <Action
          label={t("subcontractAgreement.tryAgain")}
          onPress={() => void load()}
        />
      </View>
    );
  }

  if (!agreement) return null;

  return (
    <>
      <Stack.Screen
        options={{
          title: project?.name
            ? t("subcontractAgreement.stackTitle", { name: project.name })
            : t("subcontractAgreement.screenTitle"),
        }}
      />

      <ScrollView
        contentContainerStyle={[
          styles.page,
          isUrdu && styles.rtlPage,
        ]}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => void load(true)}
            tintColor={C.navy}
            colors={[C.navy]}
          />
        }
      >
        <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
          <Pressable onPress={() => router.back()}>
            <Text style={styles.link}>
              {t("subcontractAgreement.backToProject")}
            </Text>
          </Pressable>
          <LanguageSwitcher />
        </View>

        <Text style={[styles.eyebrow, isUrdu && styles.rtlText]}>
          {project?.name ?? t("subcontractAgreement.project")}
        </Text>
        <Text style={[styles.title, isUrdu && styles.rtlText]}>
          {agreement.scope_description}
        </Text>
        <Text style={styles.status}>
          {t(`subcontractAgreement.agreementStatus.${agreement.status.toLowerCase()}`, {
            defaultValue: agreement.status.replaceAll("_", " "),
          })}
        </Text>

        {error ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
        ) : null}

        <Card title={t("subcontractAgreement.agreement")}>
          <Info
            label={t("subcontractAgreement.contractValue")}
            value={money(agreement.contract_value, ledger?.currency)}
          />
          <Info
            label={t("subcontractAgreement.startDate")}
            value={agreement.start_date}
          />
          <Info
            label={t("subcontractAgreement.endDate")}
            value={
              agreement.end_date ?? t("subcontractAgreement.notSet")
            }
          />
          <Info
            label={t("subcontractAgreement.defaultRetention")}
            value={`${agreement.default_retention_percentage}%`}
          />
          <Info
            label={t("subcontractAgreement.items")}
            value={String(agreement.items.length)}
          />
          {agreement.notes ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {agreement.notes}
            </Text>
          ) : null}
          {canManage ? (
            <Action
              label={t("subcontractAgreement.editSettings")}
              onPress={openAgreementForm}
            />
          ) : null}
        </Card>

        <Card title={t("subcontractAgreement.ledger")}>
          <Info
            label={t("subcontractAgreement.totalBilled")}
            value={money(ledger?.total_billed, ledger?.currency)}
          />
          <Info
            label={t("subcontractAgreement.totalPaid")}
            value={money(ledger?.total_paid, ledger?.currency)}
          />
          <Info
            label={t("subcontractAgreement.outstandingBillBalance")}
            value={money(ledger?.outstanding_bill_balance, ledger?.currency)}
          />
          <Info
            label={t("subcontractAgreement.advancesGiven")}
            value={money(ledger?.total_advances_given, ledger?.currency)}
          />
          <Info
            label={t("subcontractAgreement.outstandingAdvanceBalance")}
            value={money(
              ledger?.outstanding_advance_balance,
              ledger?.currency,
            )}
          />
        </Card>

        <Card title={t("subcontractAgreement.contractItems")}>
          {agreement.items.map((item) => (
            <View key={item.id} style={styles.item}>
              <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                {item.description}
              </Text>
              <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                {t("subcontractAgreement.itemRate", {
                  quantity: item.quantity,
                  unit: item.unit,
                  rate: money(item.rate, ledger?.currency),
                })}
              </Text>
            </View>
          ))}
        </Card>

        <Card title={t("subcontractAgreement.bills")}>
          {canManage ? (
            <Action
              label={t("subcontractAgreement.generateDraftBill")}
              primary
              onPress={openBillForm}
            />
          ) : null}
          {bills.length === 0 ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("subcontractAgreement.noBills")}
            </Text>
          ) : (
            <>
              {visibleBills.map((bill) => (
                <View key={bill.id} style={styles.item}>
                  <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                    {t("subcontractAgreement.billTitle", {
                      number: bill.bill_number,
                      status: t(
                        `subcontractAgreement.billStatus.${bill.status.toLowerCase()}`,
                        { defaultValue: bill.status },
                      ),
                    })}
                  </Text>
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("subcontractAgreement.billPeriod", {
                      start: bill.period_start,
                      end: bill.period_end,
                    })}
                  </Text>
                  <Info
                    label={t("subcontractAgreement.grossThisPeriod")}
                    value={money(bill.gross_value_this_period, bill.currency)}
                  />
                  <Info
                    label={t("subcontractAgreement.retention")}
                    value={money(bill.retention_this_period, bill.currency)}
                  />
                  <Info
                    label={t("subcontractAgreement.netPayable")}
                    value={money(bill.net_payable, bill.currency)}
                  />
                  <Info
                    label={t("subcontractAgreement.tax")}
                    value={money(bill.sales_tax_amount, bill.currency)}
                  />
                  <Info
                    label={t("subcontractAgreement.totalDue")}
                    value={money(bill.total_amount_due, bill.currency)}
                  />
                  <Action
                    label={t("subcontractAgreement.viewBillDetails")}
                    onPress={() => void openBill(bill.id)}
                  />
                  <View style={[styles.buttonRow, isUrdu && styles.rtlRow]}>
                    <Action
                      label={
                        sharingBillId === bill.id
                          ? t("subcontractAgreement.preparingPdf")
                          : t("subcontractAgreement.sharePdf")
                      }
                      disabled={sharingBillId !== null}
                      onPress={() => void shareBillExport(bill.id, "pdf")}
                    />
                    <Action
                      label={
                        sharingBillId === bill.id
                          ? t("subcontractAgreement.preparingExcel")
                          : t("subcontractAgreement.shareExcel")
                      }
                      disabled={sharingBillId !== null}
                      onPress={() => void shareBillExport(bill.id, "xlsx")}
                    />
                  </View>
                  {canManage && bill.status === "DRAFT" ? (
                    <Action
                      label={t("subcontractAgreement.issueBill")}
                      primary
                      disabled={saving}
                      onPress={() => confirmBillAction(bill, "issue")}
                    />
                  ) : null}
                  {canManage && bill.status !== "CANCELLED" ? (
                    <Action
                      label={t("subcontractAgreement.cancelBill")}
                      danger
                      disabled={saving}
                      onPress={() => confirmBillAction(bill, "cancel")}
                    />
                  ) : null}
                </View>
              ))}
              <Pagination
                page={billsPage}
                totalPages={billsTotalPages}
                onPageChange={setBillsPage}
              />
            </>
          )}
        </Card>

        {selectedBill ? (
          <Card
            title={t("subcontractAgreement.billDetailsTitle", {
              number: selectedBill.bill_number,
            })}
          >
            <Info
              label={t("subcontractAgreement.status")}
              value={t(
                `subcontractAgreement.billStatus.${selectedBill.status.toLowerCase()}`,
                { defaultValue: selectedBill.status },
              )}
            />
            {selectedBill.line_items.map((line) => (
              <View key={line.id} style={styles.item}>
                <Text style={[styles.cardTitle, isUrdu && styles.rtlText]}>
                  {line.description}
                </Text>
                <Info
                  label={t("subcontractAgreement.cumulativeProgress")}
                  value={`${line.cumulative_percentage}%`}
                />
                <Info
                  label={t("subcontractAgreement.thisPeriod")}
                  value={money(line.this_period_value, selectedBill.currency)}
                />
                <Info
                  label={t("subcontractAgreement.cumulativeValue")}
                  value={money(line.cumulative_value, selectedBill.currency)}
                />
              </View>
            ))}
            <Action
              label={t("subcontractAgreement.closeDetails")}
              onPress={() => setSelectedBill(null)}
            />
          </Card>
        ) : null}

        <Card title={t("subcontractAgreement.advances")}>
          {canManagePayments ? (
            <Action
              label={t("subcontractAgreement.recordAdvance")}
              onPress={() => {
                setAdvanceAmount("");
                setAdvanceDate(today());
                setAdvanceNotes("");
                setError(null);
                setForm("advance");
              }}
            />
          ) : null}
          {advances.length === 0 ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("subcontractAgreement.noAdvances")}
            </Text>
          ) : (
            <>
              {visibleAdvances.map((advance) => (
                <View key={advance.id} style={styles.item}>
                  <Info
                    label={advance.advance_date}
                    value={money(advance.amount, ledger?.currency)}
                  />
                  {advance.notes ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {advance.notes}
                    </Text>
                  ) : null}
                </View>
              ))}
              <Pagination
                page={advancesPage}
                totalPages={advancesTotalPages}
                onPageChange={setAdvancesPage}
              />
            </>
          )}
        </Card>

        <Card title={t("subcontractAgreement.payments")}>
          {canManagePayments ? (
            <Action
              label={t("subcontractAgreement.recordPayment")}
              onPress={() => {
                setPaymentBillId("");
                setGrossAmount("");
                setAdvanceRecovered("0");
                setWhtCategory("");
                setPaymentDate(today());
                setPaymentNotes("");
                setError(null);
                setForm("payment");
              }}
            />
          ) : null}
          {payments.length === 0 ? (
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("subcontractAgreement.noPayments")}
            </Text>
          ) : (
            <>
              {visiblePayments.map((payment) => (
                <View key={payment.id} style={styles.item}>
                  <Info
                    label={payment.payment_date}
                    value={money(payment.net_paid_amount, ledger?.currency)}
                  />
                  <Info
                    label={t("subcontractAgreement.gross")}
                    value={money(payment.gross_amount, ledger?.currency)}
                  />
                  <Info
                    label={t("subcontractAgreement.advanceRecovered")}
                    value={money(
                      payment.advance_recovered_amount,
                      ledger?.currency,
                    )}
                  />
                  <Info
                    label={t("subcontractAgreement.whtDeducted")}
                    value={money(payment.wht_deducted_amount, ledger?.currency)}
                  />
                  {payment.notes ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {payment.notes}
                    </Text>
                  ) : null}
                </View>
              ))}
              <Pagination
                page={paymentsPage}
                totalPages={paymentsTotalPages}
                onPageChange={setPaymentsPage}
              />
            </>
          )}
        </Card>
      </ScrollView>

      <Modal
        visible={form !== null}
        animationType="slide"
        onRequestClose={() => setForm(null)}
      >
        <ScrollView
          contentContainerStyle={[
            styles.page,
            isUrdu && styles.rtlPage,
          ]}
        >
          <View style={[styles.topBar, isUrdu && styles.rtlRow]}>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {currentFormTitle}
            </Text>
            <LanguageSwitcher />
          </View>

          {form === "agreement" ? (
            <>
              <Field
                label={t("subcontractAgreement.endDateHelp")}
                value={agreementEndDate}
                onChangeText={setAgreementEndDate}
              />
              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("subcontractAgreement.status")}
              </Text>
              <View style={[styles.buttonRow, isUrdu && styles.rtlRow]}>
                {(["ACTIVE", "COMPLETED", "TERMINATED"] as const).map(
                  (value) => (
                    <Action
                      key={value}
                      label={t(
                        `subcontractAgreement.agreementStatus.${value.toLowerCase()}`,
                        { defaultValue: value },
                      )}
                      selected={agreementStatus === value}
                      onPress={() => setAgreementStatus(value)}
                    />
                  ),
                )}
              </View>
              <Field
                label={t("subcontractAgreement.defaultRetentionPercentage")}
                value={agreementRetention}
                onChangeText={setAgreementRetention}
                keyboardType="decimal-pad"
              />
              <Action
                label={
                  saving
                    ? t("subcontractAgreement.saving")
                    : t("subcontractAgreement.saveAgreement")
                }
                primary
                disabled={saving}
                onPress={() => void saveAgreementChanges()}
              />
            </>
          ) : null}

          {form === "bill" ? (
            <>
              <Field
                label={t("subcontractAgreement.periodStart")}
                value={periodStart}
                onChangeText={setPeriodStart}
              />
              <Field
                label={t("subcontractAgreement.periodEnd")}
                value={periodEnd}
                onChangeText={setPeriodEnd}
              />

              <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
                {t("subcontractAgreement.cumulativeProgressByItem")}
              </Text>
              {agreement.items.map((item) => (
                <Field
                  key={item.id}
                  label={t("subcontractAgreement.itemPercentage", {
                    name: item.description,
                  })}
                  value={percentages[item.id] ?? "0"}
                  onChangeText={(value) =>
                    setPercentages((current) => ({
                      ...current,
                      [item.id]: value,
                    }))
                  }
                  keyboardType="decimal-pad"
                />
              ))}

              <Field
                label={t("subcontractAgreement.retentionOverride")}
                value={billRetention}
                onChangeText={setBillRetention}
                keyboardType="decimal-pad"
              />
              <Field
                label={t("subcontractAgreement.retentionCap")}
                value={billRetentionCap}
                onChangeText={setBillRetentionCap}
                keyboardType="decimal-pad"
              />
              <Field
                label={t("subcontractAgreement.otherDeductions")}
                value={deductions}
                onChangeText={setDeductions}
                keyboardType="decimal-pad"
              />
              <Field
                label={t("subcontractAgreement.deductionNote")}
                value={deductionNote}
                onChangeText={setDeductionNote}
                multiline
              />

              <View style={[styles.switchRow, isUrdu && styles.rtlRow]}>
                <Text style={[styles.body, isUrdu && styles.rtlText]}>
                  {t("subcontractAgreement.retentionSecuredByGuarantee")}
                </Text>
                <Switch
                  value={retentionByGuarantee}
                  onValueChange={setRetentionByGuarantee}
                  trackColor={{ false: C.border, true: C.gold }}
                  thumbColor={retentionByGuarantee ? C.navy : C.surface}
                />
              </View>

              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("subcontractAgreement.salesTaxAuthority")}
              </Text>
              <View style={[styles.buttonRow, isUrdu && styles.rtlRow]}>
                {["", "PRA", "SRB", "KPRA", "BRA", "ICT"].map((value) => {
                  const optionLabel = value
                    ? value
                    : t("subcontractAgreement.none");
                  return (
                    <Action
                      key={value || "none"}
                      label={optionLabel}
                      selected={salesTaxAuthority === value}
                      onPress={() => setSalesTaxAuthority(value)}
                    />
                  );
                })}
              </View>

              <Field
                label={t("subcontractAgreement.billNotes")}
                value={billNotes}
                onChangeText={setBillNotes}
                multiline
              />
              <Action
                label={
                  saving
                    ? t("subcontractAgreement.generating")
                    : t("subcontractAgreement.generateDraft")
                }
                primary
                disabled={saving}
                onPress={() => void saveDraftBill()}
              />
            </>
          ) : null}

          {form === "advance" ? (
            <>
              <Field
                label={t("subcontractAgreement.amount")}
                value={advanceAmount}
                onChangeText={setAdvanceAmount}
                keyboardType="decimal-pad"
              />
              <Field
                label={t("subcontractAgreement.advanceDate")}
                value={advanceDate}
                onChangeText={setAdvanceDate}
              />
              <Field
                label={t("subcontractAgreement.notesOptional")}
                value={advanceNotes}
                onChangeText={setAdvanceNotes}
                multiline
              />
              <Action
                label={
                  saving
                    ? t("subcontractAgreement.saving")
                    : t("subcontractAgreement.recordAdvance")
                }
                primary
                disabled={saving}
                onPress={() => void saveAdvance()}
              />
            </>
          ) : null}

          {form === "payment" ? (
            <>
              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("subcontractAgreement.billOptional")}
              </Text>
              <Action
                label={
                  paymentBillId
                    ? t("subcontractAgreement.clearSelectedBill")
                    : t("subcontractAgreement.noBillSelected")
                }
                selected={!paymentBillId}
                onPress={() => setPaymentBillId("")}
              />
              {bills
                .filter((bill) => bill.status === "ISSUED")
                .map((bill) => (
                  <Action
                    key={bill.id}
                    label={t("subcontractAgreement.billNumber", {
                      number: bill.bill_number,
                    })}
                    selected={paymentBillId === bill.id}
                    onPress={() => setPaymentBillId(bill.id)}
                  />
                ))}
              <Field
                label={t("subcontractAgreement.grossAmount")}
                value={grossAmount}
                onChangeText={setGrossAmount}
                keyboardType="decimal-pad"
              />
              <Field
                label={t("subcontractAgreement.advanceRecovery")}
                value={advanceRecovered}
                onChangeText={setAdvanceRecovered}
                keyboardType="decimal-pad"
              />
              <Text style={[styles.label, isUrdu && styles.rtlText]}>
                {t("subcontractAgreement.withholdingCategory")}
              </Text>
              <View style={[styles.buttonRow, isUrdu && styles.rtlRow]}>
                {[
                  ["", t("subcontractAgreement.none")],
                  ["GOODS_SUPPLY", t("subcontractAgreement.goods")],
                  ["SERVICES", t("subcontractAgreement.services")],
                  ["CONTRACTS_EXECUTION", t("subcontractAgreement.contracts")],
                ].map(([value, optionLabel]) => (
                  <Action
                    key={value || "none"}
                    label={optionLabel}
                    selected={whtCategory === value}
                    onPress={() => setWhtCategory(value)}
                  />
                ))}
              </View>
              <Field
                label={t("subcontractAgreement.paymentDate")}
                value={paymentDate}
                onChangeText={setPaymentDate}
              />
              <Field
                label={t("subcontractAgreement.notesOptional")}
                value={paymentNotes}
                onChangeText={setPaymentNotes}
                multiline
              />
              <Action
                label={
                  saving
                    ? t("subcontractAgreement.saving")
                    : t("subcontractAgreement.recordPayment")
                }
                primary
                disabled={saving}
                onPress={() => void savePayment()}
              />
            </>
          ) : null}

          {error ? (
            <Text style={[styles.error, isUrdu && styles.rtlText]}>
              {error}
            </Text>
          ) : null}
          <Action
            label={t("subcontractAgreement.close")}
            disabled={saving}
            onPress={() => setForm(null)}
          />
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
  const { i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  return (
    <View style={styles.card}>
      <Text style={[styles.sectionTitle, isUrdu && styles.rtlText]}>
        {props.title}
      </Text>
      {props.children}
    </View>
  );
}

function Info(props: { label: string; value: string }) {
  const { i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  return (
    <View style={[styles.infoRow, isUrdu && styles.rtlRow]}>
      <Text style={[styles.muted, isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <Text style={[styles.body, isUrdu && styles.rtlText]}>
        {props.value}
      </Text>
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
  const { i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";

  return (
    <View style={styles.field}>
      <Text style={[styles.label, isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <TextInput
        style={[
          styles.input,
          props.multiline && styles.multiline,
          isUrdu && styles.rtlText,
        ]}
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType={props.keyboardType ?? "default"}
        multiline={props.multiline}
        textAlign={isUrdu ? "right" : "left"}
        placeholderTextColor={C.muted}
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
  selected?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={
        props.selected === undefined
          ? undefined
          : { selected: props.selected }
      }
      disabled={props.disabled}
      onPress={props.onPress}
      style={[
        styles.button,
        props.primary && styles.primaryButton,
        props.danger && styles.dangerButton,
        props.selected && styles.choiceSelected,
        props.disabled && styles.disabled,
      ]}
    >
      <Text
        style={[
          styles.buttonText,
          props.primary && styles.primaryText,
          props.danger && styles.dangerText,
          props.selected && styles.choiceTextSelected,
        ]}
      >
        {props.label}
      </Text>
    </Pressable>
  );
}

function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const visiblePages = Array.from(
    { length: totalPages },
    (_, index) => index + 1,
  ).filter((value) => Math.abs(value - page) <= 2);

  if (totalPages <= 1) return null;

  return (
    <View style={[styles.pagination, isUrdu && styles.rtlRow]}>
      <Pressable
        style={[styles.pageNavButton, page === 1 && styles.disabled]}
        disabled={page === 1}
        onPress={() => onPageChange(Math.max(1, page - 1))}
        accessibilityRole="button"
      >
        <Text style={styles.pageNavText}>{t("subcontractAgreement.previous")}</Text>
      </Pressable>

      <View style={[styles.pageNumbers, isUrdu && styles.rtlRow]}>
        {visiblePages.map((value) => (
          <Pressable
            key={value}
            style={[
              styles.pageNumber,
              value === page && styles.pageNumberSelected,
            ]}
            disabled={value === page}
            onPress={() => onPageChange(value)}
            accessibilityRole="button"
            accessibilityState={{ selected: value === page }}
          >
            <Text
              style={[
                styles.pageNumberText,
                value === page && styles.pageNumberTextSelected,
              ]}
            >
              {value}
            </Text>
          </Pressable>
        ))}
      </View>

      <Pressable
        style={[
          styles.pageNavButton,
          page === totalPages && styles.disabled,
        ]}
        disabled={page === totalPages}
        onPress={() => onPageChange(Math.min(totalPages, page + 1))}
        accessibilityRole="button"
      >
        <Text style={styles.pageNavText}>{t("subcontractAgreement.next")}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 22, paddingTop: 28, paddingBottom: 40, gap: 12, backgroundColor: C.background },
  rtlPage: { direction: "rtl" },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right" },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 12, backgroundColor: C.background },
  eyebrow: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: C.text, fontSize: 23, fontWeight: "800" },
  sectionTitle: { color: C.text, fontSize: 17, fontWeight: "800", marginBottom: 5 },
  cardTitle: { color: C.text, fontSize: 15, fontWeight: "800" },
  status: { color: C.navy, backgroundColor: C.surfaceMuted, alignSelf: "flex-start", overflow: "hidden", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 6, fontSize: 11, fontWeight: "800" },
  body: { color: C.text, fontSize: 14, lineHeight: 20, flex: 1, textAlign: "right" },
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, flex: 1 },
  label: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  link: { color: C.navy, fontSize: 13, fontWeight: "800" },
  error: { color: C.red, backgroundColor: C.redBg, borderWidth: 1, borderColor: "#EAC6C0", borderRadius: 11, fontSize: 13, lineHeight: 19, padding: 12 },
  notice: { color: C.green, backgroundColor: C.greenBg, borderWidth: 1, borderColor: "#CEE1D2", borderRadius: 11, fontSize: 13, lineHeight: 19, padding: 12 },
  warning: { color: C.amber, backgroundColor: C.amberBg, borderRadius: 10, fontSize: 13, lineHeight: 19, padding: 11, marginTop: 10 },
  card: { backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, borderTopWidth: 2, borderTopColor: C.gold, padding: 16, gap: 10 },
  item: { borderTopWidth: 1, borderTopColor: C.border, paddingTop: 12, gap: 8 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 10, borderTopWidth: 1, borderTopColor: C.border, paddingVertical: 8 },
  field: { gap: 6, marginTop: 6 },
  input: { minHeight: 46, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, paddingHorizontal: 12, color: C.text, fontSize: 14 },
  multiline: { minHeight: 74, textAlignVertical: "top", paddingTop: 10 },
  buttonRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  switchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, marginTop: 12 },
  button: { minHeight: 42, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface, borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 12, paddingVertical: 9, marginTop: 4 },
  buttonText: { color: C.navy, fontSize: 13, fontWeight: "800", textAlign: "center" },
  primaryButton: { backgroundColor: C.navy, borderColor: C.navy },
  primaryText: { color: C.surface },
  dangerButton: { borderColor: "#EAC6C0", backgroundColor: C.redBg },
  dangerText: { color: C.red },
  choiceSelected: { backgroundColor: C.surfaceMuted, borderColor: C.navy },
  choiceTextSelected: { color: C.navy },
  disabled: { opacity: 0.5 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 10, padding: 10, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13 },
  pageNavButton: { minHeight: 38, justifyContent: "center", paddingHorizontal: 10, borderRadius: 9, backgroundColor: C.surfaceMuted },
  pageNavText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  pageNumbers: { flexDirection: "row", alignItems: "center", gap: 5 },
  pageNumber: { minWidth: 36, height: 36, alignItems: "center", justifyContent: "center", borderRadius: 9, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface },
  pageNumberSelected: { backgroundColor: C.navy, borderColor: C.navy },
  pageNumberText: { color: C.secondary, fontSize: 13, fontWeight: "700" },
  pageNumberTextSelected: { color: C.surface },
});
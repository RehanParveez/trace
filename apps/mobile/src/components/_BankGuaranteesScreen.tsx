import { useCallback, useState } from "react";
import {ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../api/client";
import {createBankGuarantee, getProjectBankGuaranteeSummary, listProjectBankGuarantees, markBankGuaranteeCalled, releaseBankGuarantee, renewBankGuarantee,
} from "../api/bankGuarantees";
import { listProjectBOQVersions } from "../api/drawingsBoq";
import { getProject } from "../api/projects";
import { listProjectAgreements } from "../api/subcontractors";
import i18n from "../i18n";
import LanguageSwitcher from "./LanguageSwitcher";
import type {AuthUser, BankGuarantee, BankGuaranteeHolderType, BOQVersion, Project, ProjectBankGuaranteeSummary, SubcontractAgreementDetail,
} from "../api/types";

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

function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;

  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));

  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function money(
  value: number | string,
  currency: string,
  locale = i18n.resolvedLanguage === "ur" ? "ur-PK" : "en-PK",
): string {
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

export function BankGuaranteesScreen({
  projectId,
}: {
  projectId: string;
}) {
  const { t, i18n: activeI18n } = useTranslation();
  const isUrdu = activeI18n.resolvedLanguage === "ur";

  const [user, setUser] = useState<AuthUser | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [guarantees, setGuarantees] = useState<BankGuarantee[]>([]);
  const [summary, setSummary] =
    useState<ProjectBankGuaranteeSummary | null>(null);
  const [boqVersions, setBoqVersions] = useState<BOQVersion[]>([]);
  const [agreements, setAgreements] = useState<SubcontractAgreementDetail[]>([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [holderType, setHolderType] =
    useState<BankGuaranteeHolderType>("CLIENT");
  const [boqVersionId, setBoqVersionId] = useState("");
  const [agreementId, setAgreementId] = useState("");
  const [guaranteeNumber, setGuaranteeNumber] = useState("");
  const [issuingBank, setIssuingBank] = useState("");
  const [amount, setAmount] = useState("");
  const [issueDate, setIssueDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [expiryDate, setExpiryDate] = useState("");
  const [notes, setNotes] = useState("");

  const [renewing, setRenewing] = useState<BankGuarantee | null>(null);
  const [renewNumber, setRenewNumber] = useState("");
  const [renewAmount, setRenewAmount] = useState("");
  const [renewIssueDate, setRenewIssueDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [renewExpiryDate, setRenewExpiryDate] = useState("");
  const [renewNotes, setRenewNotes] = useState("");

  const permissionKeys = user?.role.permissions.map((item) => item.key) ?? [];
  const canRead = permissionKeys.includes("bank_guarantee:read");
  const canManage = permissionKeys.includes("bank_guarantee:manage");
  const canRelease = permissionKeys.includes("bank_guarantee:release");

  const load = useCallback(
    async (refresh = false) => {
      if (!projectId) {
        setError(t("bankGuarantees.projectIdMissing"));
        setLoading(false);
        return;
      }

      if (refresh) setRefreshing(true);
      else setLoading(true);

      setError(null);

      try {
        const currentUser = await restoreSession();

        if (!currentUser) {
          router.replace("/");
          return;
        }

        setUser(currentUser);

        const hasRead = currentUser.role.permissions.some(
          (permission) => permission.key === "bank_guarantee:read",
        );

        if (!hasRead) {
          setProject(null);
          setGuarantees([]);
          setSummary(null);
          setBoqVersions([]);
          setAgreements([]);
          return;
        }

        const [
          projectResult,
          guaranteeRows,
          projectSummary,
          versionRows,
          agreementRows,
        ] = await Promise.all([
          getProject(projectId),
          listProjectBankGuarantees(projectId),
          getProjectBankGuaranteeSummary(projectId),
          listProjectBOQVersions(projectId),
          listProjectAgreements(projectId),
        ]);

        setProject(projectResult);
        setGuarantees(guaranteeRows);
        setSummary(projectSummary);
        setBoqVersions(versionRows);
        setAgreements(agreementRows);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("bankGuarantees.loadFailure"),
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, t],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function resetCreateForm() {
    setHolderType("CLIENT");
    setBoqVersionId("");
    setAgreementId("");
    setGuaranteeNumber("");
    setIssuingBank("");
    setAmount("");
    setIssueDate(new Date().toISOString().slice(0, 10));
    setExpiryDate("");
    setNotes("");
  }

  async function submitCreate() {
    if (!canManage || !projectId || saving) return;

    const numericAmount = Number(amount);
    if (!guaranteeNumber.trim() || !issuingBank.trim()) {
      setError(t("bankGuarantees.enterNumberAndBank"));
      return;
    }
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setError(t("bankGuarantees.enterValidAmount"));
      return;
    }
    if (!validDate(issueDate) || !validDate(expiryDate)) {
      setError(t("bankGuarantees.enterValidDates"));
      return;
    }
    if (expiryDate <= issueDate) {
      setError(t("bankGuarantees.expiryAfterIssue"));
      return;
    }
    if (holderType === "CLIENT" && !boqVersionId) {
      setError(t("bankGuarantees.selectBoqVersion"));
      return;
    }
    if (holderType === "SUBCONTRACTOR" && !agreementId) {
      setError(t("bankGuarantees.selectAgreement"));
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await createBankGuarantee({
        holder_type: holderType,
        project_id: projectId,
        boq_version_id: holderType === "CLIENT" ? boqVersionId : null,
        agreement_id: holderType === "SUBCONTRACTOR" ? agreementId : null,
        guarantee_number: guaranteeNumber.trim(),
        issuing_bank: issuingBank.trim(),
        amount: numericAmount,
        issue_date: issueDate,
        expiry_date: expiryDate,
        notes: notes.trim() || null,
      });

      resetCreateForm();
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("bankGuarantees.createFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  function beginRenewal(guarantee: BankGuarantee) {
    setRenewing(guarantee);
    setRenewNumber("");
    setRenewAmount(String(guarantee.amount));
    setRenewIssueDate(new Date().toISOString().slice(0, 10));
    setRenewExpiryDate("");
    setRenewNotes("");
    setError(null);
  }

  async function submitRenewal() {
    if (!canManage || !renewing || saving) return;

    const numericAmount = renewAmount.trim() ? Number(renewAmount) : undefined;

    if (!renewNumber.trim()) {
      setError(t("bankGuarantees.enterNewNumber"));
      return;
    }
    if (!validDate(renewIssueDate) || !validDate(renewExpiryDate)) {
      setError(t("bankGuarantees.enterValidRenewalDates"));
      return;
    }
    if (renewExpiryDate <= renewIssueDate) {
      setError(t("bankGuarantees.expiryAfterIssue"));
      return;
    }
    if (
      numericAmount !== undefined &&
      (!Number.isFinite(numericAmount) || numericAmount <= 0)
    ) {
      setError(t("bankGuarantees.renewalAmountInvalid"));
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await renewBankGuarantee(renewing.id, {
        guarantee_number: renewNumber.trim(),
        issue_date: renewIssueDate,
        expiry_date: renewExpiryDate,
        ...(numericAmount === undefined ? {} : { amount: numericAmount }),
        notes: renewNotes.trim() || null,
      });

      setRenewing(null);
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("bankGuarantees.renewFailure"),
      );
    } finally {
      setSaving(false);
    }
  }

  function confirmAction(
    guarantee: BankGuarantee,
    action: "release" | "call",
  ) {
    Alert.alert(
      action === "release"
        ? t("bankGuarantees.releaseTitle")
        : t("bankGuarantees.markCalledTitle"),
      t("bankGuarantees.actionConfirm", {
        action:
          action === "release"
            ? t("bankGuarantees.releaseVerb")
            : t("bankGuarantees.markCalledVerb"),
        number: guarantee.guarantee_number,
      }),
      [
        { text: t("bankGuarantees.cancel"), style: "cancel" },
        {
          text:
            action === "release"
              ? t("bankGuarantees.release")
              : t("bankGuarantees.markCalled"),
          style: "destructive",
          onPress: () => {
            void runStatusAction(guarantee, action);
          },
        },
      ],
    );
  }

  async function runStatusAction(
    guarantee: BankGuarantee,
    action: "release" | "call",
  ) {
    if (!canRelease || saving) return;

    setSaving(true);
    setError(null);

    try {
      if (action === "release") {
        await releaseBankGuarantee(guarantee.id);
      } else {
        await markBankGuaranteeCalled(guarantee.id);
      }
      await load(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("bankGuarantees.statusActionFailure", {
              action:
                action === "release"
                  ? t("bankGuarantees.releaseVerb")
                  : t("bankGuarantees.markCalledVerb"),
            }),
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: t("bankGuarantees.title") }} />
        <ActivityIndicator size="large" color={C.navy} />
        <Text style={styles.muted}>{t("bankGuarantees.loading")}</Text>
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.page}>
        <Stack.Screen options={{ title: t("bankGuarantees.title") }} />
        <Text style={styles.title}>{t("bankGuarantees.title")}</Text>
        <Text style={styles.muted}>
          {t("bankGuarantees.accessDenied")}
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={[styles.page, isUrdu && { direction: "rtl" }]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => void load(true)}
          tintColor={C.navy}
        />
      }
    >
      <Stack.Screen options={{ title: t("bankGuarantees.title") }} />

      <View style={styles.topBar}>
        <Text style={styles.eyebrow}>{t("bankGuarantees.eyebrow")}</Text>
        <LanguageSwitcher />
      </View>
      <Text style={styles.title}>
        {project?.name ?? t("bankGuarantees.title")}
      </Text>
      {project?.code ? (
        <Text style={styles.muted}>
          {t("bankGuarantees.code", { code: project.code })}
        </Text>
      ) : null}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {summary ? (
        <View style={styles.summaryCard}>
          <Text style={styles.sectionTitle}>
            {t("bankGuarantees.summaryTitle")}
          </Text>
          <InfoRow
            label={t("bankGuarantees.active")}
            value={String(summary.active_count)}
          />
          <InfoRow
            label={t("bankGuarantees.expiringSoon")}
            value={String(summary.expiring_soon_count)}
          />
          <InfoRow
            label={t("bankGuarantees.expired")}
            value={String(summary.expired_count)}
          />
          <InfoRow
            label={t("bankGuarantees.activeValue")}
            value={money(summary.total_active_value, summary.currency)}
          />
        </View>
      ) : null}

      {canManage ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>
            {t("bankGuarantees.recordTitle")}
          </Text>

          <Text style={styles.label}>{t("bankGuarantees.holder")}</Text>
          <View style={styles.choiceRow}>
            <Choice
              label={t("bankGuarantees.client")}
              selected={holderType === "CLIENT"}
              onPress={() => setHolderType("CLIENT")}
            />
            <Choice
              label={t("bankGuarantees.subcontractor")}
              selected={holderType === "SUBCONTRACTOR"}
              onPress={() => setHolderType("SUBCONTRACTOR")}
            />
          </View>

          {holderType === "CLIENT" ? (
            <>
              <Text style={styles.label}>
                {t("bankGuarantees.boqVersion")}
              </Text>
              {boqVersions.length === 0 ? (
                <Text style={styles.muted}>
                  {t("bankGuarantees.noBoqVersions")}
                </Text>
              ) : (
                boqVersions.map((version) => (
                  <Choice
                    key={version.id}
                    label={`${version.label} · ${version.status}`}
                    selected={boqVersionId === version.id}
                    onPress={() => setBoqVersionId(version.id)}
                  />
                ))
              )}
            </>
          ) : (
            <>
              <Text style={styles.label}>
                {t("bankGuarantees.subcontractAgreement")}
              </Text>
              {agreements.length === 0 ? (
                <Text style={styles.muted}>
                  {t("bankGuarantees.noAgreements")}
                </Text>
              ) : (
                agreements.map((agreement) => (
                  <Choice
                    key={agreement.id}
                    label={`${agreement.scope_description} · ${agreement.status}`}
                    selected={agreementId === agreement.id}
                    onPress={() => setAgreementId(agreement.id)}
                  />
                ))
              )}
            </>
          )}

          <Field
            label={t("bankGuarantees.guaranteeNumber")}
            value={guaranteeNumber}
            onChangeText={setGuaranteeNumber}
          />
          <Field
            label={t("bankGuarantees.issuingBank")}
            value={issuingBank}
            onChangeText={setIssuingBank}
          />
          <Field
            label={t("bankGuarantees.amount")}
            value={amount}
            onChangeText={setAmount}
            keyboardType="decimal-pad"
          />
          <Field
            label={t("bankGuarantees.issueDate")}
            value={issueDate}
            onChangeText={setIssueDate}
            placeholder="2026-10-01"
          />
          <Field
            label={t("bankGuarantees.expiryDate")}
            value={expiryDate}
            onChangeText={setExpiryDate}
            placeholder="2027-10-01"
          />
          <Field
            label={t("bankGuarantees.notesOptional")}
            value={notes}
            onChangeText={setNotes}
            multiline
          />

          <ActionButton
            label={
              saving
                ? t("bankGuarantees.saving")
                : t("bankGuarantees.recordGuarantee")
            }
            disabled={saving}
            onPress={() => void submitCreate()}
          />
        </View>
      ) : null}

      <Text style={styles.sectionTitle}>
        {t("bankGuarantees.guarantees")}
      </Text>

      {guarantees.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.muted}>
            {t("bankGuarantees.noGuarantees")}
          </Text>
        </View>
      ) : (
        guarantees.map((guarantee) => (
          <View key={guarantee.id} style={styles.card}>
            <View style={styles.rowBetween}>
              <Text style={styles.guaranteeTitle}>
                {guarantee.guarantee_number}
              </Text>
              <Text style={styles.status}>{guarantee.status}</Text>
            </View>

            <InfoRow
              label={t("bankGuarantees.holder")}
              value={guarantee.holder_type}
            />
            <InfoRow
              label={t("bankGuarantees.issuingBank")}
              value={guarantee.issuing_bank}
            />
            <InfoRow
              label={t("bankGuarantees.amount")}
              value={money(guarantee.amount, guarantee.currency)}
            />
            <InfoRow
              label={t("bankGuarantees.issueDateLabel")}
              value={guarantee.issue_date}
            />
            <InfoRow
              label={t("bankGuarantees.expiryDateLabel")}
              value={guarantee.expiry_date}
            />

            {guarantee.is_expired ? (
              <Text style={styles.warning}>
                {t("bankGuarantees.expiredBadge")}
              </Text>
            ) : guarantee.is_expiring_soon ? (
              <Text style={styles.warning}>
                {t("bankGuarantees.expiringSoonBadge")}
              </Text>
            ) : null}

            {guarantee.notes ? (
              <Text style={styles.muted}>{guarantee.notes}</Text>
            ) : null}

            {guarantee.renewed_from_guarantee_id ? (
              <Text style={styles.muted}>
                {t("bankGuarantees.renewalOfPrevious")}
              </Text>
            ) : null}

            {guarantee.status === "ACTIVE" && (canManage || canRelease) ? (
              <View style={styles.actions}>
                {canManage ? (
                  <ActionButton
                    label={t("bankGuarantees.renew")}
                    disabled={saving}
                    secondary
                    onPress={() => beginRenewal(guarantee)}
                  />
                ) : null}
                {canRelease ? (
                  <>
                    <ActionButton
                      label={t("bankGuarantees.release")}
                      disabled={saving}
                      secondary
                      onPress={() => confirmAction(guarantee, "release")}
                    />
                    <ActionButton
                      label={t("bankGuarantees.markCalled")}
                      disabled={saving}
                      secondary
                      onPress={() => confirmAction(guarantee, "call")}
                    />
                  </>
                ) : null}
              </View>
            ) : null}
          </View>
        ))
      )}

      {renewing ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>
            {t("bankGuarantees.renewTitle", {
              number: renewing.guarantee_number,
            })}
          </Text>
          <Text style={styles.muted}>
            {t("bankGuarantees.renewDescription")}
          </Text>

          <Field
            label={t("bankGuarantees.newGuaranteeNumber")}
            value={renewNumber}
            onChangeText={setRenewNumber}
          />
          <Field
            label={t("bankGuarantees.newAmountOptional")}
            value={renewAmount}
            onChangeText={setRenewAmount}
            keyboardType="decimal-pad"
          />
          <Field
            label={t("bankGuarantees.issueDate")}
            value={renewIssueDate}
            onChangeText={setRenewIssueDate}
          />
          <Field
            label={t("bankGuarantees.expiryDate")}
            value={renewExpiryDate}
            onChangeText={setRenewExpiryDate}
          />
          <Field
            label={t("bankGuarantees.notesOptional")}
            value={renewNotes}
            onChangeText={setRenewNotes}
            multiline
          />

          <ActionButton
            label={
              saving
                ? t("bankGuarantees.saving")
                : t("bankGuarantees.saveRenewal")
            }
            disabled={saving}
            onPress={() => void submitRenewal()}
          />
          <ActionButton
            label={t("bankGuarantees.cancel")}
            disabled={saving}
            secondary
            onPress={() => setRenewing(null)}
          />
        </View>
      ) : null}
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

function Field({
  label,
  value,
  onChangeText,
  keyboardType,
  placeholder,
  multiline,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  placeholder?: string;
  multiline?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType ?? "default"}
        placeholder={placeholder}
        multiline={multiline}
        textAlignVertical={multiline ? "top" : "center"}
        autoCapitalize="none"
      />
    </View>
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
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
    >
      <Text style={[styles.choiceText, selected && styles.choiceTextSelected]}>
        {selected ? "✓ " : ""}
        {label}
      </Text>
    </Pressable>
  );
}

function ActionButton({
  label,
  disabled,
  secondary,
  onPress,
}: {
  label: string;
  disabled: boolean;
  secondary?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[
        styles.actionButton,
        secondary && styles.secondaryButton,
        disabled && styles.disabledButton,
      ]}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
    >
      <Text
        style={[
          styles.actionButtonText,
          secondary && styles.secondaryButtonText,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 18, paddingTop: 21, paddingBottom: 40, backgroundColor: C.background,},
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 20, backgroundColor: C.background,},
  topBar: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10,},
  eyebrow: {color: C.muted, fontSize: 11, fontWeight: "700", letterSpacing: 1.6,},
  title: {color: C.text, fontSize: 28, fontWeight: "800", marginTop: 5, letterSpacing: -0.5,},
  subtitle: { color: C.secondary, fontSize: 14, lineHeight: 20, marginTop: 6 },
  sectionTitle: {color: C.text, fontSize: 18, fontWeight: "800", marginTop: 20, marginBottom: 10,},
  card: {backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, padding: 16, marginTop: 12,},
  summaryCard: {backgroundColor: C.surface, borderRadius: 15, borderWidth: 1, borderColor: C.border, borderTopColor: C.gold, borderTopWidth: 3, padding: 16, marginTop: 18,},
  infoRow: {flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 8, borderTopWidth: 1, borderTopColor: "#F0E9DC",},
  infoLabel: { color: C.muted, fontSize: 12, flex: 1 },
  infoValue: {color: C.text, fontSize: 13, fontWeight: "700", flex: 1, textAlign: "right",},
  rowBetween: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 8,},
  guaranteeTitle: {color: C.text, fontSize: 16, fontWeight: "800", flexShrink: 1,},
  status: {color: C.navy, backgroundColor: C.surfaceMuted, overflow: "hidden", borderRadius: 99, paddingHorizontal: 9, paddingVertical: 5, fontSize: 10, fontWeight: "800",},
  warning: {color: C.amber, backgroundColor: C.amberBg, overflow: "hidden", borderRadius: 9, paddingHorizontal: 10, paddingVertical: 8, fontWeight: "700", fontSize: 12, marginTop: 10,},
  muted: { color: C.secondary, fontSize: 13, lineHeight: 19, marginTop: 6 },
  error: {color: C.red, backgroundColor: C.redBg, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, fontSize: 13, lineHeight: 19, marginTop: 12,},
  label: {color: C.secondary, fontSize: 12, fontWeight: "700", marginBottom: 7,},
  field: { marginTop: 13 },
  input: {minHeight: 46, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, paddingHorizontal: 12, color: C.text, fontSize: 14,},
  multiline: { minHeight: 76, paddingTop: 12 },
  choiceRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  choice: {minHeight: 42, justifyContent: "center", paddingHorizontal: 12, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, marginTop: 7,},
  choiceSelected: {borderColor: C.navy, backgroundColor: C.surfaceMuted,},
  choiceText: { color: C.secondary, fontSize: 12, fontWeight: "700" },
  choiceTextSelected: { color: C.navy },
  actions: { gap: 7, marginTop: 10 },
  actionButton: {minHeight: 47, alignItems: "center", justifyContent: "center", paddingHorizontal: 14, paddingVertical: 12, borderRadius: 11, backgroundColor: C.navy, marginTop: 12,},
  actionButtonText: {color: C.surface, fontSize: 13, fontWeight: "800", textAlign: "center",},
  secondaryButton: {backgroundColor: C.surface, borderWidth: 1, borderColor: C.border,},
  secondaryButtonText: { color: C.navy },
  disabledButton: { opacity: 0.5 },
});

import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getProject } from "../../../../api/projects";
import {listBOQItems, listProjectBOQVersions,
} from "../../../../api/drawingsBoq";
import {approveProgressClaim, createProgressClaim, listProgressClaims, rejectProgressClaim, submitProgressClaim, updateProgressClaim,
} from "../../../../api/verification";
import type {BOQItem, BOQVersion, ProgressClaim, Project,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";

const PAGE_SIZE = 3;

function formatDate(value: string | null, locale: string, notSet: string) {
  if (!value) return notSet;
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(locale);
}

function validDate(value: string): boolean {
  if (!value) return false;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return (
    !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
  );
}

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

export default function ProgressVerificationScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [claims, setClaims] = useState<ProgressClaim[]>([]);
  const [approvedItems, setApprovedItems] = useState<BOQItem[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [claimsPage, setClaimsPage] = useState(1);
  const [itemsPage, setItemsPage] = useState(1);

  const [boqItemId, setBoqItemId] = useState("");
  const [claimDate, setClaimDate] = useState("");
  const [claimedQuantity, setClaimedQuantity] = useState("");
  const [claimedPercentage, setClaimedPercentage] = useState("");
  const [notes, setNotes] = useState("");
  const [editingClaimId, setEditingClaimId] = useState("");
  const [editingVersion, setEditingVersion] = useState<number | null>(null);
  const [reviewNote, setReviewNote] = useState("");

  const canRead = permissions.includes("progress_claim:read");
  const canCreate = permissions.includes("progress_claim:create");
  const canUpdate = permissions.includes("progress_claim:update");
  const canSubmit = permissions.includes("progress_claim:submit");
  const canReview = permissions.includes("progress_claim:review");

  const claimsPages = pageCount(claims.length);
  const itemsPages = pageCount(approvedItems.length);
  const visibleClaims = paginate(claims, claimsPage);
  const visibleApprovedItems = paginate(approvedItems, itemsPage);

  const load = useCallback(async () => {
    if (!projectId) {
      setError(t("progressVerification.projectNotFound"));
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }

      const granted = user.role.permissions.map((permission) => permission.key);
      setPermissions(granted);
      setProject(await getProject(projectId));

      if (granted.includes("progress_claim:read")) {
        try {
          setClaims(await listProgressClaims(projectId));
          setClaimsPage(1);
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : t("progressVerification.loadClaimsFailure"),
          );
        }
      } else {
        setClaims([]);
        setClaimsPage(1);
      }

      try {
        const versions = await listProjectBOQVersions(projectId);
        const allItems: BOQItem[] = [];

        await Promise.all(
          versions.map(async (version: BOQVersion) => {
            try {
              const items = await listBOQItems(version.id);
              for (const item of items) {
                if (item.status === "APPROVED") allItems.push(item);
              }
            } catch {
              // A version's items may be unavailable; continue loading others.
            }
          }),
        );

        setApprovedItems(allItems);
        setItemsPage(1);
      } catch {
        setApprovedItems([]);
        setItemsPage(1);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("progressVerification.loadProjectFailure"),
      );
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");

    try {
      await action();
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("progressVerification.actionFailure"),
      );
    } finally {
      setBusy(false);
    }
  }

  function resetForm() {
    setBoqItemId("");
    setClaimDate("");
    setClaimedQuantity("");
    setClaimedPercentage("");
    setNotes("");
    setEditingClaimId("");
    setEditingVersion(null);
  }

  async function saveClaim() {
    if (!projectId) return;

    if (!boqItemId) {
      setError(t("progressVerification.validation.selectItem"));
      return;
    }
    if (!validDate(claimDate)) {
      setError(t("progressVerification.validation.claimDate"));
      return;
    }

    const quantity = Number(claimedQuantity);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError(t("progressVerification.validation.quantity"));
      return;
    }

    const percentage = Number(claimedPercentage);
    if (
      !Number.isFinite(percentage) ||
      percentage < 0 ||
      percentage > 100
    ) {
      setError(t("progressVerification.validation.percentage"));
      return;
    }

    if (editingClaimId) {
      if (!canUpdate) {
        setError(t("progressVerification.cannotUpdate"));
        return;
      }
      if (editingVersion == null) {
        setError(t("progressVerification.versionMissing"));
        return;
      }

      await run(async () => {
        await updateProgressClaim(editingClaimId, {
          claim_date: claimDate,
          claimed_quantity: quantity,
          claimed_percentage: percentage,
          notes: notes.trim() || null,
          version: editingVersion,
        });
        resetForm();
      });
      return;
    }

    if (!canCreate) {
      setError(t("progressVerification.cannotCreate"));
      return;
    }

    await run(async () => {
      await createProgressClaim({
        project_id: projectId,
        boq_item_id: boqItemId,
        claim_date: claimDate,
        claimed_quantity: quantity,
        claimed_percentage: percentage,
        notes: notes.trim() || null,
      });
      resetForm();
    });
  }

  function beginEditClaim(claim: ProgressClaim) {
    if (claim.status !== "DRAFT") {
      setError(t("progressVerification.onlyDraftCanEdit"));
      return;
    }

    setEditingClaimId(claim.id);
    setEditingVersion(claim.version);
    setBoqItemId(claim.boq_item_id);
    setClaimDate(claim.claim_date?.slice(0, 10) ?? "");
    setClaimedQuantity(String(claim.claimed_quantity));
    setClaimedPercentage(String(claim.claimed_percentage));
    setNotes(claim.notes ?? "");
  }

  function handleSubmit(claim: ProgressClaim) {
    if (!canSubmit) return;

    Alert.alert(
      t("progressVerification.submitConfirmTitle"),
      t("progressVerification.submitConfirmMessage"),
      [
        {
          text: t("progressVerification.cancel"),
          style: "cancel",
        },
        {
          text: t("progressVerification.submit"),
          onPress: () =>
            void run(() => submitProgressClaim(claim.id, claim.version)),
        },
      ],
    );
  }

  async function handleApprove(claim: ProgressClaim) {
    if (!canReview) return;

    await run(() =>
      approveProgressClaim(claim.id, {
        version: claim.version,
        note: reviewNote.trim() || null,
      }),
    );
    setReviewNote("");
  }

  async function handleReject(claim: ProgressClaim) {
    if (!canReview) return;

    await run(() =>
      rejectProgressClaim(claim.id, {
        version: claim.version,
        note: reviewNote.trim() || null,
      }),
    );
    setReviewNote("");
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.switcherRow}>
          <LanguageSwitcher />
        </View>
        <ActivityIndicator size="large" color={COLORS.navy} />
        <Text style={[styles.muted, isUrdu && styles.rtlText]}>
          {t("progressVerification.loading")}
        </Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <Text
            style={[styles.title, styles.headerCopy, isUrdu && styles.rtlText]}
          >
            {t("progressVerification.title")}
          </Text>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {error || t("progressVerification.projectNotFound")}
        </Text>
        <Pressable onPress={() => router.back()}>
          <Text style={[styles.link, isUrdu && styles.rtlText]}>
            {t("progressVerification.backToProject")}
          </Text>
        </Pressable>
      </View>
    );
  }

  if (!canRead && !canCreate) {
    return (
      <View style={styles.page}>
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("progressVerification.backToProjectName", {
                  name: project.name,
                })}
              </Text>
            </Pressable>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("progressVerification.title")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>
        <Text style={[styles.error, isUrdu && styles.rtlText]}>
          {t("progressVerification.accessDenied")}
        </Text>
      </View>
    );
  }

  const selectedItem = approvedItems.find((item) => item.id === boqItemId);

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[styles.headerRow, isUrdu && styles.rtlRow]}>
          <View style={styles.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[styles.link, isUrdu && styles.rtlText]}>
                {t("progressVerification.backToProjectName", {
                  name: project.name,
                })}
              </Text>
            </Pressable>
            <Text style={[styles.title, isUrdu && styles.rtlText]}>
              {t("progressVerification.title")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? (
          <Text style={[styles.error, isUrdu && styles.rtlText]}>{error}</Text>
        ) : null}

        {(canCreate || (canUpdate && editingClaimId)) && (
          <View style={styles.formCard}>
            <Text style={[styles.section, isUrdu && styles.rtlText]}>
              {editingClaimId
                ? t("progressVerification.editDraftClaim")
                : t("progressVerification.newClaim")}
            </Text>

            {!editingClaimId ? (
              <>
                <Text style={[styles.label, isUrdu && styles.rtlText]}>
                  {t("progressVerification.approvedBOQItem")}
                </Text>
                {approvedItems.length === 0 ? (
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("progressVerification.noApprovedItems")}
                  </Text>
                ) : (
                  <>
                    {visibleApprovedItems.map((item) => (
                      <Chip
                        key={item.id}
                        label={`${item.material_name} · ${item.quantity} ${item.unit}`}
                        selected={boqItemId === item.id}
                        onPress={() => setBoqItemId(item.id)}
                        isUrdu={isUrdu}
                      />
                    ))}
                    <Pagination
                      page={itemsPage}
                      pages={itemsPages}
                      isUrdu={isUrdu}
                      onPrevious={() =>
                        setItemsPage((page) => Math.max(1, page - 1))
                      }
                      onNext={() =>
                        setItemsPage((page) =>
                          Math.min(itemsPages, page + 1),
                        )
                      }
                    />
                  </>
                )}
              </>
            ) : selectedItem ? (
              <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                {t("progressVerification.selectedItem", {
                  name: selectedItem.material_name,
                  quantity: selectedItem.quantity,
                  unit: selectedItem.unit,
                })}
              </Text>
            ) : null}

            <Field
              label={t("progressVerification.claimDate")}
              value={claimDate}
              onChangeText={setClaimDate}
              isUrdu={isUrdu}
            />
            <Field
              label={t("progressVerification.claimedQuantity")}
              value={claimedQuantity}
              onChangeText={setClaimedQuantity}
              keyboardType="decimal-pad"
              isUrdu={isUrdu}
            />
            <Field
              label={t("progressVerification.claimedPercentage")}
              value={claimedPercentage}
              onChangeText={setClaimedPercentage}
              keyboardType="decimal-pad"
              isUrdu={isUrdu}
            />
            <Field
              label={t("progressVerification.notesOptional")}
              value={notes}
              onChangeText={setNotes}
              multiline
              isUrdu={isUrdu}
            />
            <Action
              title={
                editingClaimId
                  ? t("progressVerification.saveClaimChanges")
                  : t("progressVerification.createClaim")
              }
              onPress={() => void saveClaim()}
              isUrdu={isUrdu}
            />
            {editingClaimId ? (
              <Action
                title={t("progressVerification.cancelEdit")}
                secondary
                onPress={resetForm}
                isUrdu={isUrdu}
              />
            ) : null}
          </View>
        )}

        {canReview ? (
          <View style={styles.formCard}>
            <Text style={[styles.section, isUrdu && styles.rtlText]}>
              {t("progressVerification.reviewNote")}
            </Text>
            <TextInput
              style={[
                styles.input,
                styles.multiline,
                isUrdu && styles.rtlText,
              ]}
              value={reviewNote}
              onChangeText={setReviewNote}
              placeholder={t("progressVerification.reviewNotePlaceholder")}
              multiline
              textAlignVertical="top"
              textAlign={isUrdu ? "right" : "left"}
            />
          </View>
        ) : null}

        <Text style={[styles.section, isUrdu && styles.rtlText]}>
          {t("progressVerification.claims")}
        </Text>

        {claims.length === 0 ? (
          <Text style={[styles.muted, isUrdu && styles.rtlText]}>
            {t("progressVerification.noClaims")}
          </Text>
        ) : (
          <>
            {visibleClaims.map((claim) => {
              const item = approvedItems.find(
                (approvedItem) => approvedItem.id === claim.boq_item_id,
              );

              return (
                <View key={claim.id} style={styles.card}>
                  <View style={[styles.rowBetween, isUrdu && styles.rtlRow]}>
                    <Text
                      style={[styles.itemTitle, isUrdu && styles.rtlText]}
                    >
                      {item?.material_name || claim.boq_item_id}
                    </Text>
                    <Text
                      style={
                        claim.status === "APPROVED"
                          ? styles.approved
                          : claim.status === "REJECTED"
                            ? styles.rejected
                            : claim.status === "SUBMITTED"
                              ? styles.submitted
                              : styles.draft
                      }
                    >
                      {t(
                        `progressVerification.status.${claim.status.toLowerCase()}`,
                        { defaultValue: claim.status },
                      )}
                    </Text>
                  </View>

                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("progressVerification.claimDateValue", {
                      date: formatDate(
                        claim.claim_date,
                        locale,
                        t("progressVerification.notSet"),
                      ),
                    })}
                  </Text>
                  <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                    {t("progressVerification.quantityAndPercentage", {
                      quantity: claim.claimed_quantity,
                      unit: item?.unit ? ` ${item.unit}` : "",
                      percentage: claim.claimed_percentage,
                    })}
                  </Text>

                  {claim.notes ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {claim.notes}
                    </Text>
                  ) : null}

                  {claim.review_note ? (
                    <Text style={[styles.muted, isUrdu && styles.rtlText]}>
                      {t("progressVerification.reviewNoteValue", {
                        note: claim.review_note,
                      })}
                    </Text>
                  ) : null}

                  <View style={[styles.row, isUrdu && styles.rtlRow]}>
                    {claim.status === "DRAFT" && canUpdate ? (
                      <Action
                        title={t("progressVerification.edit")}
                        secondary
                        onPress={() => beginEditClaim(claim)}
                        isUrdu={isUrdu}
                      />
                    ) : null}
                    {claim.status === "DRAFT" && canSubmit ? (
                      <Action
                        title={t("progressVerification.submit")}
                        onPress={() => handleSubmit(claim)}
                        isUrdu={isUrdu}
                      />
                    ) : null}
                    {claim.status === "SUBMITTED" && canReview ? (
                      <>
                        <Action
                          title={t("progressVerification.approve")}
                          onPress={() => void handleApprove(claim)}
                          isUrdu={isUrdu}
                        />
                        <Action
                          title={t("progressVerification.reject")}
                          danger
                          onPress={() => void handleReject(claim)}
                          isUrdu={isUrdu}
                        />
                      </>
                    ) : null}
                  </View>
                </View>
              );
            })}

            <Pagination
              page={claimsPage}
              pages={claimsPages}
              isUrdu={isUrdu}
              onPrevious={() =>
                setClaimsPage((page) => Math.max(1, page - 1))
              }
              onNext={() =>
                setClaimsPage((page) => Math.min(claimsPages, page + 1))
              }
            />
          </>
        )}

        {busy ? (
          <View style={styles.busy}>
            <ActivityIndicator color={COLORS.navy} />
            <Text style={[styles.muted, isUrdu && styles.rtlText]}>
              {t("progressVerification.saving")}
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Pagination(props: {
  page: number;
  pages: number;
  isUrdu: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const { t } = useTranslation();

  return (
    <View style={[styles.pagination, props.isUrdu && styles.rtlRow]}>
      <Action
        title={t("progressVerification.previous")}
        secondary
        disabled={props.page <= 1}
        onPress={props.onPrevious}
        isUrdu={props.isUrdu}
      />
      <Text style={[styles.pageText, props.isUrdu && styles.rtlText]}>
        {t("progressVerification.pageOf", {
          page: props.page,
          pages: props.pages,
        })}
      </Text>
      <Action
        title={t("progressVerification.next")}
        secondary
        disabled={props.page >= props.pages}
        onPress={props.onNext}
        isUrdu={props.isUrdu}
      />
    </View>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  multiline?: boolean;
  keyboardType?: "default" | "decimal-pad";
  isUrdu: boolean;
}) {
  return (
    <>
      <Text style={[styles.label, props.isUrdu && styles.rtlText]}>
        {props.label}
      </Text>
      <TextInput
        style={[
          styles.input,
          props.multiline && styles.multiline,
          props.isUrdu && styles.rtlText,
        ]}
        value={props.value}
        onChangeText={props.onChangeText}
        multiline={props.multiline}
        textAlignVertical={props.multiline ? "top" : "center"}
        textAlign={props.isUrdu ? "right" : "left"}
        keyboardType={props.keyboardType ?? "default"}
      />
    </>
  );
}

function Chip(props: {
  label: string;
  selected: boolean;
  onPress: () => void;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[styles.chip, props.selected && styles.chipSelected]}
      onPress={props.onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: props.selected }}
    >
      <Text
        style={[
          styles.chipText,
          props.selected && styles.chipTextSelected,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.label}
      </Text>
    </Pressable>
  );
}

function Action(props: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  danger?: boolean;
  disabled?: boolean;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.action,
        props.secondary && styles.actionSecondary,
        props.danger && styles.actionDanger,
        props.disabled && styles.disabled,
      ]}
      onPress={props.onPress}
      disabled={props.disabled}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          props.secondary && styles.actionSecondaryText,
          props.danger && styles.actionDangerText,
          props.isUrdu && styles.rtlText,
        ]}
      >
        {props.title}
      </Text>
    </Pressable>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#F7F3EC",
  navy: "#080D18",
  text: "#171C26",
  secondary: "#5C5347",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
  red: "#A63A32",
  redBackground: "#FBEAE7",
  green: "#287456",
  blue: "#315F9B",
  amber: "#9B641A",
};

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: COLORS.background },
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 38, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  switcherRow: { width: "100%", alignItems: "flex-end", marginBottom: 8 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 8 },
  headerCopy: { flex: 1 },
  rtlRow: { flexDirection: "row-reverse" },
  title: { color: COLORS.text, fontSize: 26, fontWeight: "800", marginTop: 10, marginBottom: 4 },
  section: { color: COLORS.text, fontSize: 18, fontWeight: "800", marginTop: 18, marginBottom: 6 },
  formCard: { backgroundColor: COLORS.surface, borderRadius: 15, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 10 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 12, marginBottom: 6 },
  input: { minHeight: 46, backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: COLORS.text },
  multiline: { minHeight: 80, textAlignVertical: "top" },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 10 },
  itemTitle: { color: COLORS.text, fontSize: 14, fontWeight: "800", flex: 1 },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 6, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginVertical: 10, lineHeight: 19, fontSize: 13 },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  chip: { borderWidth: 1, borderColor: COLORS.border, borderRadius: 12, backgroundColor: COLORS.surface, paddingHorizontal: 12, paddingVertical: 10, marginTop: 7 },
  chipSelected: { borderColor: COLORS.gold, backgroundColor: COLORS.surfaceMuted },
  chipText: { color: COLORS.secondary, fontSize: 13, fontWeight: "700" },
  chipTextSelected: { color: COLORS.navy },
  action: { minHeight: 42, flexGrow: 1, backgroundColor: COLORS.navy, borderRadius: 10, borderWidth: 1, borderColor: COLORS.navy, alignItems: "center", justifyContent: "center", paddingHorizontal: 12, paddingVertical: 10, marginTop: 9 },
  actionSecondary: { backgroundColor: COLORS.surface, borderColor: COLORS.border },
  actionDanger: { backgroundColor: COLORS.red, borderColor: COLORS.red },
  actionText: { color: COLORS.surface, fontSize: 12, fontWeight: "800", textAlign: "center" },
  actionSecondaryText: { color: COLORS.navy },
  actionDangerText: { color: COLORS.surface },
  disabled: { opacity: 0.5 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 5 },
  rowBetween: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  approved: { color: COLORS.green, fontSize: 11, fontWeight: "800" },
  rejected: { color: COLORS.red, fontSize: 11, fontWeight: "800" },
  submitted: { color: COLORS.blue, fontSize: 11, fontWeight: "800" },
  draft: { color: COLORS.amber, fontSize: 11, fontWeight: "800" },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 10 },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", textAlign: "center" },
  busy: { alignItems: "center", padding: 18, gap: 8 },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
});
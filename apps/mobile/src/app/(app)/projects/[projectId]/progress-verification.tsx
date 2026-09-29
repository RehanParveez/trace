import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { restoreSession } from "../../../../api/client";
import { getProject } from "../../../../api/projects";
import {listBOQItems, listProjectBOQVersions,
} from "../../../../api/drawingsBoq";
import {approveProgressClaim, createProgressClaim, listProgressClaims, rejectProgressClaim, submitProgressClaim, updateProgressClaim,
} from "../../../../api/verification";
import type {BOQItem, BOQVersion, ProgressClaim, Project,
} from "../../../../api/types";

function formatDate(value: string | null): string {
  if (!value) return "Not set";
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
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

export default function ProgressVerificationScreen() {
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

  const load = useCallback(async () => {
    if (!projectId) {
      setError("Project not found.");
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
      const granted = user.role.permissions.map((p) => p.key);
      setPermissions(granted);
      setProject(await getProject(projectId));

      if (granted.includes("progress_claim:read")) {
        try {
          setClaims(await listProgressClaims(projectId));
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load progress claims.",
          );
        }
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
            
            }
          }),
        );
        setApprovedItems(allItems);
      } catch {
        
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load project.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

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
      setError(err instanceof Error ? err.message : "The action failed.");
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
      setError("Select an approved BOQ item.");
      return;
    }
    if (!validDate(claimDate)) {
      setError("Claim date must be a valid YYYY-MM-DD date.");
      return;
    }
    const qty = Number(claimedQuantity);
    if (!Number.isFinite(qty) || qty <= 0) {
      setError("Claimed quantity must be a positive number.");
      return;
    }
    const pct = Number(claimedPercentage);
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
      setError("Claimed percentage must be between 0 and 100.");
      return;
    }

    if (editingClaimId) {
      if (!canUpdate) {
        setError("You cannot update progress claims.");
        return;
      }
      await run(async () => {
        
        if (editingVersion == null) {
          setError("Missing claim version. Re-open the claim and try again.");
          return;
        }
        await updateProgressClaim(editingClaimId, {
          claim_date: claimDate,
          claimed_quantity: qty,
          claimed_percentage: pct,
          notes: notes.trim() || null,
          version: editingVersion,
        });
        resetForm();
      });
      return;
    }

    if (!canCreate) {
      setError("You cannot create progress claims.");
      return;
    }

    await run(async () => {
      await createProgressClaim({
        project_id: projectId,
        boq_item_id: boqItemId,
        claim_date: claimDate,
        claimed_quantity: qty,
        claimed_percentage: pct,
        notes: notes.trim() || null,
      });
      resetForm();
    });
  }

  function beginEditClaim(claim: ProgressClaim) {
    if (claim.status !== "DRAFT") {
      setError("Only draft claims can be edited.");
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

  async function handleSubmit(claim: ProgressClaim) {
    if (!canSubmit) return;
    Alert.alert("Submit claim?", "Submit this draft claim for review?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Submit",
        onPress: () =>
          void run(() => submitProgressClaim(claim.id, claim.version)),
      },
    ]);
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
        <ActivityIndicator size="large" color="#183153" />
        <Text style={styles.muted}>Loading progress verification…</Text>
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.page}>
        <Text style={styles.error}>{error || "Project not found."}</Text>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  Back to project</Text>
        </Pressable>
      </View>
    );
  }

  if (!canRead && !canCreate) {
    return (
      <View style={styles.page}>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  {project.name}</Text>
        </Pressable>
        <Text style={styles.title}>Progress verification</Text>
        <Text style={styles.error}>
          Your organization role does not allow progress claim access.
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
        <Pressable onPress={() => router.back()}>
          <Text style={styles.link}>‹  {project.name}</Text>
        </Pressable>

        <Text style={styles.title}>Progress verification</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}

        {(canCreate || (canUpdate && editingClaimId)) && (
          <>
            <Text style={styles.section}>
              {editingClaimId ? "Edit draft claim" : "New progress claim"}
            </Text>

            {!editingClaimId ? (
              <>
                <Text style={styles.label}>Approved BOQ item</Text>
                {approvedItems.length === 0 ? (
                  <Text style={styles.muted}>
                    No approved BOQ items available. Approve items in Drawings
                    & BOQ first.
                  </Text>
                ) : (
                  approvedItems.map((item) => (
                    <Chip
                      key={item.id}
                      label={`${item.material_name} · ${item.quantity} ${item.unit}`}
                      selected={boqItemId === item.id}
                      onPress={() => setBoqItemId(item.id)}
                    />
                  ))
                )}
              </>
            ) : selectedItem ? (
              <Text style={styles.muted}>
                Item: {selectedItem.material_name} ({selectedItem.quantity}{" "}
                {selectedItem.unit})
              </Text>
            ) : null}

            <Field
              label="Claim date (YYYY-MM-DD)"
              value={claimDate}
              onChangeText={setClaimDate}
            />
            <Field
              label="Claimed quantity"
              value={claimedQuantity}
              onChangeText={setClaimedQuantity}
              keyboardType="decimal-pad"
            />
            <Field
              label="Claimed percentage (0–100)"
              value={claimedPercentage}
              onChangeText={setClaimedPercentage}
              keyboardType="decimal-pad"
            />
            <Field
              label="Notes (optional)"
              value={notes}
              onChangeText={setNotes}
              multiline
            />
            <Action
              title={editingClaimId ? "Save claim changes" : "Create claim"}
              onPress={() => void saveClaim()}
            />
            {editingClaimId ? (
              <Action title="Cancel edit" secondary onPress={resetForm} />
            ) : null}
          </>
        )}

        {canReview ? (
          <>
            <Text style={styles.section}>Review note</Text>
            <TextInput
              style={[styles.input, styles.multiline]}
              value={reviewNote}
              onChangeText={setReviewNote}
              placeholder="Optional note for approve/reject"
              multiline
              textAlignVertical="top"
            />
          </>
        ) : null}

        <Text style={styles.section}>Claims</Text>
        {claims.length === 0 ? (
          <Text style={styles.muted}>No progress claims yet.</Text>
        ) : null}

        {claims.map((claim) => {
          const item = approvedItems.find((i) => i.id === claim.boq_item_id);
          return (
            <View key={claim.id} style={styles.card}>
              <View style={styles.rowBetween}>
                <Text style={styles.itemTitle}>
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
                  {claim.status}
                </Text>
              </View>
              <Text style={styles.muted}>Date: {formatDate(claim.claim_date)}</Text>
              <Text style={styles.muted}>
                Qty: {claim.claimed_quantity}
                {item ? ` ${item.unit}` : ""} · {claim.claimed_percentage}%
              </Text>
              {claim.notes ? <Text style={styles.muted}>{claim.notes}</Text> : null}
              {claim.review_note ? (
                <Text style={styles.muted}>Review: {claim.review_note}</Text>
              ) : null}

              <View style={styles.row}>
                {claim.status === "DRAFT" && canUpdate ? (
                  <Action
                    title="Edit"
                    secondary
                    onPress={() => beginEditClaim(claim)}
                  />
                ) : null}
                {claim.status === "DRAFT" && canSubmit ? (
                  <Action title="Submit" onPress={() => void handleSubmit(claim)} />
                ) : null}
                {claim.status === "SUBMITTED" && canReview ? (
                  <>
                    <Action title="Approve" onPress={() => void handleApprove(claim)} />
                    <Action
                      title="Reject"
                      danger
                      onPress={() => void handleReject(claim)}
                    />
                  </>
                ) : null}
              </View>
            </View>
          );
        })}

        {busy ? (
          <View style={styles.busy}>
            <ActivityIndicator color="#183153" />
            <Text style={styles.muted}>Saving…</Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field({
  label,
  value,
  onChangeText,
  multiline = false,
  keyboardType = "default",
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  multiline?: boolean;
  keyboardType?: "default" | "decimal-pad";
}) {
  return (
    <>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline]}
        value={value}
        onChangeText={onChangeText}
        multiline={multiline}
        textAlignVertical={multiline ? "top" : "center"}
        keyboardType={keyboardType}
      />
    </>
  );
}

function Chip({
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
      style={[styles.chip, selected && styles.chipSelected]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
        {label}
      </Text>
    </Pressable>
  );
}

function Action({
  title,
  onPress,
  secondary = false,
  danger = false,
}: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  danger?: boolean;
}) {
  return (
    <Pressable
      style={[
        styles.action,
        secondary && styles.actionSecondary,
        danger && styles.actionDanger,
      ]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.actionText,
          secondary && styles.actionSecondaryText,
          danger && styles.actionDangerText,
        ]}
      >
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#F4F6F8" },
  page: {flexGrow: 1,  padding: 22, paddingTop: 52, paddingBottom: 48, backgroundColor: "#F4F6F8",},
  center: {flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#F4F6F8",},
  title: {color: "#17212F", fontSize: 28, fontWeight: "700", marginVertical: 18,},
  section: {color: "#17212F", fontSize: 20, fontWeight: "700", marginTop: 28, marginBottom: 8,},
  label: {color: "#344054", fontSize: 14, fontWeight: "600", marginTop: 14, marginBottom: 7,},
  input: {backgroundColor: "white", borderColor: "#D0D5DD", borderWidth: 1, borderRadius: 10, padding: 14, fontSize: 16, color: "#17212F",},
  multiline: { minHeight: 80 },
  card: {backgroundColor: "white", borderRadius: 12, borderWidth: 1, borderColor: "#E4E7EC", padding: 15, marginTop: 10,},
  itemTitle: { color: "#17212F", fontSize: 16, fontWeight: "700", flex: 1 },
  muted: { color: "#667085", marginTop: 6, lineHeight: 20 },
  error: { color: "#B42318", marginVertical: 12, lineHeight: 20 },
  link: { color: "#183153", fontWeight: "700", fontSize: 15 },
  chip: {borderWidth: 1, borderColor: "#D0D5DD", borderRadius: 20, backgroundColor: "white", paddingHorizontal: 12, paddingVertical: 9, marginTop: 6,},
  chipSelected: { borderColor: "#183153", backgroundColor: "#E8EEF5" },
  chipText: { color: "#344054", fontSize: 13, fontWeight: "600" },
  chipTextSelected: { color: "#183153" },
  action: {backgroundColor: "#183153", borderRadius: 10, alignItems: "center", padding: 13, marginTop: 10,},
  actionSecondary: {backgroundColor: "white", borderWidth: 1, borderColor: "#D0D5DD",},
  actionDanger: { backgroundColor: "#B42318" },
  actionText: { color: "white", fontWeight: "700" },
  actionSecondaryText: { color: "#183153" },
  actionDangerText: { color: "white" },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  rowBetween: {flexDirection: "row", alignItems: "center", justifyContent: "space-between",},
  approved: { color: "#067647", fontSize: 11, fontWeight: "700" },
  rejected: { color: "#B42318", fontSize: 11, fontWeight: "700" },
  submitted: { color: "#175CD3", fontSize: 11, fontWeight: "700" },
  draft: { color: "#B54708", fontSize: 11, fontWeight: "700" },
  busy: { alignItems: "center", padding: 18, gap: 8 },
});
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {getBOQSummary, listBOQItems, listProjectBOQVersions, updateBOQVersion
} from "../../../../api/drawingsBoq";
import {addAdjustment, approveVersion, archiveVersion, confirmItemRate, downloadExport, getItemTrace, issueVersion, listAdjustments, listSnapshots, priceVersion, reopenVersion, revokeAdjustment,
  submitVersionForReview, waiveItemReview,
} from "../../../../api/boqEngine";
import type {Adjustment, BOQItem, BOQSummary, BOQVersion, ExportKind, ItemTrace, Snapshot, DrawingElement, SnapshotItem, 
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { shareExportFile } from "../../../../features/drawingsBoq/exportFile";
import {availableActions, isLocked, lifecycleTone,
  type VersionAction,
} from "../../../../features/drawingsBoq/lifecycle";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import {Action, Badge, COLORS, Field, InfoRow, formatMoney, formatNumber, ui,
} from "../../../../features/drawingsBoq/ui";
import { listItemSourceElements, listSnapshotItems } from "../../../../api/boqExtras";
import { getRebarSummary } from "../../../../api/imports";
import type { RebarSummary } from "../../../../api/types";

const PAGE_SIZE = 5;

const EXPORT_KINDS: { kind: ExportKind; label: string }[] = [
  { kind: "CONTRACT_BOQ", label: "Contract BOQ" },
  { kind: "PROCUREMENT", label: "Procurement" },
  { kind: "MEASUREMENT_BOOK", label: "Measurement book" },
  { kind: "AUDIT_REPORT", label: "Audit report" },
  { kind: "REVISION_COMPARISON", label: "Revision comparison" },
  { kind: "BBS", label: "Bar bending schedule" },
];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

type PanelState =
  | { itemId: string; mode: "trace" | "adjust" | "waive" | "elements" }
  | null;

export default function BoqVersionScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; versionId?: string }>();
  const projectId = first(params.projectId);
  const versionId = first(params.versionId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [version, setVersion] = useState<BOQVersion | null>(null);
  const [summary, setSummary] = useState<BOQSummary | null>(null);
  const [items, setItems] = useState<BOQItem[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(1);
  const [panel, setPanel] = useState<PanelState>(null);
  const [note, setNote] = useState("");
  const [areaText, setAreaText] = useState("");
  const [showRebar, setShowRebar] = useState(false);

  const canUpdate = hasPerm(permissions, PERM.BOQ_UPDATE);
  const canApprove = hasPerm(permissions, PERM.BOQ_APPROVE);
  const canIssue = hasPerm(permissions, PERM.BOQ_ISSUE);
  const canAdjust = hasPerm(permissions, PERM.BOQ_ADJUST);
  const canExport = hasPerm(permissions, PERM.BOQ_EXPORT);
  const locked = version ? isLocked(version) : true;

  const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const visibleItems = items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const load = useCallback(
    async (silent = false) => {
      if (!projectId || !versionId) {
        setError(tx("boqVersion.notFound", "BOQ version not found."));
        setLoading(false);
        return;
      }
      if (!silent) setLoading(true);

      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }
        setPermissions(user.role.permissions.map((p) => p.key));

        const versions = await listProjectBOQVersions(projectId);
        const found = versions.find((v) => v.id === versionId) ?? null;
        if (!found) throw new Error(tx("boqVersion.notFound", "BOQ version not found."));
        setVersion(found);
        if (!silent) {
          setAreaText(found.covered_area_sqft == null ? "" : String(found.covered_area_sqft));
        }

        const [itemsResult, summaryResult, snapshotsResult] = await Promise.allSettled([
          listBOQItems(versionId),
          getBOQSummary(versionId),
          listSnapshots(versionId),
        ]);
        if (itemsResult.status === "fulfilled") setItems(itemsResult.value);
        else throw itemsResult.reason;
        if (summaryResult.status === "fulfilled") setSummary(summaryResult.value);
        if (snapshotsResult.status === "fulfilled") setSnapshots(snapshotsResult.value);
      } catch (err) {
        setError(describeError(err, tx("boqVersion.loadFailure", "Could not load the BOQ.")));
      } finally {
        setLoading(false);
      }
    },
    [projectId, versionId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function act(action: () => Promise<unknown>, okMessage?: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      await load(true);
      if (okMessage) setNotice(okMessage);
    } catch (err) {
      setError(describeError(err, tx("boqVersion.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  function permitted(action: VersionAction): boolean {
    switch (action) {
      case "submit":
        return canUpdate;
      case "reopen":
      case "approve":
        return canApprove;
      case "issue":
      case "archive":
        return canIssue;
    }
  }

  const ACTION_LABEL: Record<VersionAction, string> = {
    submit: tx("boqVersion.submit", "Submit for review"),
    reopen: tx("boqVersion.reopen", "Reopen"),
    approve: tx("boqVersion.approve", "Approve"),
    issue: tx("boqVersion.issue", "Issue"),
    archive: tx("boqVersion.archive", "Archive"),
  };

  function runVersionAction(action: VersionAction) {
    if (!version) return;
    const go = () =>
      void act(async () => {
        switch (action) {
          case "submit":
            await submitVersionForReview(version.id);
            break;
          case "reopen":
            await reopenVersion(version.id);
            break;
          case "approve":
            await approveVersion(version.id, note);
            break;
          case "issue":
            await issueVersion(version.id, note);
            break;
          case "archive":
            await archiveVersion(version.id);
            break;
        }
        setNote("");
      });

    if (action === "archive" || action === "issue" || action === "approve") {
      Alert.alert(
        ACTION_LABEL[action],
        tx("boqVersion.confirmAction", "Do you want to continue?"),
        [
          { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
          { text: ACTION_LABEL[action], onPress: go },
        ],
      );
    } else {
      go();
    }
  }

  async function handlePrice() {
    if (!version) return;
    await act(async () => {
      const result = await priceVersion(version.id);
      setNotice(
        tx(
          "boqVersion.priced",
          "Priced {{priced}} items, {{unpriced}} without a rate, {{mismatch}} unit mismatches.",
          { priced: result.priced, unpriced: result.unpriced, mismatch: result.unit_mismatch },
        ),
      );
    });
  }

  async function handleSaveArea() {
    if (!version) return;
    const value = areaText.trim() === "" ? null : Number(areaText);
    if (value !== null && (!Number.isFinite(value) || value <= 0)) {
      setError(tx("boqVersion.areaInvalid", "Enter a positive covered area."));
      return;
    }
    await act(async () => {
      await updateBOQVersion(version.id, { covered_area_sqft: value });
    });
  }

  async function handleExport(kind: ExportKind, fmt: "pdf" | "xlsx") {
    if (!version) return;
    const ordered = [...snapshots].sort((a, b) => b.version_no - a.version_no);
    const latest = ordered[0];
    const previous = ordered[1];

    if (kind === "REVISION_COMPARISON" && !previous) {
      setError(tx("boqVersion.needTwoSnapshots", "Comparison needs at least two snapshots."));
      return;
    }

    setBusy(true);
    setError("");
    setNotice("");
    try {
      const file = await downloadExport(version.id, kind, fmt, {
        snapshot_id: latest?.id,
        compare_snapshot_id: kind === "REVISION_COMPARISON" ? previous?.id : undefined,
      });
      await shareExportFile(file);
    } catch (err) {
      setError(describeError(err, tx("boqVersion.exportFailure", "Export failed.")));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const actions = version ? availableActions(version).filter(permitted) : [];

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>
                {tx("boqVersion.back", "Back to drawings & BOQ")}
              </Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{version?.label ?? ""}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}

        {version ? (
          <View style={ui.card}>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Badge label={version.origin} />
              <Badge
                label={version.lifecycle.replaceAll("_", " ")}
                tone={lifecycleTone(version.lifecycle)}
              />
              {version.audit_score != null ? (
                <Badge
                  label={tx("boqVersion.score", "Readiness {{score}}", {
                    score: Number(version.audit_score).toFixed(0),
                  })}
                />
              ) : null}
            </View>

            {summary ? (
              <View style={ui.summaryBox}>
                <InfoRow label={tx("boqVersion.items", "Items")} value={String(summary.item_count)} isUrdu={isUrdu} />
                <InfoRow
                  label={tx("boqVersion.total", "Total")}
                  value={formatMoney(summary.grand_total, locale, "-")}
                  isUrdu={isUrdu}
                />
                <InfoRow
                  label={tx("boqVersion.unpriced", "Unpriced items")}
                  value={String(summary.unpriced_item_count)}
                  isUrdu={isUrdu}
                />
                <InfoRow
                  label={tx("boqVersion.costPerSqft", "Cost per sq ft")}
                  value={formatMoney(summary.cost_per_sqft, locale, "-")}
                  isUrdu={isUrdu}
                />
              </View>
            ) : null}

            {!locked && canUpdate ? (
              <>
                <Field
                  label={tx("boqVersion.coveredArea", "Covered area (sq ft)")}
                  value={areaText}
                  onChangeText={setAreaText}
                  keyboardType="decimal-pad"
                  isUrdu={isUrdu}
                />
                <Action
                  title={tx("boqVersion.saveArea", "Save area")}
                  secondary
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => void handleSaveArea()}
                />
                <Action
                  title={tx("boqVersion.price", "Price items")}
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => void handlePrice()}
                />
              </>
            ) : null}

            {actions.includes("approve") || actions.includes("issue") ? (
              <Field
                label={tx("boqVersion.note", "Note (optional)")}
                value={note}
                onChangeText={setNote}
                isUrdu={isUrdu}
              />
            ) : null}

            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {actions.map((action) => (
                <Action
                  key={action}
                  title={ACTION_LABEL[action]}
                  secondary={action === "archive" || action === "reopen"}
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => runVersionAction(action)}
                />
              ))}
            </View>

            <Action
              title={tx("boqVersion.rebarSummary", "Rebar summary")}
              secondary
              isUrdu={isUrdu}
              onPress={() => setShowRebar((open) => !open)}
            />
            {showRebar ? <RebarSummaryPanel versionId={version.id} isUrdu={isUrdu} tx={tx} /> : null}
            <Action
              title={tx("boqVersion.compare", "Compare with another version")}
              secondary
              isUrdu={isUrdu}
              onPress={() =>
                router.push({
                  pathname: "/projects/[projectId]/boq-compare",
                  params: { projectId: version.project_id, versionId: version.id },
                })
              }
            />
            {version.calculation_run_id ? (
              <Action
                title={tx("boqVersion.runData", "Calculation data")}
                secondary
                isUrdu={isUrdu}
                onPress={() =>
                  router.push({
                    pathname: "/projects/[projectId]/run-data",
                    params: {
                      projectId: version.project_id,
                      runId: version.calculation_run_id ?? "",
                      versionId: version.id,
                    },
                  })
                }
              />
            ) : null}
            <Action
              title={tx("boqVersion.reviewIssues", "Review issues")}
              secondary
              isUrdu={isUrdu}
              onPress={() =>
                router.push({
                  pathname: "/projects/[projectId]/review-issues",
                  params: { projectId: version.project_id, versionId: version.id },
                })
              }
            />
          </View>
        ) : null}

        <Text style={[ui.section, isUrdu && ui.rtlText]}>
          {tx("boqVersion.itemsHeading", "Items")}
        </Text>

        {items.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("drawingsBoq.noItems", "No items yet.")}
          </Text>
        ) : null}

        {visibleItems.map((item) => {
          const open = panel?.itemId === item.id ? panel.mode : null;
          const model = !item.is_manual && item.source_kind !== "LEGACY";
          return (
            <View key={item.id} style={ui.boqItem}>
              <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{item.material_name}</Text>
                {item.review_status !== "OK" ? (
                  <Badge
                    label={item.review_status.replaceAll("_", " ")}
                    tone={item.review_status === "REVIEW_REQUIRED" ? "warn" : "neutral"}
                  />
                ) : null}
              </View>

              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {`${formatNumber(item.quantity)} ${item.unit}`}
                {item.work_item_code ? ` · ${item.work_item_code}` : ""}
              </Text>
              {item.net_quantity != null ? (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("boqVersion.qtyBreakdown", "Net {{net}} · adjustments {{adj}}", {
                    net: formatNumber(item.net_quantity),
                    adj: formatNumber(item.adjustment_total),
                  })}
                  {item.confidence != null
                    ? ` · ${tx("boqVersion.confidence", "confidence {{value}}", {
                        value: formatNumber(item.confidence, 2),
                      })}`
                    : ""}
                </Text>
              ) : null}
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {item.unit_rate == null
                  ? tx("drawingsBoq.rateNotSet", "Rate not set")
                  : `${formatMoney(item.unit_rate, locale, "-")} / ${item.unit}${
                      item.rate_source ? ` · ${item.rate_source}` : ""
                    }`}
              </Text>

              <View style={[ui.row, isUrdu && ui.rtlRow]}>
                <Action
                  title={tx("boqVersion.trace", "Trace")}
                  secondary
                  isUrdu={isUrdu}
                  onPress={() => setPanel(open === "trace" ? null : { itemId: item.id, mode: "trace" })}
                />
                {model ? (
                  <Action
                    title={tx("boqVersion.elements", "Source elements")}
                    secondary
                    isUrdu={isUrdu}
                    onPress={() => setPanel(open === "elements" ? null : { itemId: item.id, mode: "elements" })}
                  />
                ) : null}
                {!locked && canAdjust && model ? (
                  <Action
                    title={tx("boqVersion.adjust", "Adjust")}
                    secondary
                    isUrdu={isUrdu}
                    onPress={() => setPanel(open === "adjust" ? null : { itemId: item.id, mode: "adjust" })}
                  />
                ) : null}
                {!locked && canUpdate && item.review_status === "REVIEW_REQUIRED" ? (
                  <Action
                    title={tx("boqVersion.waive", "Waive review")}
                    secondary
                    isUrdu={isUrdu}
                    onPress={() => setPanel(open === "waive" ? null : { itemId: item.id, mode: "waive" })}
                  />
                ) : null}
                {!locked && canUpdate && item.unit_rate != null && item.rate_source !== "MANUAL" ? (
                  <Action
                    title={tx("boqVersion.confirmRate", "Confirm rate")}
                    secondary
                    disabled={busy}
                    isUrdu={isUrdu}
                    onPress={() => void act(() => confirmItemRate(item.id))}
                  />
                ) : null}
              </View>

              {open ? (
                <ItemPanel
                  item={item}
                  mode={open}
                  locked={locked}
                  isUrdu={isUrdu}
                  tx={tx}
                  onChanged={() => void load(true)}
                  onClose={() => setPanel(null)}
                />
              ) : null}
            </View>
          );
        })}

        {items.length > PAGE_SIZE ? (
          <View style={[ui.pagination, isUrdu && ui.rtlRow]}>
            <Action
              title={tx("drawingsBoq.previous", "Previous")}
              secondary
              disabled={page <= 1}
              isUrdu={isUrdu}
              onPress={() => setPage((p) => Math.max(1, p - 1))}
            />
            <Text style={[ui.pageText, isUrdu && ui.rtlText]}>{`${page} / ${pages}`}</Text>
            <Action
              title={tx("drawingsBoq.next", "Next")}
              secondary
              disabled={page >= pages}
              isUrdu={isUrdu}
              onPress={() => setPage((p) => Math.min(pages, p + 1))}
            />
          </View>
        ) : null}

        <Text style={[ui.section, isUrdu && ui.rtlText]}>
          {tx("boqVersion.snapshots", "Snapshots")}
        </Text>
        {snapshots.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("boqVersion.noSnapshots", "Snapshots are created when the BOQ is approved or issued.")}
          </Text>
        ) : (
          snapshots.map((snapshot) => (
            <SnapshotRow
              key={snapshot.id}
              snapshot={snapshot}
              locale={locale}
              isUrdu={isUrdu}
              tx={tx}
            />
          ))
        )}

        {canExport ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>
              {tx("boqVersion.exports", "Exports")}
            </Text>
            {EXPORT_KINDS.map(({ kind, label }) => (
              <View key={kind} style={[ui.heading, isUrdu && ui.rtlRow]}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                  {tx(`boqVersion.export.${kind.toLowerCase()}`, label)}
                </Text>
                <Action
                  title="PDF"
                  secondary
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => void handleExport(kind, "pdf")}
                />
                <Action
                  title="XLSX"
                  secondary
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => void handleExport(kind, "xlsx")}
                />
              </View>
            ))}
          </>
        ) : null}

        {busy ? (
          <View style={ui.busy}>
            <ActivityIndicator color={COLORS.navy} />
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

type Tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) => string;

function ItemPanel(props: {
  item: BOQItem;
  mode: "trace" | "adjust" | "waive" | "elements";
  locked: boolean;
  isUrdu: boolean;
  tx: Tx;
  onChanged: () => void;
  onClose: () => void;
}) {
  const { item, mode, isUrdu, tx } = props;
  const [trace, setTrace] = useState<ItemTrace | null>(null);
  const [adjustments, setAdjustments] = useState<Adjustment[]>([]);
  const [elements, setElements] = useState<DrawingElement[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [kind, setKind] = useState<"DELTA" | "REPLACE">("DELTA");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadPanel() {
      setLoading(true);
      setError("");
      try {
        if (mode === "trace") {
          const result = await getItemTrace(item.id);
          if (!cancelled) setTrace(result);
        } else if (mode === "adjust") {
          const result = await listAdjustments(item.id);
          if (!cancelled) setAdjustments(result);
        } else if (mode === "elements") {
          const result = await listItemSourceElements(item.id);
          if (!cancelled) setElements(result);
        }
      } catch (err) {
        if (!cancelled) setError(describeError(err, tx("boqVersion.actionFailure", "Action failed.")));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadPanel();
    return () => {
      cancelled = true;
    };
  }, [item.id, mode]);

  async function submitAdjustment() {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      setError(tx("boqVersion.valueInvalid", "Enter a valid number."));
      return;
    }
    if (!reason.trim()) {
      setError(tx("boqVersion.reasonRequired", "Enter a reason."));
      return;
    }
    setBusy(true);
    setError("");
    try {
      await addAdjustment(item.id, { kind, value: parsed, reason: reason.trim() });
      setValue("");
      setReason("");
      setAdjustments(await listAdjustments(item.id));
      props.onChanged();
    } catch (err) {
      setError(describeError(err, tx("boqVersion.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(adjustment: Adjustment) {
    if (!reason.trim()) {
      setError(tx("boqVersion.revokeReason", "Enter a reason in the field above to revoke."));
      return;
    }
    setBusy(true);
    setError("");
    try {
      await revokeAdjustment(adjustment.id, reason.trim());
      setReason("");
      setAdjustments(await listAdjustments(item.id));
      props.onChanged();
    } catch (err) {
      setError(describeError(err, tx("boqVersion.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  async function submitWaive() {
    if (!reason.trim()) {
      setError(tx("boqVersion.reasonRequired", "Enter a reason."));
      return;
    }
    setBusy(true);
    setError("");
    try {
      await waiveItemReview(item.id, reason.trim());
      props.onChanged();
      props.onClose();
    } catch (err) {
      setError(describeError(err, tx("boqVersion.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={ui.panel}>
      {loading ? <ActivityIndicator color={COLORS.navy} /> : null}
      {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

      {mode === "trace" && trace ? (
        <>
          <Text style={[ui.label, isUrdu && ui.rtlText]}>
            {tx("boqVersion.ledger", "Measurements ({{count}})", { count: trace.ledger.length })}
          </Text>
          {trace.ledger.slice(0, 20).map((row) => (
            <Text key={row.id} style={[ui.muted, isUrdu && ui.rtlText]}>
              {`${row.work_item_code}: ${formatNumber(row.quantity_net)} ${row.unit} · ${row.formula_code}`}
              {row.warnings.length > 0 ? ` · ${row.warnings.join("; ")}` : ""}
            </Text>
          ))}
          {trace.ledger.length > 20 ? (
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("boqVersion.more", "+{{count}} more", { count: trace.ledger.length - 20 })}
            </Text>
          ) : null}

          {trace.deductions.length > 0 ? (
            <>
              <Text style={[ui.label, isUrdu && ui.rtlText]}>
                {tx("boqVersion.deductions", "Deductions ({{count}})", { count: trace.deductions.length })}
              </Text>
              {trace.deductions.slice(0, 20).map((d) => (
                <Text key={d.id} style={[ui.muted, isUrdu && ui.rtlText]}>
                  {`${d.deduction_type}: ${formatNumber(d.quantity)} ${d.unit}`}
                  {d.explanation ? ` · ${d.explanation}` : ""}
                </Text>
              ))}
            </>
          ) : null}

          {trace.bar_marks.length > 0 ? (
            <>
              <Text style={[ui.label, isUrdu && ui.rtlText]}>
                {tx("boqVersion.barMarks", "Bar marks ({{count}})", { count: trace.bar_marks.length })}
              </Text>
              {trace.bar_marks.slice(0, 20).map((m) => (
                <Text key={m.id} style={[ui.muted, isUrdu && ui.rtlText]}>
                  {`${m.mark}: ${formatNumber(m.dia_mm, 0)} mm × ${m.count} · ${formatNumber(m.total_kg)} kg`}
                </Text>
              ))}
            </>
          ) : null}

          {trace.adjustments.length > 0 ? (
            <>
              <Text style={[ui.label, isUrdu && ui.rtlText]}>
                {tx("boqVersion.adjustments", "Adjustments")}
              </Text>
              {trace.adjustments.map((a) => (
                <Text key={a.id} style={[ui.muted, isUrdu && ui.rtlText]}>
                  {`${a.kind} ${formatNumber(a.value)} · ${a.reason}${a.revoked_at ? " (revoked)" : ""}`}
                </Text>
              ))}
            </>
          ) : null}
        </>
      ) : null}

      {mode === "adjust" ? (
        <>
          {adjustments.map((a) => (
            <View key={a.id} style={ui.boqItem}>
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {`${a.kind} ${formatNumber(a.value)} · ${a.reason}${a.revoked_at ? " (revoked)" : ""}`}
              </Text>
              {!a.revoked_at && !props.locked ? (
                <Action
                  title={tx("boqVersion.revoke", "Revoke")}
                  secondary
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => void revoke(a)}
                />
              ) : null}
            </View>
          ))}

          {!props.locked ? (
            <>
              <View style={[ui.row, isUrdu && ui.rtlRow]}>
                <Action
                  title={tx("boqVersion.delta", "Add / subtract")}
                  secondary={kind !== "DELTA"}
                  isUrdu={isUrdu}
                  onPress={() => setKind("DELTA")}
                />
                <Action
                  title={tx("boqVersion.replace", "Set total")}
                  secondary={kind !== "REPLACE"}
                  isUrdu={isUrdu}
                  onPress={() => setKind("REPLACE")}
                />
              </View>
              <Field
                label={tx("boqVersion.adjustValue", "Value ({{unit}})", { unit: item.unit })}
                value={value}
                onChangeText={setValue}
                keyboardType="decimal-pad"
                isUrdu={isUrdu}
              />
              <Field
                label={tx("boqVersion.reason", "Reason")}
                value={reason}
                onChangeText={setReason}
                isUrdu={isUrdu}
              />
              <Action
                title={tx("boqVersion.addAdjustment", "Add adjustment")}
                disabled={busy}
                isUrdu={isUrdu}
                onPress={() => void submitAdjustment()}
              />
            </>
          ) : null}
        </>
      ) : null}

      {mode === "elements" ? (
        <>
          <Text style={[ui.label, isUrdu && ui.rtlText]}>
            {tx("boqVersion.elementsCount", "Drawing elements ({{count}})", { count: elements.length })}
          </Text>
          {elements.slice(0, 30).map((element) => (
            <Text key={element.id} style={[ui.muted, isUrdu && ui.rtlText]}>
              {`${element.name ?? element.ifc_type} · ${formatNumber(element.quantity)} ${element.unit ?? ""}`}
              {element.raw_material_text ? ` · ${element.raw_material_text}` : ""}
            </Text>
          ))}
          {elements.length > 30 ? (
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("boqVersion.more", "+{{count}} more", { count: elements.length - 30 })}
            </Text>
          ) : null}
        </>
      ) : null}

      {mode === "waive" ? (
        <>
          <Field
            label={tx("boqVersion.waiveReason", "Reason for waiving the review")}
            value={reason}
            onChangeText={setReason}
            isUrdu={isUrdu}
          />
          <Action
            title={tx("boqVersion.waive", "Waive review")}
            disabled={busy}
            isUrdu={isUrdu}
            onPress={() => void submitWaive()}
          />
        </>
      ) : null}
    </View>
  );
}

function SnapshotRow(props: {
  snapshot: Snapshot;
  locale: string;
  isUrdu: boolean;
  tx: Tx;
}) {
  const { snapshot, locale, isUrdu, tx } = props;
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<SnapshotItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && rows === null) {
      setLoading(true);
      setError("");
      try {
        setRows(await listSnapshotItems(snapshot.id));
      } catch (err) {
        setError(describeError(err, tx("boqVersion.actionFailure", "Action failed.")));
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <View>
      <Pressable onPress={() => void toggle()} accessibilityRole="button">
        <InfoRow
          label={`#${snapshot.version_no} · ${snapshot.purpose}`}
          value={tx("boqVersion.snapshotItems", "{{count}} items", { count: snapshot.item_count })}
          isUrdu={isUrdu}
        />
      </Pressable>

      {open ? (
        <View style={ui.panel}>
          {loading ? <ActivityIndicator color={COLORS.navy} /> : null}
          {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
          {(rows ?? []).slice(0, 50).map((row) => (
            <Text key={row.id} style={[ui.muted, isUrdu && ui.rtlText]}>
              {`${row.line_no}. ${row.material_name} · ${formatNumber(row.quantity)} ${row.unit}`}
              {row.amount != null ? ` · ${formatMoney(row.amount, locale, "-")}` : ""}
            </Text>
          ))}
          {rows && rows.length > 50 ? (
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("boqVersion.more", "+{{count}} more", { count: rows.length - 50 })}
            </Text>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function RebarSummaryPanel(props: { versionId: string; isUrdu: boolean; tx: Tx }) {
  const { versionId, isUrdu, tx } = props;
  const [summary, setSummary] = useState<RebarSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getRebarSummary(versionId)
      .then((result) => {
        if (!cancelled) setSummary(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, tx("boqVersion.actionFailure", "Action failed.")));
      });
    return () => {
      cancelled = true;
    };
  }, [versionId]);

  return (
    <View style={ui.panel}>
      {!summary && !error ? <ActivityIndicator color={COLORS.navy} /> : null}
      {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
      {summary ? (
        <>
          {summary.rows.map((row, index) => (
            <InfoRow
              key={index}
              label={`${row.designation ?? `${formatNumber(row.dia_mm, 0)} mm`}${row.grade ? ` · ${row.grade}` : ""}`}
              value={`${formatNumber(row.total_kg)} kg · ${formatNumber(row.total_len_m, 1)} m`}
              isUrdu={isUrdu}
            />
          ))}
          <InfoRow label={tx("boqVersion.rebarTotal", "Total steel")} value={`${formatNumber(summary.total_kg)} kg`} isUrdu={isUrdu} />
          <InfoRow label={tx("boqVersion.rebarScheduled", "From confirmed schedules")} value={`${formatNumber(summary.tier1_kg)} kg`} isUrdu={isUrdu} />
          <InfoRow label={tx("boqVersion.rebarEstimated", "Estimated by rules")} value={`${formatNumber(Number(summary.tier2_kg) + Number(summary.tier3_estimate_kg))} kg`} isUrdu={isUrdu} />
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {summary.bbs_exportable
              ? tx("boqVersion.bbsReady", "A bar bending schedule export is available.")
              : tx("boqVersion.bbsNotReady", "Import and confirm a bar schedule to enable the bar bending schedule export.")}
          </Text>
        </>
      ) : null}
    </View>
  );
}
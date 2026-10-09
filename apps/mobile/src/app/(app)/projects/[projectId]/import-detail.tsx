import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {addScheduleRow, archiveRebarImport, archiveScheduleImport, bulkReviewRebarRows, bulkReviewScheduleRows, confirmRebarImport, confirmScheduleImport, getRebarImport, getScheduleImport,
  listRebarImports, rejectRebarImport, rejectScheduleImport, rematchScheduleImport, updateRebarRow, updateScheduleRow,
} from "../../../../api/imports";
import type {RebarRow, ReviewDecision, ScheduleImport, ScheduleRow,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, InfoRow, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

type Kind = "schedule" | "rebar";
type FieldDef = readonly [key: string, label: string];

const PAGE = 15;

const SCHEDULE_FIELDS: FieldDef[] = [
  ["mark", "Mark"],
  ["description", "Description"],
  ["quantity", "Quantity"],
  ["unit", "Unit"],
  ["work_item_code", "Work item code"],
];

const REBAR_FIELDS: FieldDef[] = [
  ["mark", "Mark"],
  ["designation", "Bar size (for example T12)"],
  ["dia_mm", "Diameter (mm)"],
  ["count", "Count"],
  ["spacing_mm", "Spacing (mm)"],
  ["cut_len_mm", "Cut length (mm)"],
];

const NUMERIC = new Set(["quantity", "dia_mm", "count", "spacing_mm", "cut_len_mm"]);

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function buildPayload(
  form: Record<string, string>,
  fields: FieldDef[],
): { payload: Record<string, string | number> } | { invalid: string } {
  const payload: Record<string, string | number> = {};
  for (const [key] of fields) {
    const raw = (form[key] ?? "").trim();
    if (raw === "") continue;
    if (NUMERIC.has(key)) {
      const value = Number(raw);
      if (!Number.isFinite(value) || value < 0) return { invalid: key };
      payload[key] = value;
    } else {
      payload[key] = raw;
    }
  }
  return { payload };
}

function decisionTone(status: string): "neutral" | "good" | "warn" | "bad" {
  if (status === "CONFIRMED") return "good";
  if (status === "REJECTED") return "bad";
  return "warn";
}

export default function ImportDetailScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; importId?: string; kind?: string }>();
  const projectId = first(params.projectId);
  const importId = first(params.importId);
  const kind: Kind = first(params.kind) === "rebar" ? "rebar" : "schedule";
  const fields = kind === "schedule" ? SCHEDULE_FIELDS : REBAR_FIELDS;

  const [permissions, setPermissions] = useState<string[]>([]);
  const [header, setHeader] = useState<ScheduleImport | null>(null);
  const [scheduleRows, setScheduleRows] = useState<ScheduleRow[]>([]);
  const [rebarRows, setRebarRows] = useState<RebarRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [rerun, setRerun] = useState(false);
  const [filter, setFilter] = useState<"ALL" | ReviewDecision>("ALL");
  const [page, setPage] = useState(1);
  const [editingId, setEditingId] = useState(""); // row id, "new", or ""
  const [form, setForm] = useState<Record<string, string>>({});

  const canImport = hasPerm(permissions, PERM.SCHEDULE_IMPORT);
  const editable = header?.status === "PENDING_REVIEW" || header?.status === "CONFIRMED";

  const rows: { id: string; review_status: string }[] =
    kind === "schedule" ? scheduleRows : rebarRows;
  const pendingIds = rows.filter((r) => r.review_status === "PENDING").map((r) => r.id);
  const shownRows =
    filter === "ALL" ? rows : rows.filter((r) => r.review_status === filter);
  const pages = Math.max(1, Math.ceil(shownRows.length / PAGE));
  const pageIds = new Set(shownRows.slice((page - 1) * PAGE, page * PAGE).map((r) => r.id));

  const load = useCallback(
    async (silent = false) => {
      if (!projectId || !importId) {
        setError(tx("importDetail.notFound", "Import not found."));
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

        if (kind === "schedule") {
          const detail = await getScheduleImport(importId);
          setHeader(detail);
          setScheduleRows(detail.rows);
        } else {
          const [detail, list] = await Promise.all([
            getRebarImport(importId),
            listRebarImports(projectId),
          ]);
          setRebarRows(detail.rows);
          setHeader(list.find((item) => item.id === importId) ?? null);
        }
      } catch (err) {
        setError(describeError(err, tx("importDetail.loadFailure", "Could not load the import.")));
      } finally {
        setLoading(false);
      }
    },
    [projectId, importId, kind],
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      await load(true);
    } catch (err) {
      setError(describeError(err, tx("importDetail.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  function beginEdit(row: ScheduleRow | RebarRow) {
    const next: Record<string, string> = {};
    for (const [key] of fields) {
      const value = (row as unknown as Record<string, unknown>)[key];
      next[key] = value == null ? "" : String(value);
    }
    setForm(next);
    setEditingId(row.id);
  }

  function beginNew() {
    setForm({});
    setEditingId("new");
  }

  async function saveRow() {
    const built = buildPayload(form, fields);
    if ("invalid" in built) {
      setError(tx("importDetail.invalidNumber", "Enter a valid number in {{field}}.", { field: built.invalid }));
      return;
    }
    await act(async () => {
      if (kind === "schedule") {
        if (editingId === "new") await addScheduleRow(importId!, built.payload);
        else await updateScheduleRow(editingId, built.payload);
      } else {
        await updateRebarRow(editingId, built.payload);
      }
      setEditingId("");
      setForm({});
    });
  }

  async function decide(rowId: string, status: ReviewDecision) {
    await act(async () => {
      if (kind === "schedule") await updateScheduleRow(rowId, { review_status: status });
      else await updateRebarRow(rowId, { review_status: status });
    });
  }

  async function confirmAllPending() {
    if (pendingIds.length === 0) return;
    await act(async () => {
      const ids = pendingIds.slice(0, 1000);
      if (kind === "schedule") await bulkReviewScheduleRows(importId!, ids, "CONFIRMED");
      else await bulkReviewRebarRows(importId!, ids, "CONFIRMED");
    });
  }

  async function doConfirm(rejectPending: boolean) {
    await act(async () => {
      if (kind === "schedule") {
        const result = await confirmScheduleImport(importId!, rejectPending);
        setRerun(result.rerun_recommended);
        setNotice(
          tx(
            "importDetail.confirmedSchedule",
            "Confirmed. {{created}} finishes created, {{updated}} updated, {{lines}} measurement lines, {{unlinked}} rows not linked to a room, {{mismatch}} count mismatches.",
            {
              created: result.finishes_created,
              updated: result.finishes_updated,
              lines: result.ledger_lines,
              unlinked: result.unlinked_finish_rows,
              mismatch: result.count_mismatches.length,
            },
          ),
        );
      } else {
        const result = await confirmRebarImport(importId!, rejectPending);
        setRerun(true);
        setNotice(
          tx("importDetail.confirmedRebar", "Confirmed {{confirmed}} rows, rejected {{rejected}}, {{pending}} still pending.", {
            confirmed: result.confirmed_count,
            rejected: result.rejected_count,
            pending: result.pending_count,
          }),
        );
      }
    });
  }

  function handleConfirmImport() {
    if (pendingIds.length === 0) {
      void doConfirm(false);
      return;
    }
    Alert.alert(
      tx("importDetail.pendingTitle", "Pending rows"),
      tx("importDetail.pendingBody", "{{count}} rows are still pending. Reject them and confirm the import?", {
        count: pendingIds.length,
      }),
      [
        { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
        {
          text: tx("importDetail.rejectAndConfirm", "Reject pending and confirm"),
          onPress: () => void doConfirm(true),
        },
      ],
    );
  }

  function handleRejectImport() {
    Alert.alert(tx("importDetail.rejectTitle", "Reject this import?"), "", [
      { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
      {
        text: tx("importDetail.reject", "Reject import"),
        style: "destructive",
        onPress: () =>
          void act(async () => {
            if (kind === "schedule") await rejectScheduleImport(importId!);
            else await rejectRebarImport(importId!);
          }),
      },
    ]);
  }

  async function handleArchive() {
    await act(async () => {
      if (kind === "schedule") await archiveScheduleImport(importId!);
      else await archiveRebarImport(importId!);
    });
  }

  async function handleRematch() {
    await act(async () => {
      const result = await rematchScheduleImport(importId!);
      setRerun(result.rerun_recommended);
      setNotice(
        tx("importDetail.rematched", "{{count}} rows changed.", { count: result.rows_changed }),
      );
    });
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const form_ = (
    <View style={ui.panel}>
      {fields.map(([key, label]) => (
        <Field
          key={key}
          label={tx(`importDetail.field.${key}`, label)}
          value={form[key] ?? ""}
          onChangeText={(value) => setForm((current) => ({ ...current, [key]: value }))}
          keyboardType={NUMERIC.has(key) ? "decimal-pad" : "default"}
          isUrdu={isUrdu}
        />
      ))}
      <View style={[ui.row, isUrdu && ui.rtlRow]}>
        <Action
          title={tx("importDetail.saveRow", "Save row")}
          disabled={busy}
          isUrdu={isUrdu}
          onPress={() => void saveRow()}
        />
        <Action
          title={tx("drawingsBoq.cancel", "Cancel")}
          secondary
          isUrdu={isUrdu}
          onPress={() => {
            setEditingId("");
            setForm({});
          }}
        />
      </View>
    </View>
  );

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>
                {tx("importDetail.back", "Back to imports")}
              </Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>
              {header?.file_name ?? tx("importDetail.title", "Import")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}

        {rerun && projectId ? (
          <Action
            title={tx("importDetail.runCalculation", "Run a new calculation to use this")}
            isUrdu={isUrdu}
            onPress={() =>
              router.push({
                pathname: "/projects/[projectId]/calculation",
                params: { projectId },
              })
            }
          />
        ) : null}

        {header ? (
          <View style={ui.summaryBox}>
            <InfoRow label={tx("importDetail.status", "Status")} value={header.status.replaceAll("_", " ")} isUrdu={isUrdu} />
            <InfoRow label={tx("importDetail.type", "Type")} value={kind === "schedule" ? header.schedule_kind : "REBAR"} isUrdu={isUrdu} />
            <InfoRow label={tx("importDetail.rows", "Rows")} value={String(rows.length)} isUrdu={isUrdu} />
            <InfoRow label={tx("importDetail.pending", "Pending")} value={String(pendingIds.length)} isUrdu={isUrdu} />
          </View>
        ) : null}

        {canImport && header ? (
          <View style={[ui.row, isUrdu && ui.rtlRow]}>
            {header.status === "PENDING_REVIEW" ? (
              <>
                <Action
                  title={tx("importDetail.confirmImport", "Confirm import")}
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={handleConfirmImport}
                />
                <Action
                  title={tx("importDetail.reject", "Reject import")}
                  secondary
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={handleRejectImport}
                />
              </>
            ) : null}
            {header.status === "CONFIRMED" ? (
              <Action
                title={tx("importDetail.archive", "Archive")}
                secondary
                disabled={busy}
                isUrdu={isUrdu}
                onPress={() => void handleArchive()}
              />
            ) : null}
            {kind === "schedule" && editable ? (
              <Action
                title={tx("importDetail.rematch", "Rematch to model")}
                secondary
                disabled={busy}
                isUrdu={isUrdu}
                onPress={() => void handleRematch()}
              />
            ) : null}
          </View>
        ) : null}

        {canImport && editable ? (
          <View style={[ui.row, isUrdu && ui.rtlRow]}>
            <Action
              title={tx("importDetail.confirmAll", "Confirm all pending rows")}
              secondary
              disabled={busy || pendingIds.length === 0}
              isUrdu={isUrdu}
              onPress={() => void confirmAllPending()}
            />
            {kind === "schedule" ? (
              <Action
                title={tx("importDetail.addRow", "Add row")}
                secondary
                isUrdu={isUrdu}
                onPress={beginNew}
              />
            ) : null}
          </View>
        ) : null}

        {editingId === "new" ? form_ : null}

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {(["ALL", "PENDING", "CONFIRMED", "REJECTED"] as const).map((value) => (
            <Action
              key={value}
              title={tx(`importDetail.filter.${value.toLowerCase()}`, value)}
              secondary={filter !== value}
              isUrdu={isUrdu}
              onPress={() => {
                setFilter(value);
                setPage(1);
              }}
            />
          ))}
        </View>

        {shownRows.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("importDetail.noRows", "No rows in this view.")}
          </Text>
        ) : null}

        {kind === "schedule"
          ? scheduleRows
              .filter((row) => pageIds.has(row.id))
              .map((row) => (
                <View key={row.id} style={ui.boqItem}>
                  <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                      {`#${row.row_no} ${row.mark ?? ""} ${row.description ?? row.raw_text ?? ""}`.trim()}
                    </Text>
                    <Badge label={row.review_status} tone={decisionTone(row.review_status)} />
                  </View>
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {`${formatNumber(row.quantity)} ${row.unit ?? ""}`}
                    {row.work_item_code ? ` · ${row.work_item_code}` : ""}
                    {` · ${tx("importDetail.matched", "{{count}} matched elements", { count: row.matched_element_count })}`}
                    {` · ${tx("importDetail.confidence", "confidence {{value}}", { value: formatNumber(row.confidence, 2) })}`}
                  </Text>
                  {row.quantity_defaulted ? (
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {tx("importDetail.qtyDefaulted", "Quantity was assumed, please check it.")}
                    </Text>
                  ) : null}
                  {row.notes.map((note, index) => (
                    <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{note}</Text>
                  ))}
                  {canImport && editable ? (
                    <View style={[ui.row, isUrdu && ui.rtlRow]}>
                      {row.review_status !== "CONFIRMED" ? (
                        <Action title={tx("importDetail.confirmRow", "Confirm")} disabled={busy} isUrdu={isUrdu} onPress={() => void decide(row.id, "CONFIRMED")} />
                      ) : null}
                      {row.review_status !== "REJECTED" ? (
                        <Action title={tx("importDetail.rejectRow", "Reject")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void decide(row.id, "REJECTED")} />
                      ) : null}
                      <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => beginEdit(row)} />
                    </View>
                  ) : null}
                  {editingId === row.id ? form_ : null}
                </View>
              ))
          : rebarRows
              .filter((row) => pageIds.has(row.id))
              .map((row) => (
                <View key={row.id} style={ui.boqItem}>
                  <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                      {`#${row.row_no} ${row.mark ?? row.member_mark ?? ""} ${row.designation ?? (row.dia_mm != null ? `${formatNumber(row.dia_mm, 0)} mm` : "")}`.trim()}
                    </Text>
                    <Badge label={row.review_status} tone={decisionTone(row.review_status)} />
                  </View>
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {`${row.count ?? "-"} × ${formatNumber(row.cut_len_mm, 0)} mm`}
                    {row.spacing_mm != null ? ` · @${formatNumber(row.spacing_mm, 0)} mm` : ""}
                    {row.declared_total_kg != null ? ` · ${formatNumber(row.declared_total_kg)} kg` : ""}
                    {row.matched_element_id ? ` · ${tx("importDetail.linked", "linked to model")}` : ""}
                  </Text>
                  {canImport && editable ? (
                    <View style={[ui.row, isUrdu && ui.rtlRow]}>
                      {row.review_status !== "CONFIRMED" ? (
                        <Action title={tx("importDetail.confirmRow", "Confirm")} disabled={busy} isUrdu={isUrdu} onPress={() => void decide(row.id, "CONFIRMED")} />
                      ) : null}
                      {row.review_status !== "REJECTED" ? (
                        <Action title={tx("importDetail.rejectRow", "Reject")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void decide(row.id, "REJECTED")} />
                      ) : null}
                      <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => beginEdit(row)} />
                    </View>
                  ) : null}
                  {editingId === row.id ? form_ : null}
                </View>
              ))}

        {shownRows.length > PAGE ? (
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

        {busy ? (
          <View style={ui.busy}>
            <ActivityIndicator color={COLORS.navy} />
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
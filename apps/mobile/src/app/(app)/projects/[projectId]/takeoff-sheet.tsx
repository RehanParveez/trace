import { useCallback, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {autoCalibrateSheet, bulkConfirmMeasurements, confirmMeasurement, createCalibration, deleteCalibration, deleteMeasurement, getSheetAnalysis, getTakeoffOverview, makeDefaultCalibration, prepareSheet,
  unconfirmMeasurement, updateSheet,
} from "../../../../api/takeoff";
import type {TakeoffCalibration, TakeoffMeasurement, TakeoffSheet, TakeoffSheetAnalysis,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import {measurementTitle, measurementTone, prepTone, quantityText, ratioText, reconLabel, sheetTitle, toNumber, warningText,
} from "../../../../features/drawingsBoq/takeoffText";
import { Action, Badge, COLORS, Field, InfoRow, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

const CONTENT_KINDS = ["VECTOR", "RASTER", "UNKNOWN"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function TakeoffSheetScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; drawingId?: string; sheetId?: string }>();
  const projectId = first(params.projectId) ?? "";
  const drawingId = first(params.drawingId) ?? "";
  const sheetId = first(params.sheetId) ?? "";

  const [permissions, setPermissions] = useState<string[]>([]);
  const [sheet, setSheet] = useState<TakeoffSheet | null>(null);
  const [calibrations, setCalibrations] = useState<TakeoffCalibration[]>([]);
  const [measurements, setMeasurements] = useState<TakeoffMeasurement[]>([]);
  const [analysis, setAnalysis] = useState<TakeoffSheetAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [label, setLabel] = useState("");
  const [printedScale, setPrintedScale] = useState("");
  const [scaleInput, setScaleInput] = useState("");
  const [ratioInput, setRatioInput] = useState("");
  const [calLabel, setCalLabel] = useState("");

  const canEdit = hasPerm(permissions, PERM.BOQ_UPDATE);

  const load = useCallback(async () => {
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));
      const overview = await getTakeoffOverview(drawingId);
      const current = overview.sheets.find((s) => s.id === sheetId) ?? null;
      setSheet(current);
      setLabel(current?.label ?? "");
      setPrintedScale(current?.scale_text ?? "");
      setCalibrations(overview.calibrations.filter((c) => c.sheet_id === sheetId));
      setMeasurements(overview.measurements.filter((m) => m.sheet_id === sheetId));
      if (current?.prep_status === "READY") {
        try {
          setAnalysis(await getSheetAnalysis(sheetId));
        } catch {
          setAnalysis(null);
        }
      } else {
        setAnalysis(null);
      }
      setError("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.sheet.loadFailure", "Could not load this sheet.")));
    } finally {
      setLoading(false);
    }
   
  }, [drawingId, sheetId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function run(work: () => Promise<string | void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const message = await work();
      if (message) setNotice(message);
      await load();
    } catch (err) {
      setError(describeError(err, tx("takeoff.sheet.actionFailure", "That did not work.")));
    } finally {
      setBusy(false);
    }
  }

  function calibrationNotice(result: TakeoffCalibration): string {
    const recomputed = result.measurements_recomputed ?? 0;
    const reverted = result.measurements_reverted_to_draft ?? 0;
    return recomputed || reverted
      ? tx("takeoff.sheet.recomputed", "Scale saved. {{n}} measurements recalculated, {{r}} went back to draft.", { n: recomputed, r: reverted })
      : tx("takeoff.sheet.scaleSaved", "Scale saved.");
  }

  const saveSheet = () =>
    run(async () => {
      await updateSheet(sheetId, { label: label.trim() || null, scale_text: printedScale.trim() || null });
      return tx("takeoff.sheet.saved", "Sheet saved.");
    });

  const addCalibration = () =>
    run(async () => {
      const ratio = toNumber(ratioInput);
      const text = scaleInput.trim();
      if (!text && ratio === null) {
        throw new Error(tx("takeoff.sheet.needScale", "Type a scale such as 1:100, or a ratio."));
      }
      const result = await createCalibration(sheetId, {
        method: "SCALE_RATIO",
        scale_text: text || null,
        ratio,
        label: calLabel.trim() || null,
        make_default: true,
      });
      setScaleInput("");
      setRatioInput("");
      setCalLabel("");
      return calibrationNotice(result);
    });

  const autoCalibrate = (use: "RECOMMENDED" | "DECLARED" | "DIMENSIONS") =>
    run(async () => {
      const result = await autoCalibrateSheet(sheetId, { use, make_default: true });
      const notes = result.notes.map((n) => n.message).filter(Boolean).join(" ");
      return `${calibrationNotice(result.calibration)} ${notes}`.trim();
    });

  function confirmDelete(title: string, action: () => Promise<void>) {
    Alert.alert(title, tx("takeoff.sheet.cannotUndo", "This cannot be undone."), [
      { text: tx("takeoff.cancel", "Cancel"), style: "cancel" },
      { text: tx("takeoff.delete", "Delete"), style: "destructive", onPress: () => void run(action) },
    ]);
  }

  const draftIds = measurements.filter((m) => m.status === "DRAFT").map((m) => m.id);

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const rec = analysis?.detected_scale?.recommended ?? null;
  const declared = analysis?.detected_scale?.declared?.primary ?? null;
  const notes = analysis?.detected_scale?.notes ?? [];

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>
              {sheet ? sheetTitle(tx, sheet) : tx("takeoff.sheet.title", "Sheet")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}
        {busy ? <ActivityIndicator color={COLORS.navy} /> : null}

        {sheet ? (
          <>
            <View style={ui.summaryBox}>
              <InfoRow label={tx("takeoff.sheet.status", "Reading")} value={sheet.prep_status} isUrdu={isUrdu} />
              <InfoRow label={tx("takeoff.sheet.kind", "Content")} value={sheet.content_kind} isUrdu={isUrdu} />
              <InfoRow
                label={tx("takeoff.sheet.size", "Page size (points)")}
                value={`${formatNumber(sheet.width_pt, 0)} × ${formatNumber(sheet.height_pt, 0)}`}
                isUrdu={isUrdu}
              />
              <InfoRow label={tx("takeoff.sheet.text", "Text characters")} value={String(sheet.text_chars ?? "—")} isUrdu={isUrdu} />
              <InfoRow label={tx("takeoff.sheet.vector", "Drawing operations")} value={String(sheet.vector_ops ?? "—")} isUrdu={isUrdu} />
            </View>
            {sheet.prep_error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{sheet.prep_error}</Text> : null}

            {canEdit ? (
              <>
                <Action
                  title={
                    sheet.prep_status === "READY"
                      ? tx("takeoff.sheet.readAgain", "Read this sheet again")
                      : tx("takeoff.sheet.read", "Read this sheet")
                  }
                  secondary={sheet.prep_status === "READY"}
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() => void run(async () => { await prepareSheet(sheetId, sheet.prep_status === "READY"); })}
                />
                <Field label={tx("takeoff.sheet.label", "Sheet name")} value={label} onChangeText={setLabel} isUrdu={isUrdu} />
                <Field
                  label={tx("takeoff.sheet.printedScale", "Printed scale (for example 1:100)")}
                  value={printedScale}
                  onChangeText={setPrintedScale}
                  isUrdu={isUrdu}
                />
                <Action title={tx("takeoff.sheet.save", "Save sheet")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void saveSheet()} />
                <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.contentType", "What kind of drawing is this?")}</Text>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  {CONTENT_KINDS.map((kind) => (
                    <Action
                      key={kind}
                      title={kind}
                      secondary={sheet.content_kind !== kind}
                      disabled={busy}
                      isUrdu={isUrdu}
                      onPress={() => void run(async () => { await updateSheet(sheetId, { content_kind: kind }); })}
                    />
                  ))}
                </View>
              </>
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.scale", "Scale")}</Text>
            {analysis ? (
              <View style={ui.card}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.detected", "Found on the sheet")}</Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {declared
                    ? tx("takeoff.sheet.declared", "Printed scale: {{text}}", { text: declared.text })
                    : tx("takeoff.sheet.noDeclared", "No printed scale found.")}
                </Text>
                {rec ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {tx("takeoff.sheet.recommended", "Recommended: {{text}} ({{basis}}, trust {{trust}})", {
                      text: rec.scale_text,
                      basis: rec.basis,
                      trust: formatNumber(rec.trust, 2),
                    })}
                  </Text>
                ) : null}
                {analysis.detected_scale.agreement ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {tx("takeoff.sheet.agreement", "Printed scale and printed dimensions: {{value}}", { value: analysis.detected_scale.agreement })}
                  </Text>
                ) : null}
                {analysis.stale ? (
                  <Text style={[ui.error, isUrdu && ui.rtlText]}>
                    {tx("takeoff.sheet.stale", "This reading is out of date. Read the sheet again.")}
                  </Text>
                ) : null}
                {notes.map((note, index) => (
                  <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{note.message ?? note.code}</Text>
                ))}
                {canEdit ? (
                  <View style={[ui.row, isUrdu && ui.rtlRow]}>
                    <Action title={tx("takeoff.sheet.useRecommended", "Use recommended")} disabled={busy || !rec} isUrdu={isUrdu} onPress={() => void autoCalibrate("RECOMMENDED")} />
                    <Action title={tx("takeoff.sheet.usePrinted", "Use printed scale")} secondary disabled={busy || !declared} isUrdu={isUrdu} onPress={() => void autoCalibrate("DECLARED")} />
                    <Action title={tx("takeoff.sheet.useDimensions", "Use printed dimensions")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void autoCalibrate("DIMENSIONS")} />
                  </View>
                ) : null}
              </View>
            ) : (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("takeoff.sheet.readFirst", "Read the sheet first to see the scale it shows.")}
              </Text>
            )}

            {calibrations.map((cal) => (
              <View key={cal.id} style={ui.card}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                    {`${cal.label || cal.method} · ${ratioText(cal.ratio)}`}
                  </Text>
                  <View style={[ui.row, isUrdu && ui.rtlRow]}>
                    {cal.is_default ? <Badge label={tx("takeoff.sheet.default", "default")} tone="good" /> : null}
                    <Badge label={cal.usable ? tx("takeoff.sheet.usable", "usable") : tx("takeoff.sheet.unusable", "not usable")} tone={cal.usable ? "good" : "bad"} />
                  </View>
                </View>
                {cal.reason ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{cal.reason}</Text> : null}
                {cal.check_error_pct !== null && cal.check_error_pct !== undefined ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {tx("takeoff.sheet.checkError", "Check against a known distance: {{pct}}% off", { pct: formatNumber(cal.check_error_pct, 2) })}
                  </Text>
                ) : null}
                {cal.warnings.map((warning, index) => (
                  <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{warningText(warning)}</Text>
                ))}
                {canEdit ? (
                  <View style={[ui.row, isUrdu && ui.rtlRow]}>
                    {!cal.is_default && cal.usable ? (
                      <Action
                        title={tx("takeoff.sheet.makeDefault", "Make default")}
                        secondary
                        disabled={busy}
                        isUrdu={isUrdu}
                        onPress={() => void run(async () => { await makeDefaultCalibration(cal.id); })}
                      />
                    ) : null}
                    <Action
                      title={tx("takeoff.delete", "Delete")}
                      secondary
                      disabled={busy}
                      isUrdu={isUrdu}
                      onPress={() => confirmDelete(tx("takeoff.sheet.deleteScale", "Delete this scale?"), async () => { await deleteCalibration(cal.id); })}
                    />
                  </View>
                ) : null}
              </View>
            ))}

            {canEdit ? (
              <View style={ui.card}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.addScale", "Set a scale by hand")}</Text>
                <Field label={tx("takeoff.sheet.scaleText", "Scale (for example 1:100 or 1/8\" = 1'-0\")")} value={scaleInput} onChangeText={setScaleInput} isUrdu={isUrdu} />
                <Field label={tx("takeoff.sheet.ratio", "Or the ratio as a number (100 means 1:100)")} value={ratioInput} onChangeText={setRatioInput} keyboardType="decimal-pad" isUrdu={isUrdu} />
                <Field label={tx("takeoff.sheet.calLabel", "Name (optional)")} value={calLabel} onChangeText={setCalLabel} isUrdu={isUrdu} />
                <Action title={tx("takeoff.sheet.saveScale", "Save scale")} disabled={busy} isUrdu={isUrdu} onPress={() => void addCalibration()} />
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("takeoff.sheet.twoPointNote", "Setting a scale from two points on the drawing needs the sheet view, which is on the web app.")}
                </Text>
              </View>
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.measurements", "Measurements")}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Action
                title={tx("takeoff.sheet.counts", "Counts from tags & shapes")}
                secondary
                isUrdu={isUrdu}
                onPress={() => router.push({ pathname: "/projects/[projectId]/takeoff-counts", params: { projectId, drawingId, sheetId } })}
              />
              <Action
                title={tx("takeoff.sheet.found", "Found items")}
                secondary
                isUrdu={isUrdu}
                onPress={() => router.push({ pathname: "/projects/[projectId]/takeoff-found", params: { projectId, drawingId, sheetId } })}
              />
              {canEdit && draftIds.length > 0 ? (
                <Action
                  title={tx("takeoff.sheet.confirmDrafts", "Confirm {{count}} drafts", { count: draftIds.length })}
                  disabled={busy}
                  isUrdu={isUrdu}
                  onPress={() =>
                    void run(async () => {
                      const result = await bulkConfirmMeasurements(draftIds);
                      const reasons = result.failed.map((f) => f.message ?? f.code ?? "").filter(Boolean).join(" ");
                      return `${tx("takeoff.drawing.confirmed", "{{ok}} confirmed, {{failed}} could not be confirmed.", { ok: result.confirmed.length, failed: result.failed.length })} ${reasons}`.trim();
                    })
                  }
                />
              ) : null}
            </View>
            {measurements.length === 0 ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("takeoff.sheet.noMeasurements", "No measurements on this sheet yet. Use Counts or Found items to add some.")}
              </Text>
            ) : null}
            {measurements.map((m) => (
              <View key={m.id} style={ui.boqItem}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{measurementTitle(tx, m)}</Text>
                  <Badge label={m.status} tone={measurementTone(m.status)} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[m.kind, m.quantity_mode, m.work_item_code ?? tx("takeoff.noWorkItem", "no work item"), reconLabel(tx, m.recon_mode)].join(" · ")}
                </Text>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{quantityText(m)}</Text>
                {(m.computed?.warnings ?? []).map((warning, index) => (
                  <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{warning}</Text>
                ))}
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  <Action
                    title={canEdit ? tx("takeoff.edit", "Edit") : tx("takeoff.view", "View")}
                    secondary
                    isUrdu={isUrdu}
                    onPress={() =>
                      router.push({
                        pathname: "/projects/[projectId]/takeoff-measurement",
                        params: { projectId, drawingId, sheetId, measurementId: m.id },
                      })
                    }
                  />
                  {canEdit ? (
                    <>
                      <Action
                        title={m.status === "CONFIRMED" ? tx("takeoff.unconfirm", "Unconfirm") : tx("takeoff.confirm", "Confirm")}
                        secondary={m.status === "CONFIRMED"}
                        disabled={busy}
                        isUrdu={isUrdu}
                        onPress={() =>
                          void run(async () => {
                            if (m.status === "CONFIRMED") await unconfirmMeasurement(m.id);
                            else await confirmMeasurement(m.id);
                          })
                        }
                      />
                      <Action
                        title={tx("takeoff.delete", "Delete")}
                        secondary
                        disabled={busy}
                        isUrdu={isUrdu}
                        onPress={() => confirmDelete(tx("takeoff.sheet.deleteMeasurement", "Delete this measurement?"), async () => { await deleteMeasurement(m.id); })}
                      />
                    </>
                  ) : null}
                </View>
              </View>
            ))}
          </>
        ) : (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.notFound", "This sheet was not found.")}</Text>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
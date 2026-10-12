import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getTakeoffOverview, listTakeoffModes, previewMeasurement, updateMeasurement } from "../../../../api/takeoff";
import type { TakeoffCalibration, TakeoffMeasurement, TakeoffMode, TakeoffParams, TakeoffPreview, TakeoffReconMode } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { RECON_MODES, measurementTitle, quantityText, ratioText, reconHint, reconLabel, toNumber } from "../../../../features/drawingsBoq/takeoffText";
import { Action, COLORS, Field, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

const DIMS = ["DRAWN", "SPECIFIED", "ASSUMED"] as const;
const SIZE_PARAMS = ["height_mm", "thickness_mm", "width_mm", "depth_mm", "length_mm"] as const;

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function TakeoffMeasurementScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; drawingId?: string; sheetId?: string; measurementId?: string }>();
  const drawingId = first(params.drawingId) ?? "";
  const measurementId = first(params.measurementId) ?? "";

  const [permissions, setPermissions] = useState<string[]>([]);
  const [m, setM] = useState<TakeoffMeasurement | null>(null);
  const [modes, setModes] = useState<TakeoffMode[]>([]);
  const [calibrations, setCalibrations] = useState<TakeoffCalibration[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<TakeoffPreview | null>(null);

  const [mode, setMode] = useState("");
  const [sizes, setSizes] = useState<Record<string, string>>({});
  const [repeat, setRepeat] = useState("1");
  const [dims, setDims] = useState<(typeof DIMS)[number]>("DRAWN");
  const [workItem, setWorkItem] = useState("");
  const [label, setLabel] = useState("");
  const [tag, setTag] = useState("");
  const [grade, setGrade] = useState("");
  const [recon, setRecon] = useState<TakeoffReconMode>("AUTO");
  const [calibrationId, setCalibrationId] = useState<string | null>(null);
  const [openings, setOpenings] = useState<{ role: "DOOR" | "WINDOW" | "OPENING"; width: string; height: string; nos: string }[]>([]);
  const [adjustments, setAdjustments] = useState<{ op: "LESS" | "ADD"; value: string; label: string }[]>([]);

  const canEdit = hasPerm(permissions, PERM.BOQ_UPDATE);

  const load = useCallback(async () => {
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));
      const [overview, modeList] = await Promise.all([getTakeoffOverview(drawingId), listTakeoffModes()]);
      const current = overview.measurements.find((x) => x.id === measurementId) ?? null;
      setM(current);
      setModes(modeList);
      if (current) {
        setCalibrations(overview.calibrations.filter((c) => c.sheet_id === current.sheet_id && c.usable));
        setMode(current.quantity_mode);
        const p = current.params ?? {};
        const next: Record<string, string> = {};
        for (const key of SIZE_PARAMS) next[key] = p[key] !== undefined && p[key] !== null ? String(p[key]) : "";
        setSizes(next);
        setRepeat(String(p.repeat ?? 1));
        setDims(p.dims_basis ?? "DRAWN");
        setOpenings((p.openings ?? []).map((o) => ({ role: o.role, width: String(o.width_mm), height: String(o.height_mm), nos: String(o.nos) })));
        setAdjustments((p.adjustments ?? []).map((a) => ({ op: a.op, value: String(a.value), label: a.label ?? "" })));
        setWorkItem(current.work_item_code ?? "");
        setLabel(current.label ?? "");
        setTag(current.tag ?? "");
        setGrade(current.material_grade ?? "");
        setRecon(current.recon_mode);
        setCalibrationId(current.calibration_id);
      }
      setError("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.measurement.loadFailure", "Could not load this measurement.")));
    } finally {
      setLoading(false);
    }
   
  }, [drawingId, measurementId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const kindModes = modes.filter((x) => m && x.kind === m.kind);
  const activeMode = kindModes.find((x) => x.quantity_mode === mode);

  function buildParams(): TakeoffParams {
    const out: TakeoffParams = {};
    for (const key of SIZE_PARAMS) {
      const n = toNumber(sizes[key] ?? "");
      if (n !== null) out[key] = n;
    }
    out.repeat = Math.max(1, Math.trunc(toNumber(repeat) ?? 1));
    out.dims_basis = dims;
    out.openings = openings
      .map((o) => ({ role: o.role, width_mm: toNumber(o.width) ?? 0, height_mm: toNumber(o.height) ?? 0, nos: Math.max(1, Math.trunc(toNumber(o.nos) ?? 1)) }))
      .filter((o) => o.width_mm > 0 && o.height_mm > 0);
    out.adjustments = adjustments
      .map((a) => ({ op: a.op, value: toNumber(a.value) ?? 0, label: a.label.trim() || null }))
      .filter((a) => a.value > 0);
    return out;
  }

  async function runPreview() {
    if (!m) return;
    setBusy(true);
    setError("");
    try {
      setPreview(
        await previewMeasurement({
          sheet_id: m.sheet_id,
          kind: m.kind,
          quantity_mode: mode,
          geometry: m.geometry,
          params: buildParams(),
          calibration_id: calibrationId,
          source: m.source,
        }),
      );
    } catch (err) {
      setError(describeError(err, tx("takeoff.measurement.previewFailure", "Could not work out the quantity.")));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!m) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const saved = await updateMeasurement(m.id, {
        quantity_mode: mode,
        params: buildParams(),
        calibration_id: calibrationId,
        work_item_code: workItem.trim() || null,
        label: label.trim() || null,
        tag: tag.trim() || null,
        material_grade: grade.trim() || null,
        recon_mode: recon,
      });
      setM(saved);
      setNotice(
        saved.status === "DRAFT" && m.status === "CONFIRMED"
          ? tx("takeoff.measurement.savedDraft", "Saved. It went back to draft, so confirm it again.")
          : tx("takeoff.measurement.saved", "Saved."),
      );
    } catch (err) {
      setError(describeError(err, tx("takeoff.measurement.saveFailure", "Could not save the measurement.")));
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

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{m ? measurementTitle(tx, m) : tx("takeoff.measurement.title", "Measurement")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}
        {busy ? <ActivityIndicator color={COLORS.navy} /> : null}

        {!m ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("takeoff.measurement.notFound", "This measurement was not found.")}</Text>
        ) : (
          <>
            <View style={ui.summaryBox}>
              <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${m.kind} · ${m.status} · ${quantityText(m)}`}</Text>
              {m.computed?.formula ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{m.computed.formula}</Text> : null}
              {(m.computed?.warnings ?? []).map((w, i) => (
                <Text key={i} style={[ui.muted, isUrdu && ui.rtlText]}>{w}</Text>
              ))}
            </View>

            <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("takeoff.measurement.mode", "How the quantity is worked out")}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {kindModes.map((x) => (
                <Action key={x.quantity_mode} title={`${x.quantity_mode} (${x.output_unit})`} secondary={mode !== x.quantity_mode} disabled={!canEdit} isUrdu={isUrdu} onPress={() => setMode(x.quantity_mode)} />
              ))}
            </View>
            {activeMode && activeMode.required_params.length > 0 ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("takeoff.measurement.required", "Needs: {{list}}", { list: activeMode.required_params.join(", ") })}
              </Text>
            ) : null}

            {SIZE_PARAMS.map((key) => (
              <Field key={key} label={key.replace("_mm", "") + " (mm)"} value={sizes[key] ?? ""} onChangeText={(v) => setSizes((cur) => ({ ...cur, [key]: v }))} keyboardType="decimal-pad" editable={canEdit} isUrdu={isUrdu} />
            ))}
            <Field label={tx("takeoff.measurement.repeat", "Repeat (identical floors or units)")} value={repeat} onChangeText={setRepeat} keyboardType="decimal-pad" editable={canEdit} isUrdu={isUrdu} />

            <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("takeoff.measurement.dims", "Where the sizes come from")}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {DIMS.map((d) => (
                <Action key={d} title={d} secondary={dims !== d} disabled={!canEdit} isUrdu={isUrdu} onPress={() => setDims(d)} />
              ))}
            </View>

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.measurement.openings", "Openings to deduct")}</Text>
            {openings.map((o, i) => (
              <View key={i} style={ui.card}>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  {(["DOOR", "WINDOW", "OPENING"] as const).map((role) => (
                    <Action key={role} title={role} secondary={o.role !== role} disabled={!canEdit} isUrdu={isUrdu} onPress={() => setOpenings((cur) => cur.map((x, j) => (j === i ? { ...x, role } : x)))} />
                  ))}
                </View>
                <Field label={tx("takeoff.measurement.width", "Width (mm)")} value={o.width} onChangeText={(v) => setOpenings((cur) => cur.map((x, j) => (j === i ? { ...x, width: v } : x)))} keyboardType="decimal-pad" editable={canEdit} isUrdu={isUrdu} />
                <Field label={tx("takeoff.measurement.height", "Height (mm)")} value={o.height} onChangeText={(v) => setOpenings((cur) => cur.map((x, j) => (j === i ? { ...x, height: v } : x)))} keyboardType="decimal-pad" editable={canEdit} isUrdu={isUrdu} />
                <Field label={tx("takeoff.measurement.nos", "Number")} value={o.nos} onChangeText={(v) => setOpenings((cur) => cur.map((x, j) => (j === i ? { ...x, nos: v } : x)))} keyboardType="decimal-pad" editable={canEdit} isUrdu={isUrdu} />
                {canEdit ? <Action title={tx("takeoff.remove", "Remove")} secondary isUrdu={isUrdu} onPress={() => setOpenings((cur) => cur.filter((_, j) => j !== i))} /> : null}
              </View>
            ))}
            {canEdit ? (
              <Action title={tx("takeoff.measurement.addOpening", "Add opening")} secondary isUrdu={isUrdu} onPress={() => setOpenings((cur) => [...cur, { role: "DOOR", width: "", height: "", nos: "1" }])} />
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.measurement.adjustments", "Adjustments")}</Text>
            {adjustments.map((a, i) => (
              <View key={i} style={ui.card}>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  {(["LESS", "ADD"] as const).map((op) => (
                    <Action key={op} title={op} secondary={a.op !== op} disabled={!canEdit} isUrdu={isUrdu} onPress={() => setAdjustments((cur) => cur.map((x, j) => (j === i ? { ...x, op } : x)))} />
                  ))}
                </View>
                <Field label={tx("takeoff.measurement.adjValue", "Amount (in the unit of the result)")} value={a.value} onChangeText={(v) => setAdjustments((cur) => cur.map((x, j) => (j === i ? { ...x, value: v } : x)))} keyboardType="decimal-pad" editable={canEdit} isUrdu={isUrdu} />
                <Field label={tx("takeoff.measurement.adjLabel", "Reason")} value={a.label} onChangeText={(v) => setAdjustments((cur) => cur.map((x, j) => (j === i ? { ...x, label: v } : x)))} editable={canEdit} isUrdu={isUrdu} />
                {canEdit ? <Action title={tx("takeoff.remove", "Remove")} secondary isUrdu={isUrdu} onPress={() => setAdjustments((cur) => cur.filter((_, j) => j !== i))} /> : null}
              </View>
            ))}
            {canEdit ? (
              <Action title={tx("takeoff.measurement.addAdjustment", "Add adjustment")} secondary isUrdu={isUrdu} onPress={() => setAdjustments((cur) => [...cur, { op: "LESS", value: "", label: "" }])} />
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.measurement.details", "Details")}</Text>
            <Field label={tx("takeoff.counts.workItem", "Work item code")} value={workItem} onChangeText={setWorkItem} editable={canEdit} isUrdu={isUrdu} />
            <Field label={tx("takeoff.counts.label", "Name")} value={label} onChangeText={setLabel} editable={canEdit} isUrdu={isUrdu} />
            <Field label={tx("takeoff.measurement.tag", "Tag")} value={tag} onChangeText={setTag} editable={canEdit} isUrdu={isUrdu} />
            <Field label={tx("takeoff.counts.grade", "Material grade (optional)")} value={grade} onChangeText={setGrade} editable={canEdit} isUrdu={isUrdu} />

            <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("takeoff.counts.reconMode", "If the model already has this work item")}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {RECON_MODES.map((r) => (
                <Action key={r} title={reconLabel(tx, r)} secondary={recon !== r} disabled={!canEdit} isUrdu={isUrdu} onPress={() => setRecon(r)} />
              ))}
            </View>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>{reconHint(tx, recon)}</Text>

            <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("takeoff.measurement.scale", "Scale used")}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Action title={tx("takeoff.measurement.sheetDefault", "Sheet default")} secondary={calibrationId !== null} disabled={!canEdit} isUrdu={isUrdu} onPress={() => setCalibrationId(null)} />
              {calibrations.map((c) => (
                <Action key={c.id} title={`${c.label || c.method} ${ratioText(c.ratio)}`} secondary={calibrationId !== c.id} disabled={!canEdit} isUrdu={isUrdu} onPress={() => setCalibrationId(c.id)} />
              ))}
            </View>

            {preview ? (
              <View style={ui.summaryBox}>
                <Text style={[preview.ok ? ui.itemTitle : ui.error, isUrdu && ui.rtlText]}>
                  {preview.ok ? `${formatNumber(preview.quantity ?? "0")} ${preview.unit ?? ""}`.trim() : preview.error?.message ?? ""}
                </Text>
                {preview.formula ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{preview.formula}</Text> : null}
                {preview.warnings.map((w, i) => (
                  <Text key={i} style={[ui.muted, isUrdu && ui.rtlText]}>{w}</Text>
                ))}
              </View>
            ) : null}

            {canEdit ? (
              <View style={[ui.row, isUrdu && ui.rtlRow]}>
                <Action title={tx("takeoff.preview", "Preview")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void runPreview()} />
                <Action title={tx("takeoff.measurement.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void save()} />
              </View>
            ) : null}
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
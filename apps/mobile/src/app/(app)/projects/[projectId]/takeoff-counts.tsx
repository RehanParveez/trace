import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { createMeasurement, getSheetShape, getSheetTag, listSheetShapes, listSheetTags, previewMeasurement } from "../../../../api/takeoff";
import type { TakeoffCountSuggestion, TakeoffPreview, TakeoffReconMode, TakeoffShape, TakeoffTag } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { RECON_MODES, reconHint, reconLabel } from "../../../../features/drawingsBoq/takeoffText";
import { Action, Badge, COLORS, Field, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function TakeoffCountsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; drawingId?: string; sheetId?: string }>();
  const sheetId = first(params.sheetId) ?? "";

  const [permissions, setPermissions] = useState<string[]>([]);
  const [tags, setTags] = useState<TakeoffTag[]>([]);
  const [shapes, setShapes] = useState<TakeoffShape[]>([]);
  const [tab, setTab] = useState<"tags" | "shapes">("tags");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [picked, setPicked] = useState<{ title: string; note: string | null; count: number; suggestion: TakeoffCountSuggestion } | null>(null);
  const [workItem, setWorkItem] = useState("");
  const [label, setLabel] = useState("");
  const [grade, setGrade] = useState("");
  const [recon, setRecon] = useState<TakeoffReconMode>("AUTO");
  const [preview, setPreview] = useState<TakeoffPreview | null>(null);

  const canEdit = hasPerm(permissions, PERM.BOQ_UPDATE);

  const load = useCallback(async () => {
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));
      const [tagResult, shapeResult] = await Promise.all([listSheetTags(sheetId), listSheetShapes(sheetId)]);
      setTags(tagResult.tags);
      setShapes(shapeResult.shapes);
      setError("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.counts.loadFailure", "Could not read tags and shapes. Read the sheet first.")));
    } finally {
      setLoading(false);
    }
    
  }, [sheetId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function pick(work: () => Promise<{ title: string; note: string | null; count: number; suggestion: TakeoffCountSuggestion }>) {
    setBusy(true);
    setError("");
    setNotice("");
    setPreview(null);
    try {
      const result = await work();
      setPicked(result);
      setLabel(result.suggestion.label ?? "");
    } catch (err) {
      setError(describeError(err, tx("takeoff.counts.pickFailure", "Could not load that count.")));
    } finally {
      setBusy(false);
    }
  }

  const pickTag = (tag: string) =>
    pick(async () => {
      const d = await getSheetTag(sheetId, tag);
      return { title: d.tag, note: d.note, count: d.count, suggestion: d.suggestion };
    });

  const pickShape = (shape: TakeoffShape) =>
    pick(async () => {
      const d = await getSheetShape(sheetId, shape.id);
      return { title: `${d.shape.shape} ${formatNumber(d.shape.a_mm ?? d.shape.a_pt, 0)} × ${formatNumber(d.shape.b_mm ?? d.shape.b_pt, 0)}`, note: null, count: d.shape.count, suggestion: d.suggestion };
    });

  function payload() {
    if (!picked) return null;
    return {
      kind: "COUNT" as const,
      quantity_mode: "DIRECT",
      geometry: picked.suggestion.geometry,
      source: picked.suggestion.source,
      tag: picked.suggestion.tag,
      label: label.trim() || picked.suggestion.label,
      work_item_code: workItem.trim() || null,
      material_grade: grade.trim() || null,
      recon_mode: recon,
    };
  }

  async function runPreview() {
    const body = payload();
    if (!body) return;
    setBusy(true);
    setError("");
    try {
      setPreview(await previewMeasurement({ sheet_id: sheetId, kind: body.kind, quantity_mode: body.quantity_mode, geometry: body.geometry, source: body.source }));
    } catch (err) {
      setError(describeError(err, tx("takeoff.counts.previewFailure", "Could not work out the count.")));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    const body = payload();
    if (!body) return;
    setBusy(true);
    setError("");
    try {
      await createMeasurement(sheetId, body);
      setNotice(tx("takeoff.counts.saved", "Saved as a draft measurement. Confirm it on the sheet."));
      setPicked(null);
      setPreview(null);
      setWorkItem("");
      setGrade("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.counts.saveFailure", "Could not save the count.")));
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
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("takeoff.counts.title", "Counts")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}
        {busy ? <ActivityIndicator color={COLORS.navy} /> : null}

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          <Action title={tx("takeoff.counts.tags", "Tags ({{n}})", { n: tags.length })} secondary={tab !== "tags"} isUrdu={isUrdu} onPress={() => setTab("tags")} />
          <Action title={tx("takeoff.counts.shapes", "Shapes ({{n}})", { n: shapes.length })} secondary={tab !== "shapes"} isUrdu={isUrdu} onPress={() => setTab("shapes")} />
        </View>

        {tab === "tags" && tags.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("takeoff.counts.noTags", "No repeated tags found on this sheet.")}</Text>
        ) : null}
        {tab === "tags"
          ? tags.map((tag) => (
              <Pressable key={tag.tag} style={ui.boqItem} onPress={() => void pickTag(tag.tag)}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tag.tag}</Text>
                  <Badge label={String(tag.count)} tone="neutral" />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("takeoff.counts.inDrawing", "{{n}} on this drawing in total", { n: tag.in_drawing })}
                </Text>
              </Pressable>
            ))
          : null}

        {tab === "shapes" && shapes.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("takeoff.counts.noShapes", "No repeated shapes found on this sheet.")}</Text>
        ) : null}
        {tab === "shapes"
          ? shapes.map((shape) => (
              <Pressable key={shape.id} style={ui.boqItem} onPress={() => void pickShape(shape)}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                    {`${shape.shape} · ${formatNumber(shape.a_mm ?? shape.a_pt, 0)} × ${formatNumber(shape.b_mm ?? shape.b_pt, 0)}${shape.a_mm !== null ? " mm" : " pt"}`}
                  </Text>
                  <Badge label={String(shape.count)} tone="neutral" />
                </View>
                {shape.filled ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("takeoff.counts.filled", "{{n}} filled", { n: shape.filled })}</Text>
                ) : null}
              </Pressable>
            ))
          : null}

        {picked ? (
          <View style={ui.card}>
            <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${picked.title} × ${picked.count}`}</Text>
            {picked.note ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{picked.note}</Text> : null}
            {canEdit ? (
              <>
                <Field label={tx("takeoff.counts.workItem", "Work item code")} value={workItem} onChangeText={setWorkItem} isUrdu={isUrdu} />
                <Field label={tx("takeoff.counts.label", "Name")} value={label} onChangeText={setLabel} isUrdu={isUrdu} />
                <Field label={tx("takeoff.counts.grade", "Material grade (optional)")} value={grade} onChangeText={setGrade} isUrdu={isUrdu} />
                <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("takeoff.counts.reconMode", "If the model already has this work item")}</Text>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  {RECON_MODES.map((mode) => (
                    <Action key={mode} title={reconLabel(tx, mode)} secondary={recon !== mode} isUrdu={isUrdu} onPress={() => setRecon(mode)} />
                  ))}
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{reconHint(tx, recon)}</Text>
                {preview ? (
                  <Text style={[preview.ok ? ui.notice : ui.error, isUrdu && ui.rtlText]}>
                    {preview.ok
                      ? `${formatNumber(preview.quantity ?? "0")} ${preview.unit ?? ""}`.trim()
                      : preview.error?.message ?? tx("takeoff.counts.previewFailure", "Could not work out the count.")}
                  </Text>
                ) : null}
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  <Action title={tx("takeoff.preview", "Preview")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void runPreview()} />
                  <Action title={tx("takeoff.counts.save", "Save as draft")} disabled={busy} isUrdu={isUrdu} onPress={() => void save()} />
                </View>
              </>
            ) : null}
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
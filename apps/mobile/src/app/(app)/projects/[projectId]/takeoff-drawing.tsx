import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Switch, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {bulkConfirmMeasurements, extractDrawingItems, getTakeoffOverview, prepareDrawingSheets, syncTakeoffSheets,
} from "../../../../api/takeoff";
import type { TakeoffOverview } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { prepTone, sheetTitle } from "../../../../features/drawingsBoq/takeoffText";
import { Action, Badge, COLORS, InfoRow, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function TakeoffDrawingScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; drawingId?: string }>();
  const projectId = first(params.projectId) ?? "";
  const drawingId = first(params.drawingId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [overview, setOverview] = useState<TakeoffOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [details, setDetails] = useState<string[]>([]);
  const [autoScale, setAutoScale] = useState(true);

  const canEdit = hasPerm(permissions, PERM.BOQ_UPDATE);

  const load = useCallback(async () => {
    if (!drawingId) {
      setLoading(false);
      return;
    }
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));
      setOverview(await getTakeoffOverview(drawingId));
      setError("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.drawing.loadFailure", "Could not load this drawing.")));
    } finally {
      setLoading(false);
    }

  }, [drawingId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function run(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    setDetails([]);
    try {
      await work();
    } catch (err) {
      setError(describeError(err, tx("takeoff.drawing.actionFailure", "That did not work.")));
    } finally {
      setProgress("");
      setBusy(false);
    }
  }

  const openSheets = () =>
    run(async () => {
      if (!drawingId) return;
      setOverview(await syncTakeoffSheets(drawingId));
      setNotice(tx("takeoff.drawing.sheetsOpened", "Sheets are open."));
    });

  const prepareAll = () =>
    run(async () => {
      if (!drawingId) return;
      let remaining = 1;
      let pass = 0;
      let failed: string[] = [];
      while (remaining > 0 && pass < 12) {
        pass += 1;
        setProgress(tx("takeoff.drawing.preparing", "Reading sheets… (round {{n}})", { n: pass }));
        const result = await prepareDrawingSheets(drawingId, { budget_seconds: 45 });
        remaining = result.remaining;
        failed = [...failed, ...result.failed.map((f) => f.message ?? f.code ?? "")];
        if (result.prepared.length === 0) break;
      }
      setOverview(await getTakeoffOverview(drawingId));
      setDetails(failed.filter(Boolean));
      setNotice(
        remaining > 0
          ? tx("takeoff.drawing.prepareMore", "{{n}} sheets still need reading. Tap again to continue.", { n: remaining })
          : tx("takeoff.drawing.prepareDone", "All sheets are read."),
      );
    });

  const findItems = () =>
    run(async () => {
      if (!drawingId) return;
      const result = await extractDrawingItems(drawingId, { auto_calibrate: autoScale });
      setOverview(await getTakeoffOverview(drawingId));
      setDetails(result.skipped.map((s) => `${tx("takeoff.page", "Page {{n}}", { n: s.page_no })}: ${s.message}`));
      setNotice(
        tx("takeoff.drawing.found", "{{done}} sheets read for items, {{skipped}} skipped.", {
          done: result.done.length,
          skipped: result.skipped.length,
        }),
      );
    });

  const confirmDrafts = () =>
    run(async () => {
      if (!overview || !drawingId) return;
      const ids = overview.measurements.filter((m) => m.status === "DRAFT").map((m) => m.id);
      if (ids.length === 0) {
        setNotice(tx("takeoff.drawing.noDrafts", "There are no draft measurements."));
        return;
      }
      const result = await bulkConfirmMeasurements(ids);
      setOverview(await getTakeoffOverview(drawingId));
      setDetails(result.failed.map((f) => f.message ?? f.code ?? "").filter(Boolean));
      setNotice(
        tx("takeoff.drawing.confirmed", "{{ok}} confirmed, {{failed}} could not be confirmed.", {
          ok: result.confirmed.length,
          failed: result.failed.length,
        }),
      );
    });

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const s = overview?.summary;

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("takeoff.drawing.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("takeoff.drawing.title", "PDF drawing")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}
        {details.map((line, index) => (
          <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{line}</Text>
        ))}
        {busy ? (
          <View style={ui.busy}>
            <ActivityIndicator color={COLORS.navy} />
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>{progress || tx("takeoff.drawing.working", "Working…")}</Text>
          </View>
        ) : null}

        {s ? (
          <View style={ui.summaryBox}>
            <InfoRow label={tx("takeoff.sheets", "Sheets")} value={String(s.sheets)} isUrdu={isUrdu} />
            <InfoRow label={tx("takeoff.calibrated", "Scale set")} value={String(s.calibrated_sheets)} isUrdu={isUrdu} />
            <InfoRow label={tx("takeoff.measurements", "Measurements")} value={String(s.measurements)} isUrdu={isUrdu} />
            <InfoRow label={tx("takeoff.draft", "Draft measurements")} value={String(s.draft)} isUrdu={isUrdu} />
            <InfoRow label={tx("takeoff.confirmed", "Confirmed")} value={String(s.confirmed)} isUrdu={isUrdu} />
          </View>
        ) : null}

        {canEdit ? (
          <>
            <Action
              title={overview && overview.sheets.length > 0 ? tx("takeoff.drawing.refreshSheets", "Refresh sheets") : tx("takeoff.drawing.openSheets", "Open sheets")}
              secondary={!!overview && overview.sheets.length > 0}
              disabled={busy}
              isUrdu={isUrdu}
              onPress={() => void openSheets()}
            />
            <Action
              title={tx("takeoff.drawing.prepareAll", "Read all sheets")}
              secondary
              disabled={busy || !overview || overview.sheets.length === 0}
              isUrdu={isUrdu}
              onPress={() => void prepareAll()}
            />
            <View style={[ui.heading, isUrdu && ui.rtlRow]}>
              <View style={ui.headerCopy}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                  {tx("takeoff.drawing.autoScale", "Set the scale automatically")}
                </Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx(
                    "takeoff.drawing.autoScaleHint",
                    "Only used when a sheet has no scale and the printed scale agrees with its printed dimensions.",
                  )}
                </Text>
              </View>
              <Switch value={autoScale} onValueChange={setAutoScale} />
            </View>
            <Action
              title={tx("takeoff.drawing.findItems", "Find items automatically")}
              secondary
              disabled={busy || !overview || overview.sheets.length === 0}
              isUrdu={isUrdu}
              onPress={() => void findItems()}
            />
            <Action
              title={tx("takeoff.drawing.reviewFound", "Review found items")}
              secondary
              isUrdu={isUrdu}
              onPress={() =>
                router.push({ pathname: "/projects/[projectId]/takeoff-found", params: { projectId, drawingId: drawingId ?? "" } })
              }
            />
            <Action
              title={tx("takeoff.drawing.confirmAll", "Confirm all drafts")}
              secondary
              disabled={busy || !s || s.draft === 0}
              isUrdu={isUrdu}
              onPress={() => void confirmDrafts()}
            />
          </>
        ) : (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("takeoff.noPermission", "You can view the takeoff but not change it.")}
          </Text>
        )}

        <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.drawing.sheets", "Sheets")}</Text>
        {overview && overview.sheets.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("takeoff.drawing.noSheets", "No sheets yet. Tap Open sheets to create one for each page of the PDF.")}
          </Text>
        ) : null}
        {overview?.sheets.map((sheet) => {
          const calibrated = overview.calibrations.some((c) => c.sheet_id === sheet.id && c.is_default && c.usable);
          const count = overview.measurements.filter((m) => m.sheet_id === sheet.id).length;
          return (
            <Pressable
              key={sheet.id}
              style={ui.boqItem}
              onPress={() =>
                router.push({
                  pathname: "/projects/[projectId]/takeoff-sheet",
                  params: { projectId, drawingId: drawingId ?? "", sheetId: sheet.id },
                })
              }
            >
              <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{sheetTitle(tx, sheet)}</Text>
                <Badge label={sheet.prep_status} tone={prepTone(sheet.prep_status)} />
              </View>
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {[
                  sheet.content_kind,
                  calibrated ? tx("takeoff.scaleSet", "scale set") : tx("takeoff.scaleMissing", "no scale"),
                  tx("takeoff.measurementCount", "{{count}} measurements", { count }),
                  sheet.scale_text,
                ].filter(Boolean).join(" · ")}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
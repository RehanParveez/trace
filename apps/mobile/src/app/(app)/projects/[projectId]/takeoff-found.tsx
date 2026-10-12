import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { acceptCandidates, extractSheetItems, listDrawingCandidates, rejectCandidates, restoreCandidates } from "../../../../api/takeoff";
import type { CandidateList, TakeoffCandidate } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { toNumber } from "../../../../features/drawingsBoq/takeoffText";
import { Action, Badge, COLORS, Field, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

const CATEGORIES = ["ALL", "COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW", "WALL", "ROOM"];
const DECISIONS = ["NEW", "ACCEPTED", "REJECTED"];
const OVERRIDE_CATEGORIES = ["COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW", "WALL", "ROOM"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function TakeoffFoundScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; drawingId?: string; sheetId?: string }>();
  const drawingId = first(params.drawingId) ?? "";
  const sheetId = first(params.sheetId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [lists, setLists] = useState<CandidateList[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [details, setDetails] = useState<string[]>([]);
  const [category, setCategory] = useState("ALL");
  const [decision, setDecision] = useState("NEW");
  const [selected, setSelected] = useState<string[]>([]);
  const [wallHeight, setWallHeight] = useState("");
  const [columnHeight, setColumnHeight] = useState("");
  const [footingDepth, setFootingDepth] = useState("");
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  const canEdit = hasPerm(permissions, PERM.BOQ_UPDATE);

  const load = useCallback(async () => {
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));
      const result = await listDrawingCandidates(drawingId);
      setLists(sheetId ? result.sheets.filter((s) => s.sheet_id === sheetId) : result.sheets);
      setSelected([]);
      setError("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.found.loadFailure", "Could not load the found items.")));
    } finally {
      setLoading(false);
    }
    
  }, [drawingId, sheetId]);

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
      await load();
    } catch (err) {
      setError(describeError(err, tx("takeoff.found.actionFailure", "That did not work.")));
    } finally {
      setBusy(false);
    }
  }

  const extractNow = () =>
    run(async () => {
      if (!sheetId) return;
      const r = await extractSheetItems(sheetId, { auto_calibrate: true });
      setNotice(
        tx("takeoff.found.extracted", "{{a}} new, {{u}} updated, {{r}} removed.", { a: r.added, u: r.updated, r: r.removed }),
      );
    });

  const accept = () =>
    run(async () => {
      const work_items: Record<string, string> = {};
      for (const [cat, code] of Object.entries(overrides)) if (code.trim()) work_items[cat] = code.trim();
      const r = await acceptCandidates({
        ids: selected,
        wall_height_mm: toNumber(wallHeight),
        column_height_mm: toNumber(columnHeight),
        footing_depth_mm: toNumber(footingDepth),
        work_items,
      });
      setDetails(r.failed.map((f) => `${f.code}: ${f.message}`));
      setNotice(tx("takeoff.found.accepted", "{{ok}} accepted as draft measurements, {{bad}} could not be accepted.", { ok: r.accepted.length, bad: r.failed.length }));
    });

  const decide = (kind: "reject" | "restore") =>
    run(async () => {
      const r = kind === "reject" ? await rejectCandidates(selected) : await restoreCandidates(selected);
      setDetails(r.failed.map((f) => `${f.code}: ${f.message}`));
      setNotice(tx("takeoff.found.changed", "{{n}} updated.", { n: r.changed.length }));
    });

  const toggle = (id: string) => setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  const visible = (list: CandidateList): TakeoffCandidate[] =>
    list.candidates.filter((c) => (category === "ALL" || c.category === category) && c.decision === decision);

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const allVisible = lists.flatMap(visible);

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("takeoff.found.title", "Found items")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}
        {details.map((line, index) => (
          <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{line}</Text>
        ))}
        {busy ? <ActivityIndicator color={COLORS.navy} /> : null}

        {canEdit && sheetId ? (
          <Action title={tx("takeoff.found.find", "Find items on this sheet")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void extractNow()} />
        ) : null}

        {lists.map((list) => {
          const x = list.extraction;
          return (
            <View key={list.sheet_id}>
              {x.stale ? (
                <Text style={[ui.error, isUrdu && ui.rtlText]}>
                  {tx("takeoff.found.stale", "A sheet changed since items were found. Find them again.")}
                </Text>
              ) : null}
              {x.scale_unverified ? (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("takeoff.found.scaleUnverified", "The scale on a sheet has not been checked, so sizes may be off.")}
                </Text>
              ) : null}
              {x.notes.map((n, i) => (
                <Text key={i} style={[ui.muted, isUrdu && ui.rtlText]}>{n.message}</Text>
              ))}
              {x.unmapped_tags.length > 0 ? (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("takeoff.found.unmapped", "Tags with no matching item: {{tags}}", {
                    tags: x.unmapped_tags.map((u) => `${u.tag} (${u.count})`).join(", "),
                  })}
                </Text>
              ) : null}
            </View>
          );
        })}

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {CATEGORIES.map((c) => (
            <Action key={c} title={c} secondary={category !== c} isUrdu={isUrdu} onPress={() => setCategory(c)} />
          ))}
        </View>
        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {DECISIONS.map((d) => (
            <Action key={d} title={d} secondary={decision !== d} isUrdu={isUrdu} onPress={() => { setDecision(d); setSelected([]); }} />
          ))}
        </View>

        {canEdit && decision === "NEW" ? (
          <View style={ui.card}>
            <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("takeoff.found.sizes", "Sizes missing from the drawing (mm)")}</Text>
            <Field label={tx("takeoff.found.wallHeight", "Wall height")} value={wallHeight} onChangeText={setWallHeight} keyboardType="decimal-pad" isUrdu={isUrdu} />
            <Field label={tx("takeoff.found.columnHeight", "Column height")} value={columnHeight} onChangeText={setColumnHeight} keyboardType="decimal-pad" isUrdu={isUrdu} />
            <Field label={tx("takeoff.found.footingDepth", "Footing depth")} value={footingDepth} onChangeText={setFootingDepth} keyboardType="decimal-pad" isUrdu={isUrdu} />
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("takeoff.found.overrideHint", "Work item for a whole category (optional). Leave empty to use the suggested one.")}
            </Text>
            {OVERRIDE_CATEGORIES.map((cat) => (
              <Field
                key={cat}
                label={cat}
                value={overrides[cat] ?? ""}
                onChangeText={(v) => setOverrides((cur) => ({ ...cur, [cat]: v }))}
                isUrdu={isUrdu}
              />
            ))}
          </View>
        ) : null}

        {canEdit && allVisible.length > 0 ? (
          <View style={[ui.row, isUrdu && ui.rtlRow]}>
            <Action
              title={tx("takeoff.found.selectAll", "Select all")}
              secondary
              isUrdu={isUrdu}
              onPress={() => setSelected(allVisible.map((c) => c.id))}
            />
            <Action title={tx("takeoff.found.clear", "Clear")} secondary isUrdu={isUrdu} onPress={() => setSelected([])} />
            {decision === "NEW" ? (
              <>
                <Action title={tx("takeoff.found.accept", "Accept ({{n}})", { n: selected.length })} disabled={busy || selected.length === 0} isUrdu={isUrdu} onPress={() => void accept()} />
                <Action title={tx("takeoff.found.reject", "Reject")} secondary disabled={busy || selected.length === 0} isUrdu={isUrdu} onPress={() => void decide("reject")} />
              </>
            ) : null}
            {decision === "REJECTED" ? (
              <Action title={tx("takeoff.found.restore", "Restore")} disabled={busy || selected.length === 0} isUrdu={isUrdu} onPress={() => void decide("restore")} />
            ) : null}
          </View>
        ) : null}

        {allVisible.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("takeoff.found.none", "Nothing here.")}</Text>
        ) : null}
        {allVisible.map((c) => {
          const on = selected.includes(c.id);
          return (
            <Pressable key={c.id} style={[ui.boqItem, on && { borderColor: COLORS.navy, borderWidth: 2 }]} onPress={() => canEdit && toggle(c.id)}>
              <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${c.category} · ${c.label}`}</Text>
                <Badge label={c.status} tone={c.status === "VALID" ? "good" : c.status === "WARNING" ? "warn" : "bad"} />
              </View>
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {[c.tag, `× ${c.count}`, c.kind, c.suggested_work_item, `${tx("takeoff.found.confidence", "confidence")} ${formatNumber(c.confidence, 2)}`].filter(Boolean).join(" · ")}
              </Text>
              {c.missing.length > 0 ? (
                <Text style={[ui.error, isUrdu && ui.rtlText]}>
                  {tx("takeoff.found.missing", "Missing: {{list}}", { list: c.missing.join(", ") })}
                </Text>
              ) : null}
              {c.notes.map((n, i) => (
                <Text key={i} style={[ui.muted, isUrdu && ui.rtlText]}>{n.message}</Text>
              ))}
            </Pressable>
          );
        })}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
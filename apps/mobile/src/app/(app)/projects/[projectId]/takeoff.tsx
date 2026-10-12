import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listProjectDrawings } from "../../../../api/drawingsBoq";
import { getProjectTakeoffDrawings } from "../../../../api/takeoff";
import type { Drawing, ProjectTakeoffDrawing } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { Action, Badge, COLORS, InfoRow, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function TakeoffProjectScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [summary, setSummary] = useState<Record<string, ProjectTakeoffDrawing>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      const list = await listProjectDrawings(projectId);
      setDrawings(list.filter((d) => d.format === "PDF"));
      try {
        
        const result = await getProjectTakeoffDrawings(projectId);
        setSummary(Object.fromEntries(result.drawings.map((d) => [d.drawing_id, d])));
      } catch {
        setSummary({});
      }
      setError("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.loadFailure", "Could not load the PDF drawings.")));
    } finally {
      setLoading(false);
    }
    
  }, [projectId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("takeoff.back", "Back to drawings & BOQ")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("takeoff.title", "PDF takeoff")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        <Text style={[ui.muted, isUrdu && ui.rtlText]}>
          {tx(
            "takeoff.help",
            "Measure quantities from PDF drawings: set the scale of each sheet, find or count items, then confirm the measurements. Confirmed measurements are included the next time you calculate.",
          )}
        </Text>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        <Action
          title={tx("takeoff.reconciliation", "Compare with the model")}
          secondary
          isUrdu={isUrdu}
          onPress={() =>
            router.push({ pathname: "/projects/[projectId]/takeoff-recon", params: { projectId: projectId ?? "" } })
          }
        />

        {drawings.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("takeoff.none", "No PDF drawings in this project. Upload a PDF on Drawings & BOQ first.")}
          </Text>
        ) : null}

        {drawings.map((drawing) => {
          const s = summary[drawing.id];
          return (
            <View key={drawing.id} style={ui.card}>
              <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{drawing.original_filename}</Text>
                <Badge
                  label={drawing.is_current_revision ? tx("takeoff.current", "current") : tx("takeoff.older", "older")}
                  tone={drawing.is_current_revision ? "good" : "neutral"}
                />
              </View>
              {drawing.revision_label ? (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{drawing.revision_label}</Text>
              ) : null}
              {s ? (
                <View style={ui.summaryBox}>
                  <InfoRow label={tx("takeoff.sheets", "Sheets")} value={String(s.sheets)} isUrdu={isUrdu} />
                  <InfoRow label={tx("takeoff.prepared", "Read")} value={String(s.prepared_sheets)} isUrdu={isUrdu} />
                  <InfoRow label={tx("takeoff.calibrated", "Scale set")} value={String(s.calibrated_sheets)} isUrdu={isUrdu} />
                  <InfoRow label={tx("takeoff.draft", "Draft measurements")} value={String(s.draft)} isUrdu={isUrdu} />
                  <InfoRow label={tx("takeoff.confirmed", "Confirmed")} value={String(s.confirmed)} isUrdu={isUrdu} />
                </View>
              ) : null}
              <Action
                title={tx("takeoff.open", "Open takeoff")}
                isUrdu={isUrdu}
                onPress={() =>
                  router.push({
                    pathname: "/projects/[projectId]/takeoff-drawing",
                    params: { projectId: projectId ?? "", drawingId: drawing.id },
                  })
                }
              />
            </View>
          );
        })}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
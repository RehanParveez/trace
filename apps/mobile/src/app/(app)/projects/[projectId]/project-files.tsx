import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listProjectDrawings } from "../../../../api/drawingsBoq";
import { downloadDrawingFile, getBoqItemCounts } from "../../../../api/runData";
import type { Drawing } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { shareExportFile } from "../../../../features/drawingsBoq/exportFile";
import { Action, Badge, COLORS, InfoRow, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function ProjectFilesScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [itemCount, setItemCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!projectId) {
      setError(tx("files.projectMissing", "Project not found."));
      setLoading(false);
      return;
    }
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      const [list, counts] = await Promise.all([listProjectDrawings(projectId), getBoqItemCounts()]);
      setDrawings(list);
      setItemCount(counts.find((c) => c.project_id === projectId)?.latest_boq_item_count ?? 0);
      setError("");
    } catch (err) {
      setError(describeError(err, tx("files.loadFailure", "Could not load the files.")));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function handleDownload(drawing: Drawing) {
    setBusyId(drawing.id);
    setError("");
    try {
      const file = await downloadDrawingFile(drawing.id, drawing.original_filename);
      await shareExportFile(file);
    } catch (err) {
      setError(describeError(err, tx("files.downloadFailure", "Could not download the file.")));
    } finally {
      setBusyId("");
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
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("files.back", "Back to drawings & BOQ")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("files.title", "Files & counts")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        <View style={ui.summaryBox}>
          <InfoRow label={tx("files.itemCount", "Items in the latest BOQ")} value={String(itemCount ?? 0)} isUrdu={isUrdu} />
          <InfoRow label={tx("files.drawingCount", "Drawings")} value={String(drawings.length)} isUrdu={isUrdu} />
        </View>

        <Text style={[ui.muted, isUrdu && ui.rtlText]}>
          {tx("files.help", "Download or share the original drawing files. Large IFC files can take a while on a phone connection.")}
        </Text>

        {drawings.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("files.none", "No drawings uploaded yet.")}</Text> : null}

        {drawings.map((drawing) => (
          <View key={drawing.id} style={ui.card}>
            <View style={[ui.heading, isUrdu && ui.rtlRow]}>
              <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{drawing.original_filename}</Text>
              <Badge label={drawing.format} tone="neutral" />
            </View>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {[drawing.status, drawing.is_current_revision ? tx("files.current", "current revision") : tx("files.older", "older revision")].join(" · ")}
            </Text>
            <Action
              title={busyId === drawing.id ? tx("files.downloading", "Downloading…") : tx("files.download", "Download / share")}
              secondary
              disabled={busyId !== ""}
              isUrdu={isUrdu}
              onPress={() => void handleDownload(drawing)}
            />
          </View>
        ))}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
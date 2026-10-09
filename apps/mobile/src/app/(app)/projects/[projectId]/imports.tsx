import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import * as DocumentPicker from "expo-document-picker";
import { restoreSession } from "../../../../api/client";
import { listProjectDrawings } from "../../../../api/drawingsBoq";
import {createManualScheduleImport, importRebarFile, importRebarFromPdf, importScheduleFile, importScheduleFromPdf, listRebarImports, listScheduleImports,
} from "../../../../api/imports";
import type { Drawing, ScheduleImport, ScheduleKind } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, ui } from "../../../../features/drawingsBoq/ui";

const KINDS: ScheduleKind[] = ["FINISH", "DOOR", "WINDOW", "FIXTURE", "GENERAL"];
const FILE_TYPES = [".csv", ".txt", ".xlsx"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function statusTone(status: string): "neutral" | "good" | "warn" | "bad" {
  if (status === "CONFIRMED") return "good";
  if (status === "PENDING_REVIEW") return "warn";
  if (status === "REJECTED") return "bad";
  return "neutral";
}

export default function ImportsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [tab, setTab] = useState<"schedule" | "rebar">("schedule");
  const [kind, setKind] = useState<ScheduleKind>("FINISH");
  const [imports, setImports] = useState<ScheduleImport[]>([]);
  const [pdfs, setPdfs] = useState<Drawing[]>([]);
  const [pickPdf, setPickPdf] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const canImport = hasPerm(permissions, PERM.SCHEDULE_IMPORT);

  const load = useCallback(
    async (which: "schedule" | "rebar") => {
      if (!projectId) {
        setError(tx("imports.projectMissing", "Project not found."));
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
        const [list, drawings] = await Promise.all([
          which === "schedule" ? listScheduleImports(projectId) : listRebarImports(projectId),
          listProjectDrawings(projectId),
        ]);
        setImports(list);
        setPdfs(drawings.filter((d) => d.format === "PDF" && d.is_current_revision));
      } catch (err) {
        setError(describeError(err, tx("imports.loadFailure", "Could not load imports.")));
      } finally {
        setLoading(false);
      }
    },
    [projectId],
  );

  useFocusEffect(
    useCallback(() => {
      void load(tab);
    }, [load, tab]),
  );

  function openImport(importId: string) {
    if (!projectId) return;
    router.push({
      pathname: "/projects/[projectId]/import-detail",
      params: { projectId, importId, kind: tab },
    });
  }

  async function create(action: () => Promise<string>) {
    setBusy(true);
    setError("");
    try {
      openImport(await action());
    } catch (err) {
      setError(describeError(err, tx("imports.createFailure", "Could not create the import.")));
    } finally {
      setBusy(false);
    }
  }

  async function handleFile() {
    if (!projectId) return;
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "*/*",
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;

      const file = result.assets[0];
      const lower = file.name.toLowerCase();
      if (!FILE_TYPES.some((suffix) => lower.endsWith(suffix))) {
        setError(tx("imports.fileType", "Choose a .csv or .xlsx file (5 MB maximum)."));
        return;
      }
      const upload = { uri: file.uri, name: file.name, mimeType: file.mimeType };
      await create(async () =>
        tab === "schedule"
          ? (await importScheduleFile(projectId, upload, kind)).id
          : (await importRebarFile(projectId, upload)).schedule_import_id,
      );
    } catch (err) {
      setError(describeError(err, tx("imports.createFailure", "Could not create the import.")));
    }
  }

  async function handleFromPdf(drawing: Drawing) {
    if (!projectId) return;
    setPickPdf(false);
    await create(async () =>
      tab === "schedule"
        ? (await importScheduleFromPdf(projectId, drawing.id, kind)).id
        : (await importRebarFromPdf(projectId, drawing.id)).schedule_import_id,
    );
  }

  async function handleManual() {
    if (!projectId) return;
    await create(async () => (await createManualScheduleImport(projectId, kind)).id);
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
              <Text style={[ui.link, isUrdu && ui.rtlText]}>
                {tx("imports.back", "Back to drawings & BOQ")}
              </Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>
              {tx("imports.title", "Schedules & rebar")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          <Action
            title={tx("imports.tabSchedules", "Schedules")}
            secondary={tab !== "schedule"}
            isUrdu={isUrdu}
            onPress={() => {
              setTab("schedule");
              setImports([]);
              setPickPdf(false);
            }}
          />
          <Action
            title={tx("imports.tabRebar", "Rebar (BBS)")}
            secondary={tab !== "rebar"}
            isUrdu={isUrdu}
            onPress={() => {
              setTab("rebar");
              setImports([]);
              setPickPdf(false);
            }}
          />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {canImport ? (
          <View style={ui.card}>
            {tab === "schedule" ? (
              <>
                <Text style={[ui.label, isUrdu && ui.rtlText]}>
                  {tx("imports.kind", "Schedule type")}
                </Text>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  {KINDS.map((value) => (
                    <Action
                      key={value}
                      title={tx(`imports.kind.${value.toLowerCase()}`, value)}
                      secondary={kind !== value}
                      isUrdu={isUrdu}
                      onPress={() => setKind(value)}
                    />
                  ))}
                </View>
              </>
            ) : null}

            <Action
              title={tx("imports.fromFile", "Import from CSV / XLSX")}
              disabled={busy}
              isUrdu={isUrdu}
              onPress={() => void handleFile()}
            />
            <Action
              title={tx("imports.fromPdf", "Import from a PDF drawing")}
              secondary
              disabled={busy}
              isUrdu={isUrdu}
              onPress={() => setPickPdf((open) => !open)}
            />
            {tab === "schedule" ? (
              <Action
                title={tx("imports.manual", "Start an empty manual schedule")}
                secondary
                disabled={busy}
                isUrdu={isUrdu}
                onPress={() => void handleManual()}
              />
            ) : null}

            {pickPdf ? (
              pdfs.length === 0 ? (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("imports.noPdfs", "No PDF drawings in this project yet.")}
                </Text>
              ) : (
                pdfs.map((drawing) => (
                  <Action
                    key={drawing.id}
                    title={drawing.original_filename}
                    secondary
                    disabled={busy}
                    isUrdu={isUrdu}
                    onPress={() => void handleFromPdf(drawing)}
                  />
                ))
              )
            ) : null}

            {busy ? (
              <View style={ui.busy}>
                <ActivityIndicator color={COLORS.navy} />
              </View>
            ) : null}
          </View>
        ) : null}

        <Text style={[ui.section, isUrdu && ui.rtlText]}>
          {tx("imports.existing", "Existing imports")}
        </Text>
        {imports.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("imports.none", "Nothing imported yet.")}
          </Text>
        ) : null}

        {imports.map((item) => (
          <Pressable
            key={item.id}
            style={ui.card}
            onPress={() => openImport(item.id)}
            accessibilityRole="button"
          >
            <View style={[ui.heading, isUrdu && ui.rtlRow]}>
              <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                {item.file_name ?? `${item.schedule_kind} · ${item.source}`}
              </Text>
              <Badge label={item.status.replaceAll("_", " ")} tone={statusTone(item.status)} />
            </View>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("imports.counts", "{{kind}} · {{rows}} rows · {{confirmed}} confirmed", {
                kind: item.schedule_kind,
                rows: item.row_count,
                confirmed: item.confirmed_count,
              })}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
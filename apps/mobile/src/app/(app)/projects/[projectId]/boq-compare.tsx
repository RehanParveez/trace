import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listProjectBOQVersions } from "../../../../api/drawingsBoq";
import { getVersionDiff } from "../../../../api/boqExtras";
import type { BOQVersion, DiffLine, DiffResult } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import {Action, Badge, COLORS, InfoRow, formatMoney, formatNumber, ui,
} from "../../../../features/drawingsBoq/ui";

const SHOW_STEP = 30;

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function tone(status: string): "neutral" | "good" | "warn" | "bad" {
  if (status === "ADDED") return "good";
  if (status === "REMOVED") return "bad";
  if (status === "CHANGED") return "warn";
  return "neutral";
}

export default function BoqCompareScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; versionId?: string }>();
  const projectId = first(params.projectId);
  const versionId = first(params.versionId);

  const [versions, setVersions] = useState<BOQVersion[]>([]);
  const [baseId, setBaseId] = useState("");
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [filter, setFilter] = useState<"ALL" | "ADDED" | "REMOVED" | "CHANGED">("ALL");
  const [shown, setShown] = useState(SHOW_STEP);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const current = versions.find((v) => v.id === versionId) ?? null;
  const others = versions.filter((v) => v.id !== versionId);

  const load = useCallback(async () => {
    if (!projectId || !versionId) {
      setError(tx("compare.notFound", "BOQ version not found."));
      setLoading(false);
      return;
    }
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setVersions(await listProjectBOQVersions(projectId));
    } catch (err) {
      setError(describeError(err, tx("compare.loadFailure", "Could not load versions.")));
    } finally {
      setLoading(false);
    }
  }, [projectId, versionId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function compareWith(id: string) {
    if (!versionId) return;
    setBaseId(id);
    setBusy(true);
    setError("");
    setDiff(null);
    setShown(SHOW_STEP);
    try {
      setDiff(await getVersionDiff(id, versionId));
    } catch (err) {
      setError(describeError(err, tx("compare.failure", "Could not compare the versions.")));
    } finally {
      setBusy(false);
    }
  }

  const lines: DiffLine[] = (diff?.lines ?? []).filter(
    (line) => filter === "ALL" || line.status === filter,
  );

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={ui.page}>
      <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
        <View style={ui.headerCopy}>
          <Pressable onPress={() => router.back()}>
            <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("compare.back", "Back")}</Text>
          </Pressable>
          <Text style={[ui.title, isUrdu && ui.rtlText]}>
            {tx("compare.title", "Compare versions")}
          </Text>
        </View>
        <LanguageSwitcher />
      </View>

      {current ? (
        <Text style={[ui.muted, isUrdu && ui.rtlText]}>
          {tx("compare.current", "Comparing against: {{label}}", { label: current.label })}
        </Text>
      ) : null}

      {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

      <Text style={[ui.section, isUrdu && ui.rtlText]}>
        {tx("compare.pickBase", "Compare with an earlier version")}
      </Text>
      {others.length === 0 ? (
        <Text style={[ui.muted, isUrdu && ui.rtlText]}>
          {tx("compare.noOthers", "There is no other version in this project.")}
        </Text>
      ) : null}
      <View style={[ui.row, isUrdu && ui.rtlRow]}>
        {others.map((version) => (
          <Action
            key={version.id}
            title={version.label}
            secondary={baseId !== version.id}
            disabled={busy}
            isUrdu={isUrdu}
            onPress={() => void compareWith(version.id)}
          />
        ))}
      </View>

      {busy ? (
        <View style={ui.busy}>
          <ActivityIndicator color={COLORS.navy} />
        </View>
      ) : null}

      {diff ? (
        <>
          <View style={ui.summaryBox}>
            <InfoRow label={tx("compare.added", "Added")} value={String(diff.summary.ADDED)} isUrdu={isUrdu} />
            <InfoRow label={tx("compare.removed", "Removed")} value={String(diff.summary.REMOVED)} isUrdu={isUrdu} />
            <InfoRow label={tx("compare.changed", "Changed")} value={String(diff.summary.CHANGED)} isUrdu={isUrdu} />
            <InfoRow label={tx("compare.unchanged", "Unchanged")} value={String(diff.summary.UNCHANGED)} isUrdu={isUrdu} />
            <InfoRow label={tx("compare.totalA", "Earlier total")} value={formatMoney(diff.summary.total_a, locale, "-")} isUrdu={isUrdu} />
            <InfoRow label={tx("compare.totalB", "This version total")} value={formatMoney(diff.summary.total_b, locale, "-")} isUrdu={isUrdu} />
            <InfoRow
              label={tx("compare.delta", "Difference")}
              value={`${formatMoney(diff.summary.total_delta, locale, "-")}${
                diff.summary.total_delta_pct != null
                  ? ` (${formatNumber(diff.summary.total_delta_pct, 1)}%)`
                  : ""
              }`}
              isUrdu={isUrdu}
            />
          </View>

          <View style={[ui.row, isUrdu && ui.rtlRow]}>
            {(["ALL", "ADDED", "REMOVED", "CHANGED"] as const).map((value) => (
              <Action
                key={value}
                title={tx(`compare.filter.${value.toLowerCase()}`, value)}
                secondary={filter !== value}
                isUrdu={isUrdu}
                onPress={() => {
                  setFilter(value);
                  setShown(SHOW_STEP);
                }}
              />
            ))}
          </View>

          {lines.length === 0 ? (
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("compare.noLines", "No lines in this view.")}
            </Text>
          ) : null}

          {lines.slice(0, shown).map((line) => (
            <View key={line.item_key} style={ui.boqItem}>
              <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                  {line.material_name ?? line.work_item_code ?? line.item_key}
                </Text>
                <Badge label={line.status} tone={tone(line.status)} />
              </View>
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {`${formatNumber(line.quantity_a)} → ${formatNumber(line.quantity_b)} ${
                  line.unit_b ?? line.unit_a ?? ""
                }`}
                {line.quantity_delta_pct != null
                  ? ` (${formatNumber(line.quantity_delta_pct, 1)}%)`
                  : ""}
                {line.unit_changed ? ` · ${tx("compare.unitChanged", "unit changed")}` : ""}
              </Text>
              {line.amount_delta != null ? (
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("compare.amountDelta", "Amount difference: {{amount}}", {
                    amount: formatMoney(line.amount_delta, locale, "-"),
                  })}
                </Text>
              ) : null}
            </View>
          ))}

          {lines.length > shown ? (
            <Action
              title={tx("compare.showMore", "Show more ({{count}} left)", {
                count: lines.length - shown,
              })}
              secondary
              isUrdu={isUrdu}
              onPress={() => setShown((count) => count + SHOW_STEP)}
            />
          ) : null}
        </>
      ) : null}
    </ScrollView>
  );
}
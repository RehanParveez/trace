import { useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getElementImpact } from "../../../../api/runInsight";
import type { ElementImpact } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { COLORS, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function ElementImpactScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; runId?: string; elementId?: string }>();
  const runId = first(params.runId);
  const elementId = first(params.elementId);

  const [impact, setImpact] = useState<ElementImpact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function init() {
      if (!runId || !elementId) {
        setError(tx("insight.impact.missing", "No element was chosen."));
        setLoading(false);
        return;
      }
      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }
        const result = await getElementImpact(runId, elementId);
        if (!cancelled) setImpact(result);
      } catch (err) {
        if (!cancelled) setError(describeError(err, tx("insight.impact.loadFailure", "Could not load the impact.")));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
 
  }, [runId, elementId]);

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const own = impact?.affected_ledger.filter((row) => row.element_id === elementId) ?? [];
  const others = impact?.affected_ledger.filter((row) => row.element_id !== elementId) ?? [];

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("insight.impact.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("insight.impact.title", "Element impact")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        <Text style={[ui.muted, isUrdu && ui.rtlText]}>
          {tx(
            "insight.impact.help",
            "Elements that touch or overlap this one share quantities with it. If this element changes, these are recalculated too.",
          )}
        </Text>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {impact ? (
          <>
            {impact.truncated ? (
              <Text style={[ui.notice, isUrdu && ui.rtlText]}>
                {tx("insight.impact.truncated", "This element touches a very large number of others. Only the first 500 are shown.")}
              </Text>
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>
              {tx("insight.impact.touching", "Touching elements ({{count}})", { count: impact.touching.length })}
            </Text>
            {impact.touching.length === 0 ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("insight.impact.noneTouching", "No other element touches this one.")}</Text>
            ) : null}
            {impact.touching.map((element) => (
              <View key={element.element_id} style={ui.boqItem}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{element.name ?? element.ifc_type ?? element.element_id.slice(0, 8)}</Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[
                    element.ifc_type,
                    element.overlap_mm3 != null ? `${formatNumber(element.overlap_mm3 / 1e9, 4)} m³ ${tx("insight.impact.overlap", "overlap")}` : null,
                    element.ifc_global_id,
                  ].filter(Boolean).join(" · ")}
                </Text>
              </View>
            ))}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>
              {tx("insight.impact.own", "This element's quantities ({{count}})", { count: own.length })}
            </Text>
            {own.map((row) => (
              <View key={row.ledger_id} style={ui.boqItem}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${row.work_item_code} · ${formatNumber(row.quantity_net)} ${row.unit}`}</Text>
              </View>
            ))}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>
              {tx("insight.impact.others", "Quantities of touching elements ({{count}})", { count: others.length })}
            </Text>
            {others.map((row) => (
              <View key={row.ledger_id} style={ui.boqItem}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${row.work_item_code} · ${formatNumber(row.quantity_net)} ${row.unit}`}</Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{row.element_id ? row.element_id.slice(0, 8) : "—"}</Text>
              </View>
            ))}
          </>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
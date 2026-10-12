import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getTakeoffReconciliation } from "../../../../api/takeoff";
import type { TakeoffReconciliation } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { Badge, COLORS, InfoRow, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function TakeoffReconScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [data, setData] = useState<TakeoffReconciliation | null>(null);
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
      setData(await getTakeoffReconciliation(projectId));
      setError("");
    } catch (err) {
      setError(describeError(err, tx("takeoff.recon.loadFailure", "Could not load the comparison. Calculate first.")));
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

  const s = data?.stats;
  const skipped = Object.entries(s?.skipped ?? {});

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page}>
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("takeoff.sheet.back", "Back")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("takeoff.recon.title", "PDF vs model")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {data && !data.run_id ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("takeoff.recon.noRun", "No calculation has used PDF measurements yet. Confirm some measurements, then calculate.")}
          </Text>
        ) : null}

        {s ? (
          <View style={ui.summaryBox}>
            <InfoRow label={tx("takeoff.recon.measurements", "Measurements")} value={String(s.measurements ?? 0)} isUrdu={isUrdu} />
            <InfoRow label={tx("takeoff.recon.counted", "Counted")} value={String(s.counted ?? 0)} isUrdu={isUrdu} />
            <InfoRow label={tx("takeoff.recon.verified", "Verify only")} value={String(s.verified ?? 0)} isUrdu={isUrdu} />
            {s.tolerance_pct ? <InfoRow label={tx("takeoff.recon.tolerance", "Tolerance")} value={`${s.tolerance_pct}%`} isUrdu={isUrdu} /> : null}
          </View>
        ) : null}

        {skipped.length > 0 ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.recon.skipped", "Left out")}</Text>
            {skipped.map(([reason, n]) => (
              <InfoRow key={reason} label={reason} value={String(n)} isUrdu={isUrdu} />
            ))}
          </>
        ) : null}

        {(s?.replaced ?? []).length > 0 ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.recon.replaced", "Model quantity replaced")}</Text>
            {s?.replaced?.map((r, i) => (
              <View key={i} style={ui.boqItem}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{r.work_item_code}</Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("takeoff.recon.replacedDetail", "{{rows}} model rows dropped, model had {{q}}", { rows: r.rows_dropped, q: formatNumber(r.model_quantity) })}
                </Text>
              </View>
            ))}
          </>
        ) : null}

        {(s?.not_counted ?? []).length > 0 ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.recon.notCounted", "Not counted (the model already measures these)")}</Text>
            {s?.not_counted?.map((r, i) => (
              <View key={i} style={ui.boqItem}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{r.work_item_code}</Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("takeoff.recon.notCountedDetail", "{{n}} PDF measurements. Set them to Add to model or Replace model to count them.", { n: r.measurements })}
                </Text>
              </View>
            ))}
          </>
        ) : null}

        {(s?.variances ?? []).length > 0 ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.recon.variances", "Differences from the model")}</Text>
            {s?.variances?.map((v, i) => (
              <View key={i} style={ui.boqItem}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{v.work_item_code}</Text>
                  <Badge label={`${formatNumber(v.variance_pct ?? 0, 1)}%`} tone={v.over_tolerance ? "bad" : "good"} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("takeoff.recon.varianceDetail", "PDF {{p}} · model {{m}} {{u}}", { p: formatNumber(v.pdf_quantity ?? 0), m: formatNumber(v.model_quantity ?? 0), u: v.unit ?? "" })}
                </Text>
              </View>
            ))}
          </>
        ) : null}

        {(data?.measurements ?? []).length > 0 ? (
          <>
            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("takeoff.recon.rows", "Each measurement")}</Text>
            {data?.measurements.map((row) => (
              <View key={row.measurement_id} style={ui.boqItem}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{row.label || row.tag || row.work_item_code || row.measurement_id.slice(0, 8)}</Text>
                  {row.decision ? <Badge label={row.decision} tone={row.decision === "COUNTED" ? "good" : "warn"} /> : null}
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[row.work_item_code, row.quantity ? `${formatNumber(row.quantity)} ${row.unit ?? ""}`.trim() : null, row.reason ?? row.message].filter(Boolean).join(" · ")}
                </Text>
              </View>
            ))}
          </>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
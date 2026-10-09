import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listBOQItems } from "../../../../api/drawingsBoq";
import { getPricingSummary, getRateResolution, listRateBooks, priceVersionWith } from "../../../../api/pricing";
import type { BOQItem, PricingSummary, RateBook, RateExplain } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, InfoRow, formatMoney, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

const PAGE = 10;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function lineText(line: Record<string, unknown>) {
  return Object.entries(line)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`)
    .join(" · ");
}

export default function VersionPricingScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; versionId?: string }>();
  const versionId = first(params.versionId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [summary, setSummary] = useState<PricingSummary | null>(null);
  const [items, setItems] = useState<BOQItem[]>([]);
  const [books, setBooks] = useState<RateBook[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [asOf, setAsOf] = useState("");
  const [overwrite, setOverwrite] = useState(false);
  const [onlyUnpriced, setOnlyUnpriced] = useState(false);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [explainId, setExplainId] = useState("");
  const [explain, setExplain] = useState<RateExplain | null>(null);

  const canPrice = hasPerm(permissions, PERM.BOQ_UPDATE);

  const load = useCallback(async () => {
    if (!versionId) {
      setError(tx("versionPricing.notFound", "BOQ version not found."));
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
      const [sum, list, active] = await Promise.all([
        getPricingSummary(versionId),
        listBOQItems(versionId),
        listRateBooks("ACTIVE"),
      ]);
      setSummary(sum);
      setItems(list);
      setBooks(active);
      setError("");
    } catch (err) {
      setError(describeError(err, tx("versionPricing.loadFailure", "Could not load pricing.")));
    } finally {
      setLoading(false);
    }
  }, [versionId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handlePrice() {
    if (!versionId) return;
    if (asOf.trim() && !DATE.test(asOf.trim())) {
      setError(tx("versionPricing.badDate", "The date must look like 2026-10-31."));
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await priceVersionWith(versionId, { rateBookIds: picked, asOf, overwriteManual: overwrite });
      setNotice(
        tx("versionPricing.priced", "Priced {{priced}} lines ({{changed}} changed), {{unpriced}} without a rate, {{mismatch}} unit mismatches, {{manual}} manual rates kept.", {
          priced: result.priced,
          changed: result.changed,
          unpriced: result.unpriced,
          mismatch: result.unit_mismatch,
          manual: result.skipped_manual,
        }),
      );
      await load();
    } catch (err) {
      setError(describeError(err, tx("versionPricing.priceFailure", "Pricing failed.")));
    } finally {
      setBusy(false);
    }
  }

  async function toggleExplain(itemId: string) {
    if (explainId === itemId) {
      setExplainId("");
      setExplain(null);
      return;
    }
    setExplainId(itemId);
    setExplain(null);
    try {
      setExplain(await getRateResolution(itemId, asOf.trim() && DATE.test(asOf.trim()) ? asOf : undefined));
    } catch (err) {
      setError(describeError(err, tx("versionPricing.explainFailure", "Could not explain this rate.")));
    }
  }

  function toggleBook(bookId: string) {
    setPicked((current) => (current.includes(bookId) ? current.filter((id) => id !== bookId) : [...current, bookId]));
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const shown = onlyUnpriced ? items.filter((item) => item.unit_rate == null) : items;
  const pages = Math.max(1, Math.ceil(shown.length / PAGE));
  const pageItems = shown.slice((page - 1) * PAGE, page * PAGE);
  const bookCodes = Array.isArray(summary?.pricing_meta?.rate_books)
    ? (summary!.pricing_meta.rate_books as { code?: string }[]).map((b) => b.code).filter(Boolean).join(", ")
    : "";

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("versionPricing.back", "Back to pricing")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("versionPricing.title", "Version pricing")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}

        {summary ? (
          <View style={ui.summaryBox}>
            <InfoRow label={tx("versionPricing.total", "Total")} value={formatMoney(summary.total, locale, "-")} isUrdu={isUrdu} />
            <InfoRow label={tx("versionPricing.items", "Lines")} value={String(summary.item_count)} isUrdu={isUrdu} />
            <InfoRow label={tx("versionPricing.unpriced", "Without a rate")} value={String(summary.unpriced_count)} isUrdu={isUrdu} />
            <InfoRow label={tx("versionPricing.pricedAt", "Last priced")} value={summary.priced_at ? new Date(summary.priced_at).toLocaleString(locale) : tx("versionPricing.never", "Never")} isUrdu={isUrdu} />
            {bookCodes ? <InfoRow label={tx("versionPricing.books", "Rate books used")} value={bookCodes} isUrdu={isUrdu} /> : null}
            {Object.entries(summary.by_source).map(([source, count]) => (
              <InfoRow key={source} label={source} value={String(count)} isUrdu={isUrdu} />
            ))}
          </View>
        ) : null}

        {canPrice ? (
          <View style={ui.panel}>
            <Text style={[ui.label, isUrdu && ui.rtlText]}>
              {tx("versionPricing.stack", "Rate books to use (none selected = the standard stack)")}
            </Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {books.map((book) => (
                <Action key={book.id} title={`${book.code} v${book.immutable_version}`} secondary={!picked.includes(book.id)} isUrdu={isUrdu} onPress={() => toggleBook(book.id)} />
              ))}
            </View>
            <Field label={tx("versionPricing.asOf", "Price as of (2026-10-31, optional)")} value={asOf} onChangeText={setAsOf} isUrdu={isUrdu} />
            <Action
              title={overwrite ? tx("versionPricing.overwriteOn", "Overwriting manual rates") : tx("versionPricing.overwriteOff", "Keeping manual rates")}
              secondary={!overwrite}
              isUrdu={isUrdu}
              onPress={() => setOverwrite((value) => !value)}
            />
            <Action title={tx("versionPricing.run", "Price this version")} disabled={busy} isUrdu={isUrdu} onPress={() => void handlePrice()} />
          </View>
        ) : null}

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          <Action title={tx("versionPricing.all", "All lines")} secondary={onlyUnpriced} isUrdu={isUrdu} onPress={() => { setOnlyUnpriced(false); setPage(1); }} />
          <Action title={tx("versionPricing.onlyUnpriced", "Without a rate")} secondary={!onlyUnpriced} isUrdu={isUrdu} onPress={() => { setOnlyUnpriced(true); setPage(1); }} />
        </View>

        {pageItems.map((item) => {
          const amount = item.unit_rate == null ? null : Number(item.quantity) * Number(item.unit_rate);
          return (
            <View key={item.id} style={ui.boqItem}>
              <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{item.material_name}</Text>
                <Badge label={item.rate_source ?? (item.unit_rate == null ? "UNPRICED" : "UNSOURCED")} tone={item.unit_rate == null ? "warn" : "good"} />
              </View>
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {`${formatNumber(item.quantity)} ${item.unit} × ${formatMoney(item.unit_rate, locale, "-")} = ${amount == null ? "-" : formatMoney(amount, locale, "-")}`}
              </Text>
              <Action title={explainId === item.id ? tx("versionPricing.hideWhy", "Hide") : tx("versionPricing.why", "Why this rate?")} secondary isUrdu={isUrdu} onPress={() => void toggleExplain(item.id)} />
              {explainId === item.id ? (
                <View style={ui.panel}>
                  {!explain ? <ActivityIndicator color={COLORS.navy} /> : null}
                  {explain ? (
                    <>
                      <InfoRow label={tx("versionPricing.current", "Current")} value={`${explain.current_source ?? "-"} · ${formatMoney(explain.current_unit_rate, locale, "-")}`} isUrdu={isUrdu} />
                      <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("versionPricing.wouldBe", "A new run would give")}</Text>
                      <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                        {explain.would_resolve_to ? lineText(explain.would_resolve_to) : tx("versionPricing.noRate", "No rate found.")}
                      </Text>
                      {explain.attempts.length > 0 ? (
                        <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("versionPricing.attempts", "What was tried")}</Text>
                      ) : null}
                      {explain.attempts.map((attempt, index) => (
                        <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{lineText(attempt)}</Text>
                      ))}
                      {explain.stack.length > 0 ? (
                        <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("versionPricing.stackUsed", "Rate book stack")}</Text>
                      ) : null}
                      {explain.stack.map((entry, index) => (
                        <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{lineText(entry)}</Text>
                      ))}
                    </>
                  ) : null}
                </View>
              ) : null}
            </View>
          );
        })}

        {shown.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("versionPricing.noLines", "No lines to show.")}</Text> : null}

        {shown.length > PAGE ? (
          <View style={[ui.pagination, isUrdu && ui.rtlRow]}>
            <Action title={tx("drawingsBoq.previous", "Previous")} secondary disabled={page <= 1} isUrdu={isUrdu} onPress={() => setPage((p) => Math.max(1, p - 1))} />
            <Text style={[ui.pageText, isUrdu && ui.rtlText]}>{`${page} / ${pages}`}</Text>
            <Action title={tx("drawingsBoq.next", "Next")} secondary disabled={page >= pages} isUrdu={isUrdu} onPress={() => setPage((p) => Math.min(pages, p + 1))} />
          </View>
        ) : null}

        {busy ? (
          <View style={ui.busy}>
            <ActivityIndicator color={COLORS.navy} />
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
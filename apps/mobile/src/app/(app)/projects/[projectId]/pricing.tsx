import { useCallback, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listProjectBOQVersions } from "../../../../api/drawingsBoq";
import {createRateBook, createRateOverride, listRateBooks, listRateOverrides, revokeRateOverride,
} from "../../../../api/pricing";
import type { BOQVersion, RateBook, RateBookStatus, RateOverride } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { lifecycleTone } from "../../../../features/drawingsBoq/lifecycle";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, formatMoney, ui } from "../../../../features/drawingsBoq/ui";

type Tab = "books" | "overrides" | "versions";

const STATUSES: ("ALL" | RateBookStatus)[] = ["ALL", "DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"];
const DATE = /^\d{4}-\d{2}-\d{2}$/;

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function bookTone(status: string): "neutral" | "good" | "warn" | "bad" {
  if (status === "ACTIVE") return "good";
  if (status === "DRAFT") return "warn";
  return "neutral";
}

const NEW_BOOK = { code: "", name: "", currency: "PKR", edition: "", province: "", city: "" };
const NEW_OVERRIDE = { code: "", unit: "", rate: "", reason: "", from: "", to: "" };

export default function PricingScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>("books");
  const [status, setStatus] = useState<"ALL" | RateBookStatus>("ALL");
  const [includeRevoked, setIncludeRevoked] = useState(false);
  const [books, setBooks] = useState<RateBook[]>([]);
  const [overrides, setOverrides] = useState<RateOverride[]>([]);
  const [versions, setVersions] = useState<BOQVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [bookForm, setBookForm] = useState(NEW_BOOK);
  const [ovForm, setOvForm] = useState(NEW_OVERRIDE);
  const [revokeId, setRevokeId] = useState("");
  const [revokeReason, setRevokeReason] = useState("");

  const canBooks = hasPerm(permissions, PERM.RATEBOOK_MANAGE);
  const canOverride = hasPerm(permissions, PERM.BOQ_ADJUST);

  const load = useCallback(async () => {
    if (!projectId) {
      setError(tx("pricing.projectMissing", "Project not found."));
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

      if (tab === "books") {
        setBooks(await listRateBooks(status === "ALL" ? undefined : status));
      } else if (tab === "overrides") {
        setOverrides(await listRateOverrides(projectId, includeRevoked));
      } else {
        setVersions(await listProjectBOQVersions(projectId));
      }
      setError("");
    } catch (err) {
      setError(describeError(err, tx("pricing.loadFailure", "Could not load pricing data.")));
    } finally {
      setLoading(false);
    }
  }, [projectId, tab, status, includeRevoked]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function openBook(bookId: string) {
    if (!projectId) return;
    router.push({ pathname: "/projects/[projectId]/rate-book", params: { projectId, bookId } });
  }

  async function act(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(describeError(err, tx("pricing.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateBook() {
    if (!bookForm.code.trim() || !bookForm.name.trim()) {
      setError(tx("pricing.needCodeName", "Enter a code and a name."));
      return;
    }
    if (bookForm.currency.trim().length !== 3) {
      setError(tx("pricing.badCurrency", "Currency must be a 3-letter code such as PKR."));
      return;
    }
    await act(async () => {
      const created = await createRateBook({
        code: bookForm.code,
        name: bookForm.name,
        currency: bookForm.currency.toUpperCase(),
        edition: bookForm.edition,
        province: bookForm.province,
        city: bookForm.city,
      });
      setAdding(false);
      setBookForm(NEW_BOOK);
      openBook(created.id);
    });
  }

  async function handleCreateOverride() {
    if (!projectId) return;
    const rate = Number(ovForm.rate);
    if (!ovForm.code.trim() || !ovForm.unit.trim() || !ovForm.reason.trim()) {
      setError(tx("pricing.needOverrideFields", "Enter a work item code, a unit and a reason."));
      return;
    }
    if (!ovForm.rate.trim() || !Number.isFinite(rate) || rate < 0) {
      setError(tx("pricing.badRate", "Enter a rate of zero or more."));
      return;
    }
    for (const date of [ovForm.from, ovForm.to]) {
      if (date.trim() && !DATE.test(date.trim())) {
        setError(tx("pricing.badDate", "Dates must look like 2026-10-31."));
        return;
      }
    }
    await act(async () => {
      await createRateOverride(projectId, {
        work_item_code: ovForm.code.trim(),
        unit: ovForm.unit.trim(),
        rate,
        reason: ovForm.reason.trim(),
        effective_from: ovForm.from.trim() || undefined,
        effective_to: ovForm.to.trim() || undefined,
      });
      setAdding(false);
      setOvForm(NEW_OVERRIDE);
      await load();
    });
  }

  async function handleRevoke(overrideId: string) {
    if (!revokeReason.trim()) {
      setError(tx("pricing.needReason", "Enter a reason."));
      return;
    }
    await act(async () => {
      await revokeRateOverride(overrideId, revokeReason);
      setRevokeId("");
      setRevokeReason("");
      await load();
    });
  }

  function confirmRevoke(overrideId: string) {
    Alert.alert(tx("pricing.revokeTitle", "Revoke this override?"), tx("pricing.revokeBody", "New pricing runs will stop using it."), [
      { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
      { text: tx("pricing.revoke", "Revoke"), style: "destructive", onPress: () => void handleRevoke(overrideId) },
    ]);
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
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("pricing.back", "Back to drawings & BOQ")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("pricing.title", "Pricing")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {(["books", "overrides", "versions"] as Tab[]).map((value) => (
            <Action
              key={value}
              title={tx(`pricing.tab.${value}`, value === "books" ? "Rate books" : value === "overrides" ? "Overrides" : "Versions")}
              secondary={tab !== value}
              isUrdu={isUrdu}
              onPress={() => {
                setTab(value);
                setAdding(false);
                setError("");
              }}
            />
          ))}
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {tab === "books" ? (
          <>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {STATUSES.map((value) => (
                <Action key={value} title={value} secondary={status !== value} isUrdu={isUrdu} onPress={() => setStatus(value)} />
              ))}
            </View>
            {canBooks ? (
              <Action title={tx("pricing.newBook", "New rate book")} secondary={!adding} isUrdu={isUrdu} onPress={() => setAdding((open) => !open)} />
            ) : null}
            {adding ? (
              <View style={ui.panel}>
                <Field label={tx("pricing.code", "Code")} value={bookForm.code} onChangeText={(v) => setBookForm((f) => ({ ...f, code: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.name", "Name")} value={bookForm.name} onChangeText={(v) => setBookForm((f) => ({ ...f, name: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.currency", "Currency")} value={bookForm.currency} onChangeText={(v) => setBookForm((f) => ({ ...f, currency: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.edition", "Edition (optional)")} value={bookForm.edition} onChangeText={(v) => setBookForm((f) => ({ ...f, edition: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.province", "Province (optional)")} value={bookForm.province} onChangeText={(v) => setBookForm((f) => ({ ...f, province: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.city", "City (optional)")} value={bookForm.city} onChangeText={(v) => setBookForm((f) => ({ ...f, city: v }))} isUrdu={isUrdu} />
                <Action title={tx("pricing.createBook", "Create draft")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleCreateBook()} />
              </View>
            ) : null}
            {books.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("pricing.noBooks", "No rate books found.")}</Text> : null}
            {books.map((book) => (
              <Pressable key={book.id} style={ui.card} accessibilityRole="button" onPress={() => openBook(book.id)}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${book.code} v${book.immutable_version} · ${book.name}`}</Text>
                  <Badge label={book.status} tone={bookTone(book.status)} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("pricing.bookCounts", "{{items}} rates · {{analyses}} analyses · {{escalations}} escalations", {
                    items: book.item_count,
                    analyses: book.analysis_count,
                    escalations: book.escalation_count,
                  })}
                  {book.is_system ? ` · ${tx("pricing.system", "System")}` : ""}
                </Text>
              </Pressable>
            ))}
          </>
        ) : null}

        {tab === "overrides" ? (
          <>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("pricing.overrideHelp", "A project override beats every rate book for this project.")}
            </Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Action
                title={includeRevoked ? tx("pricing.hideRevoked", "Hide revoked") : tx("pricing.showRevoked", "Show revoked")}
                secondary
                isUrdu={isUrdu}
                onPress={() => setIncludeRevoked((value) => !value)}
              />
              {canOverride ? (
                <Action title={tx("pricing.newOverride", "New override")} secondary={!adding} isUrdu={isUrdu} onPress={() => setAdding((open) => !open)} />
              ) : null}
            </View>
            {adding ? (
              <View style={ui.panel}>
                <Field label={tx("pricing.workItemCode", "Work item code")} value={ovForm.code} onChangeText={(v) => setOvForm((f) => ({ ...f, code: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.unit", "Unit")} value={ovForm.unit} onChangeText={(v) => setOvForm((f) => ({ ...f, unit: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.rate", "Rate")} value={ovForm.rate} onChangeText={(v) => setOvForm((f) => ({ ...f, rate: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
                <Field label={tx("pricing.reason", "Reason")} value={ovForm.reason} onChangeText={(v) => setOvForm((f) => ({ ...f, reason: v }))} multiline isUrdu={isUrdu} />
                <Field label={tx("pricing.from", "From (2026-10-31, optional)")} value={ovForm.from} onChangeText={(v) => setOvForm((f) => ({ ...f, from: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.to", "To (optional)")} value={ovForm.to} onChangeText={(v) => setOvForm((f) => ({ ...f, to: v }))} isUrdu={isUrdu} />
                <Action title={tx("pricing.saveOverride", "Save override")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleCreateOverride()} />
              </View>
            ) : null}
            {overrides.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("pricing.noOverrides", "No overrides.")}</Text> : null}
            {overrides.map((item) => (
              <View key={item.id} style={ui.card}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${item.work_item_code} · ${formatMoney(item.rate, locale, "-")} / ${item.unit}`}</Text>
                  <Badge label={item.revoked_at ? tx("pricing.revoked", "Revoked") : tx("pricing.active", "Active")} tone={item.revoked_at ? "bad" : "good"} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{item.reason}</Text>
                {item.effective_from || item.effective_to ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>{`${item.effective_from ?? "…"} → ${item.effective_to ?? "…"}`}</Text>
                ) : null}
                {item.revoked_at ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>{item.revoke_reason ?? ""}</Text>
                ) : canOverride ? (
                  revokeId === item.id ? (
                    <>
                      <Field label={tx("pricing.revokeReason", "Reason for revoking")} value={revokeReason} onChangeText={setRevokeReason} isUrdu={isUrdu} />
                      <View style={[ui.row, isUrdu && ui.rtlRow]}>
                        <Action title={tx("pricing.revoke", "Revoke")} disabled={busy} isUrdu={isUrdu} onPress={() => confirmRevoke(item.id)} />
                        <Action title={tx("drawingsBoq.cancel", "Cancel")} secondary isUrdu={isUrdu} onPress={() => { setRevokeId(""); setRevokeReason(""); }} />
                      </View>
                    </>
                  ) : (
                    <Action title={tx("pricing.revoke", "Revoke")} secondary isUrdu={isUrdu} onPress={() => setRevokeId(item.id)} />
                  )
                ) : null}
              </View>
            ))}
          </>
        ) : null}

        {tab === "versions" ? (
          <>
            {versions.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("pricing.noVersions", "No BOQ versions yet.")}</Text> : null}
            {versions.map((version) => (
              <Pressable
                key={version.id}
                style={ui.card}
                accessibilityRole="button"
                onPress={() =>
                  projectId &&
                  router.push({
                    pathname: "/projects/[projectId]/version-pricing",
                    params: { projectId, versionId: version.id },
                  })
                }
              >
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{version.label}</Text>
                  <Badge label={version.lifecycle} tone={lifecycleTone(version.lifecycle)} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {version.priced_at
                    ? tx("pricing.pricedAt", "Priced {{date}}", { date: new Date(version.priced_at).toLocaleDateString(locale) })
                    : tx("pricing.notPriced", "Not priced yet")}
                </Text>
              </Pressable>
            ))}
          </>
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
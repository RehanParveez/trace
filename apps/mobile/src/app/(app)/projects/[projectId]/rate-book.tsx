import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import * as DocumentPicker from "expo-document-picker";
import { restoreSession } from "../../../../api/client";
import {addEscalation, addRateItem, applyAnalysis, archiveRateBook, computeAnalysis, deleteAnalysis, deleteEscalation, deleteRateBook, deleteRateItem, getAnalysisBreakdown, getRateBook,
  importRateItemsCsv, listAnalyses, listEscalations, listRateItems, newRateBookVersion, publishRateBook, updateRateBook, updateRateItem,
} from "../../../../api/pricing";
import { bulkUpsertRates } from "../../../../api/pricingExtras";
import type {AnalysisBreakdown, RateAnalysis, RateBook, RateEscalation, RateItem,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, InfoRow, formatMoney, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

type Tab = "items" | "escalations" | "analyses";
type Panel = "" | "details" | "addItem" | "editItem" | "addEscalation" | "bulk";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function lineText(line: Record<string, unknown>) {
  return Object.entries(line)
    .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`)
    .join(" · ");
}

export default function RateBookScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; bookId?: string }>();
  const bookId = first(params.bookId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [book, setBook] = useState<RateBook | null>(null);
  const [tab, setTab] = useState<Tab>("items");
  const [panel, setPanel] = useState<Panel>("");
  const [items, setItems] = useState<RateItem[]>([]);
  const [escalations, setEscalations] = useState<RateEscalation[]>([]);
  const [analyses, setAnalyses] = useState<RateAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [search, setSearch] = useState("");
  const [details, setDetails] = useState({ name: "", edition: "", province: "", city: "", from: "", to: "" });
  const [itemForm, setItemForm] = useState({ code: "", unit: "", rate: "", description: "", trade: "" });
  const [editId, setEditId] = useState("");
  const [escForm, setEscForm] = useState({ scope: "ALL", from: "", factor: "", note: "" });
  const [bulkText, setBulkText] = useState("");
  const [openAnalysis, setOpenAnalysis] = useState("");
  const [breakdown, setBreakdown] = useState<AnalysisBreakdown | null>(null);

  const canManage = hasPerm(permissions, PERM.RATEBOOK_MANAGE);
  const isDraft = book?.status === "DRAFT";
  const editable = canManage && isDraft && !book?.is_system;

  const loadTab = useCallback(
    async (which: Tab, query = "") => {
      if (!bookId) return;
      if (which === "items") setItems(await listRateItems(bookId, query));
      else if (which === "escalations") setEscalations(await listEscalations(bookId));
      else setAnalyses(await listAnalyses(bookId));
    },
    [bookId],
  );

  const load = useCallback(async () => {
    if (!bookId) {
      setError(tx("rateBook.notFound", "Rate book not found."));
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
      setBook(await getRateBook(bookId));
      await loadTab(tab, search);
      setError("");
    } catch (err) {
      setError(describeError(err, tx("rateBook.loadFailure", "Could not load the rate book.")));
    } finally {
      setLoading(false);
    }
  }, [bookId, tab]);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(action: () => Promise<unknown>, done?: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      if (bookId) setBook(await getRateBook(bookId));
      await loadTab(tab, search);
      if (done) setNotice(done);
    } catch (err) {
      setError(describeError(err, tx("rateBook.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  function ask(title: string, body: string, confirmLabel: string, run: () => void) {
    Alert.alert(title, body, [
      { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
      { text: confirmLabel, style: "destructive", onPress: run },
    ]);
  }

  function openDetails() {
    if (!book) return;
    setDetails({
      name: book.name,
      edition: book.edition ?? "",
      province: book.province ?? "",
      city: book.city ?? "",
      from: book.effective_from ?? "",
      to: book.effective_to ?? "",
    });
    setPanel(panel === "details" ? "" : "details");
  }

  async function saveDetails() {
    for (const date of [details.from, details.to]) {
      if (date.trim() && !DATE.test(date.trim())) {
        setError(tx("rateBook.badDate", "Dates must look like 2026-10-31."));
        return;
      }
    }
    await act(async () => {
      await updateRateBook(bookId!, {
        name: details.name,
        edition: details.edition,
        province: details.province,
        city: details.city,
        effective_from: details.from,
        effective_to: details.to,
      });
      setPanel("");
    }, tx("rateBook.saved", "Saved."));
  }

  async function handlePublish() {
    await act(async () => {
      await publishRateBook(bookId!);
    }, tx("rateBook.published", "Published. This book is now locked."));
  }

  async function handleNewVersion() {
    if (!bookId) return;
    setBusy(true);
    setError("");
    try {
      const draft = await newRateBookVersion(bookId);
      router.replace({
        pathname: "/projects/[projectId]/rate-book",
        params: { projectId: first(params.projectId) ?? "", bookId: draft.id },
      });
    } catch (err) {
      setError(describeError(err, tx("rateBook.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  function handleDeleteBook() {
    ask(tx("rateBook.deleteTitle", "Delete this draft?"), tx("rateBook.deleteBody", "Its rates, escalations and analyses are deleted too."), tx("rateBook.delete", "Delete"), () => {
      setBusy(true);
      deleteRateBook(bookId!)
        .then(() => router.back())
        .catch((err) => setError(describeError(err, tx("rateBook.actionFailure", "Action failed."))))
        .finally(() => setBusy(false));
    });
  }

  async function handleAddItem() {
    const rate = Number(itemForm.rate);
    if (!itemForm.code.trim() || !itemForm.unit.trim()) {
      setError(tx("rateBook.needCodeUnit", "Enter a work item code and a unit."));
      return;
    }
    if (!itemForm.rate.trim() || !Number.isFinite(rate) || rate < 0) {
      setError(tx("rateBook.badRate", "Enter a rate of zero or more."));
      return;
    }
    await act(async () => {
      await addRateItem(bookId!, {
        work_item_code: itemForm.code,
        unit: itemForm.unit,
        rate,
        description: itemForm.description,
        trade: itemForm.trade,
      });
      setItemForm({ code: "", unit: "", rate: "", description: "", trade: "" });
      setPanel("");
    });
  }

  function beginEdit(item: RateItem) {
    setEditId(item.id);
    setItemForm({
      code: item.work_item_code,
      unit: item.unit,
      rate: String(item.rate),
      description: item.description ?? "",
      trade: item.trade ?? "",
    });
    setPanel("editItem");
  }

  async function handleSaveItem() {
    const rate = Number(itemForm.rate);
    if (!itemForm.rate.trim() || !Number.isFinite(rate) || rate < 0) {
      setError(tx("rateBook.badRate", "Enter a rate of zero or more."));
      return;
    }
    await act(async () => {
      await updateRateItem(editId, { rate, description: itemForm.description, trade: itemForm.trade });
      setPanel("");
      setEditId("");
    });
  }

  async function handleImport() {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["text/csv", "text/comma-separated-values", "text/plain", "*/*"],
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;
      const file = result.assets[0];
      if (!file.name.toLowerCase().endsWith(".csv")) {
        setError(tx("rateBook.csvOnly", "Choose a .csv file with columns work_item_code, unit, rate."));
        return;
      }
      await act(async () => {
        const out = await importRateItemsCsv(bookId!, { uri: file.uri, name: file.name, mimeType: file.mimeType });
        setNotice(tx("rateBook.imported", "Imported: {{created}} new, {{updated}} updated.", out));
      });
    } catch (err) {
      setError(describeError(err, tx("rateBook.actionFailure", "Action failed.")));
    }
  }

  async function handleAddEscalation() {
    const factor = Number(escForm.factor);
    if (!DATE.test(escForm.from.trim())) {
      setError(tx("rateBook.badDate", "Dates must look like 2026-10-31."));
      return;
    }
    if (!Number.isFinite(factor) || factor <= 0) {
      setError(tx("rateBook.badFactor", "Enter a factor above zero, for example 1.08."));
      return;
    }
    await act(async () => {
      await addEscalation(bookId!, {
        trade_scope: escForm.scope.trim() || "ALL",
        effective_from: escForm.from.trim(),
        factor,
        note: escForm.note.trim() || undefined,
      });
      setEscForm({ scope: "ALL", from: "", factor: "", note: "" });
      setPanel("");
    });
  }

  async function handleBulk() {
    const rows: { work_item_code: string; unit: string; rate: number; description?: string; trade?: string }[] = [];
    const lines = bulkText.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    for (const [index, line] of lines.entries()) {
      const cells = line.split(",").map((cell) => cell.trim());
      if (index === 0 && cells[0].toLowerCase() === "work_item_code") continue;
      const rate = Number((cells[2] ?? "").replace(/,/g, ""));
      if (!cells[0] || !cells[1] || !cells[2] || !Number.isFinite(rate) || rate < 0) {
        setError(tx("rateBook.bulkBadLine", "Line {{n}} is not valid. Use: code,unit,rate", { n: index + 1 }));
        return;
      }
      rows.push({ work_item_code: cells[0], unit: cells[1], rate, description: cells[3] || undefined, trade: cells[4] || undefined });
    }
    if (rows.length === 0) {
      setError(tx("rateBook.bulkEmpty", "Paste at least one line."));
      return;
    }
    if (rows.length > 2000) {
      setError(tx("rateBook.bulkTooMany", "At most 2000 lines at a time."));
      return;
    }
    await act(async () => {
      const out = await bulkUpsertRates(bookId!, rows);
      setNotice(tx("rateBook.imported", "Imported: {{created}} new, {{updated}} updated.", out));
      setBulkText("");
      setPanel("");
    });
  }

  async function toggleBreakdown(analysisId: string) {
    if (openAnalysis === analysisId) {
      setOpenAnalysis("");
      setBreakdown(null);
      return;
    }
    setOpenAnalysis(analysisId);
    setBreakdown(null);
    try {
      setBreakdown(await getAnalysisBreakdown(analysisId));
    } catch (err) {
      setError(describeError(err, tx("rateBook.actionFailure", "Action failed.")));
    }
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const rateForm = (saveLabel: string, onSave: () => void, lockCodes: boolean) => (
    <View style={ui.panel}>
      <Field label={tx("pricing.workItemCode", "Work item code")} value={itemForm.code} editable={!lockCodes} onChangeText={(v) => setItemForm((f) => ({ ...f, code: v }))} isUrdu={isUrdu} />
      <Field label={tx("pricing.unit", "Unit")} value={itemForm.unit} editable={!lockCodes} onChangeText={(v) => setItemForm((f) => ({ ...f, unit: v }))} isUrdu={isUrdu} />
      <Field label={tx("pricing.rate", "Rate")} value={itemForm.rate} onChangeText={(v) => setItemForm((f) => ({ ...f, rate: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
      <Field label={tx("rateBook.description", "Description")} value={itemForm.description} onChangeText={(v) => setItemForm((f) => ({ ...f, description: v }))} isUrdu={isUrdu} />
      <Field label={tx("rateBook.trade", "Trade")} value={itemForm.trade} onChangeText={(v) => setItemForm((f) => ({ ...f, trade: v }))} isUrdu={isUrdu} />
      <View style={[ui.row, isUrdu && ui.rtlRow]}>
        <Action title={saveLabel} disabled={busy} isUrdu={isUrdu} onPress={onSave} />
        <Action title={tx("drawingsBoq.cancel", "Cancel")} secondary isUrdu={isUrdu} onPress={() => setPanel("")} />
      </View>
    </View>
  );

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("rateBook.back", "Back to pricing")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{book ? `${book.code} v${book.immutable_version}` : ""}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}

        {book ? (
          <>
            <View style={ui.summaryBox}>
              <InfoRow label={tx("rateBook.name", "Name")} value={book.name} isUrdu={isUrdu} />
              <InfoRow label={tx("rateBook.status", "Status")} value={book.is_system ? `${book.status} · ${tx("pricing.system", "System")}` : book.status} isUrdu={isUrdu} />
              <InfoRow label={tx("rateBook.currency", "Currency")} value={book.currency} isUrdu={isUrdu} />
              <InfoRow label={tx("rateBook.edition", "Edition")} value={book.edition ?? "-"} isUrdu={isUrdu} />
              <InfoRow label={tx("rateBook.where", "Province / city")} value={[book.province, book.city].filter(Boolean).join(" / ") || "-"} isUrdu={isUrdu} />
              <InfoRow label={tx("rateBook.effective", "Effective")} value={`${book.effective_from ?? "…"} → ${book.effective_to ?? "…"}`} isUrdu={isUrdu} />
            </View>

            {canManage && !book.is_system ? (
              <View style={[ui.row, isUrdu && ui.rtlRow]}>
                {isDraft ? (
                  <>
                    <Action title={tx("rateBook.editDetails", "Edit details")} secondary={panel !== "details"} isUrdu={isUrdu} onPress={openDetails} />
                    <Action
                      title={tx("rateBook.publish", "Publish")}
                      disabled={busy}
                      isUrdu={isUrdu}
                      onPress={() =>
                        ask(tx("rateBook.publishTitle", "Publish this rate book?"), tx("rateBook.publishBody", "It becomes locked. Changes after that need a new version."), tx("rateBook.publish", "Publish"), () => void handlePublish())
                      }
                    />
                    <Action title={tx("rateBook.delete", "Delete")} secondary disabled={busy} isUrdu={isUrdu} onPress={handleDeleteBook} />
                  </>
                ) : (
                  <>
                    <Action title={tx("rateBook.newVersion", "Start a new version")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleNewVersion()} />
                    {book.status === "ACTIVE" || book.status === "SUPERSEDED" ? (
                      <Action
                        title={tx("rateBook.archive", "Archive")}
                        secondary
                        disabled={busy}
                        isUrdu={isUrdu}
                        onPress={() => ask(tx("rateBook.archiveTitle", "Archive this rate book?"), "", tx("rateBook.archive", "Archive"), () => void act(() => archiveRateBook(bookId!)))}
                      />
                    ) : null}
                  </>
                )}
              </View>
            ) : (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {book.is_system
                  ? tx("rateBook.systemNote", "System rate book. Read only.")
                  : tx("rateBook.noRights", "You can view this rate book but not change it.")}
              </Text>
            )}

            {panel === "details" ? (
              <View style={ui.panel}>
                <Field label={tx("rateBook.name", "Name")} value={details.name} onChangeText={(v) => setDetails((d) => ({ ...d, name: v }))} isUrdu={isUrdu} />
                <Field label={tx("rateBook.edition", "Edition")} value={details.edition} onChangeText={(v) => setDetails((d) => ({ ...d, edition: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.province", "Province")} value={details.province} onChangeText={(v) => setDetails((d) => ({ ...d, province: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.city", "City")} value={details.city} onChangeText={(v) => setDetails((d) => ({ ...d, city: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.from", "From (2026-10-31)")} value={details.from} onChangeText={(v) => setDetails((d) => ({ ...d, from: v }))} isUrdu={isUrdu} />
                <Field label={tx("pricing.to", "To")} value={details.to} onChangeText={(v) => setDetails((d) => ({ ...d, to: v }))} isUrdu={isUrdu} />
                <Action title={tx("rateBook.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void saveDetails()} />
              </View>
            ) : null}

            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Action title={`${tx("rateBook.tabItems", "Rates")} (${book.item_count})`} secondary={tab !== "items"} isUrdu={isUrdu} onPress={() => { setTab("items"); setPanel(""); }} />
              <Action title={`${tx("rateBook.tabEsc", "Escalations")} (${book.escalation_count})`} secondary={tab !== "escalations"} isUrdu={isUrdu} onPress={() => { setTab("escalations"); setPanel(""); }} />
              <Action title={`${tx("rateBook.tabAnalyses", "Analyses")} (${book.analysis_count})`} secondary={tab !== "analyses"} isUrdu={isUrdu} onPress={() => { setTab("analyses"); setPanel(""); }} />
            </View>

            {tab === "items" ? (
              <>
                <Field label={tx("rateBook.search", "Search by code or description")} value={search} onChangeText={setSearch} isUrdu={isUrdu} />
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  <Action title={tx("rateBook.searchGo", "Search")} secondary isUrdu={isUrdu} onPress={() => void act(async () => undefined)} />
                  {editable ? (
                    <>
                      <Action title={tx("rateBook.addRate", "Add a rate")} secondary={panel !== "addItem"} isUrdu={isUrdu} onPress={() => { setItemForm({ code: "", unit: "", rate: "", description: "", trade: "" }); setPanel(panel === "addItem" ? "" : "addItem"); }} />
                      <Action title={tx("rateBook.importCsv", "Import CSV")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void handleImport()} />
                      <Action title={tx("rateBook.pasteRates", "Paste rates")} secondary={panel !== "bulk"} isUrdu={isUrdu} onPress={() => setPanel(panel === "bulk" ? "" : "bulk")} />
                    </>
                  ) : null}
                </View>
                {panel === "bulk" ? (
                  <View style={ui.panel}>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {tx("rateBook.bulkHelp", "One rate per line: code,unit,rate and optionally ,description,trade. Existing rates with the same code and unit are updated.")}
                    </Text>
                    <Field label={tx("rateBook.bulkLabel", "Rates")} value={bulkText} onChangeText={setBulkText} multiline isUrdu={isUrdu} />
                    <Action title={tx("rateBook.bulkRun", "Add or update rates")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleBulk()} />
                  </View>
                ) : null}
                {panel === "addItem" ? rateForm(tx("rateBook.addRate", "Add a rate"), () => void handleAddItem(), false) : null}
                {items.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("rateBook.noItems", "No rates found.")}</Text> : null}
                {items.length >= 200 ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("rateBook.first200", "Showing the first 200. Use search to find others.")}</Text>
                ) : null}
                {items.map((item) => (
                  <View key={item.id} style={ui.boqItem}>
                    <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                      <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${item.work_item_code} · ${formatMoney(item.rate, locale, "-")} / ${item.unit}`}</Text>
                      {!item.is_active ? <Badge label={tx("rateBook.inactive", "Inactive")} tone="warn" /> : null}
                    </View>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>{[item.description, item.trade, item.analysis_id ? tx("rateBook.fromAnalysis", "from analysis") : null].filter(Boolean).join(" · ")}</Text>
                    {editable ? (
                      <View style={[ui.row, isUrdu && ui.rtlRow]}>
                        <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => beginEdit(item)} />
                        <Action title={item.is_active ? tx("rateBook.deactivate", "Deactivate") : tx("rateBook.activate", "Activate")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void act(() => updateRateItem(item.id, { is_active: !item.is_active }))} />
                        <Action title={tx("rateBook.delete", "Delete")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => ask(tx("rateBook.deleteRateTitle", "Delete this rate?"), "", tx("rateBook.delete", "Delete"), () => void act(() => deleteRateItem(item.id)))} />
                      </View>
                    ) : null}
                    {panel === "editItem" && editId === item.id ? rateForm(tx("rateBook.save", "Save"), () => void handleSaveItem(), true) : null}
                  </View>
                ))}
              </>
            ) : null}

            {tab === "escalations" ? (
              <>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("rateBook.escHelp", "An escalation multiplies rates from its date onward. Scope ALL applies to every trade.")}
                </Text>
                {editable ? (
                  <Action title={tx("rateBook.addEsc", "Add an escalation")} secondary={panel !== "addEscalation"} isUrdu={isUrdu} onPress={() => setPanel(panel === "addEscalation" ? "" : "addEscalation")} />
                ) : null}
                {panel === "addEscalation" ? (
                  <View style={ui.panel}>
                    <Field label={tx("rateBook.scope", "Trade scope (ALL or a trade)")} value={escForm.scope} onChangeText={(v) => setEscForm((f) => ({ ...f, scope: v }))} isUrdu={isUrdu} />
                    <Field label={tx("rateBook.escFrom", "Effective from (2026-10-31)")} value={escForm.from} onChangeText={(v) => setEscForm((f) => ({ ...f, from: v }))} isUrdu={isUrdu} />
                    <Field label={tx("rateBook.factor", "Factor (for example 1.08)")} value={escForm.factor} onChangeText={(v) => setEscForm((f) => ({ ...f, factor: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
                    <Field label={tx("rateBook.note", "Note (optional)")} value={escForm.note} onChangeText={(v) => setEscForm((f) => ({ ...f, note: v }))} isUrdu={isUrdu} />
                    <Action title={tx("rateBook.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleAddEscalation()} />
                  </View>
                ) : null}
                {escalations.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("rateBook.noEsc", "No escalations.")}</Text> : null}
                {escalations.map((esc) => (
                  <View key={esc.id} style={ui.boqItem}>
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${esc.trade_scope} · ×${formatNumber(esc.factor, 4)} · ${esc.effective_from}`}</Text>
                    {esc.note ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{esc.note}</Text> : null}
                    {editable ? (
                      <Action title={tx("rateBook.delete", "Delete")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => ask(tx("rateBook.deleteEscTitle", "Delete this escalation?"), "", tx("rateBook.delete", "Delete"), () => void act(() => deleteEscalation(esc.id)))} />
                    ) : null}
                  </View>
                ))}
              </>
            ) : null}

            {tab === "analyses" ? (
              <>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("rateBook.analysisHelp", "A rate analysis builds a rate from materials, labour and plant. Compute it, then apply it to put the result in the rates list. New analyses are created on the web for now.")}
                </Text>
                {editable ? (
                  <Action
                    title={tx("rateBook.newAnalysis", "New analysis")}
                    secondary
                    isUrdu={isUrdu}
                    onPress={() => router.push({ pathname: "/projects/[projectId]/analysis-edit", params: { projectId: first(params.projectId) ?? "", bookId: bookId ?? "" } })}
                  />
                ) : null}
                {analyses.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("rateBook.noAnalyses", "No analyses.")}</Text> : null}
                {analyses.map((analysis) => (
                  <View key={analysis.id} style={ui.boqItem}>
                    <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                      <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${analysis.code} · ${analysis.work_item_code}`}</Text>
                      <Badge label={analysis.computed_rate == null ? tx("rateBook.notComputed", "Not computed") : `${formatMoney(analysis.computed_rate, locale, "-")} / ${analysis.unit}`} tone={analysis.computed_rate == null ? "warn" : "good"} />
                    </View>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {`${analysis.description} · ${tx("rateBook.basis", "per {{qty}} {{unit}}", { qty: formatNumber(analysis.basis_quantity, 4), unit: analysis.unit })} · ${tx("rateBook.ohp", "overhead {{o}}% · profit {{p}}%", { o: formatNumber(analysis.overhead_pct, 3), p: formatNumber(analysis.profit_pct, 3) })}`}
                    </Text>
                    {analysis.components.map((c) => (
                      <Text key={c.id} style={[ui.muted, isUrdu && ui.rtlText]}>
                        {`${c.sequence}. ${c.component_type} · ${c.description} · ${formatNumber(c.coefficient, 6)} ${c.unit}${c.unit_rate != null ? ` @ ${formatNumber(c.unit_rate, 2)}` : ""}`}
                      </Text>
                    ))}
                    <View style={[ui.row, isUrdu && ui.rtlRow]}>
                      <Action title={openAnalysis === analysis.id ? tx("rateBook.hideBreakdown", "Hide breakdown") : tx("rateBook.breakdown", "Breakdown")} secondary isUrdu={isUrdu} onPress={() => void toggleBreakdown(analysis.id)} />
                      {editable ? (
                        <>
                          <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => router.push({ pathname: "/projects/[projectId]/analysis-edit", params: { projectId: first(params.projectId) ?? "", bookId: bookId ?? "", analysisId: analysis.id } })} />
                          <Action title={tx("rateBook.compute", "Compute")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void act(() => computeAnalysis(analysis.id), tx("rateBook.computed", "Computed."))} />
                          <Action title={tx("rateBook.apply", "Apply to rates")} disabled={busy || analysis.computed_rate == null} isUrdu={isUrdu} onPress={() => void act(() => applyAnalysis(analysis.id), tx("rateBook.applied", "Applied to the rates list."))} />
                          <Action title={tx("rateBook.delete", "Delete")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => ask(tx("rateBook.deleteAnalysisTitle", "Delete this analysis?"), "", tx("rateBook.delete", "Delete"), () => void act(() => deleteAnalysis(analysis.id)))} />
                        </>
                      ) : null}
                    </View>
                    {openAnalysis === analysis.id ? (
                      <View style={ui.panel}>
                        {!breakdown ? <ActivityIndicator color={COLORS.navy} /> : null}
                        {breakdown ? (
                          <>
                            {breakdown.lines.map((line, index) => (
                              <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>{lineText(line)}</Text>
                            ))}
                            <InfoRow label={tx("rateBook.cost", "Cost")} value={breakdown.cost} isUrdu={isUrdu} />
                            <InfoRow label={tx("rateBook.overhead", "Overhead")} value={breakdown.overhead} isUrdu={isUrdu} />
                            <InfoRow label={tx("rateBook.profit", "Profit")} value={breakdown.profit} isUrdu={isUrdu} />
                            <InfoRow label={tx("rateBook.total", "Total")} value={breakdown.total} isUrdu={isUrdu} />
                            <InfoRow label={tx("rateBook.rate", "Rate")} value={`${breakdown.rate} / ${breakdown.unit}`} isUrdu={isUrdu} />
                          </>
                        ) : null}
                      </View>
                    ) : null}
                  </View>
                ))}
              </>
            ) : null}
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
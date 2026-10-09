import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getAnalysis, listRateItems } from "../../../../api/pricing";
import { createAnalysis, updateAnalysis } from "../../../../api/pricingExtras";
import type {AnalysisComponentInput, AnalysisComponentSource, AnalysisComponentType, RateItem,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, COLORS, Field, ui } from "../../../../features/drawingsBoq/ui";

type Draft = {
  key: number;
  type: AnalysisComponentType;
  description: string;
  workItem: string;
  source: AnalysisComponentSource;
  refId: string;
  refLabel: string;
  unit: string;
  coefficient: string;
  unitRate: string;
};

const TYPES: AnalysisComponentType[] = ["MATERIAL", "LABOUR", "PLANT", "OTHER"];
const SOURCES: AnalysisComponentSource[] = ["DIRECT", "RATE_ITEM", "LABOUR_RATE", "MATERIAL_LIBRARY"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

let nextKey = 1;
function blank(): Draft {
  return { key: nextKey++, type: "MATERIAL", description: "", workItem: "", source: "DIRECT", refId: "", refLabel: "", unit: "", coefficient: "", unitRate: "" };
}

export default function AnalysisEditScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; bookId?: string; analysisId?: string }>();
  const bookId = first(params.bookId);
  const analysisId = first(params.analysisId);
  const editing = Boolean(analysisId);

  const [allowed, setAllowed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [head, setHead] = useState({ code: "", workItem: "", description: "", unit: "", basis: "1", overhead: "0", profit: "0" });
  const [parts, setParts] = useState<Draft[]>([]);
  const [rateItems, setRateItems] = useState<RateItem[] | null>(null);
  const [pickFor, setPickFor] = useState(0);
  const [pickSearch, setPickSearch] = useState("");

  const load = useCallback(async () => {
    if (!bookId) {
      setError(tx("analysisEdit.notFound", "Rate book not found."));
      setLoading(false);
      return;
    }
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setAllowed(hasPerm(user.role.permissions.map((p) => p.key), PERM.RATEBOOK_MANAGE));
      if (analysisId) {
        const a = await getAnalysis(analysisId);
        setHead({
          code: a.code,
          workItem: a.work_item_code,
          description: a.description,
          unit: a.unit,
          basis: String(a.basis_quantity),
          overhead: String(a.overhead_pct),
          profit: String(a.profit_pct),
        });
        setParts(
          a.components.map((c) => ({
            key: nextKey++,
            type: c.component_type as AnalysisComponentType,
            description: c.description,
            workItem: c.work_item_code ?? "",
            source: c.rate_source as AnalysisComponentSource,
            refId: c.ref_rate_item_id ?? "",
            refLabel: c.ref_rate_item_id ? tx("analysisEdit.chosenRate", "chosen rate") : "",
            unit: c.unit,
            coefficient: String(c.coefficient),
            unitRate: c.unit_rate == null ? "" : String(c.unit_rate),
          })),
        );
      }
    } catch (err) {
      setError(describeError(err, tx("analysisEdit.loadFailure", "Could not load the analysis.")));
    } finally {
      setLoading(false);
    }

  }, [bookId, analysisId]);

  useEffect(() => {
    void load();
  }, [load]);

  function patch(key: number, change: Partial<Draft>) {
    setParts((current) => current.map((p) => (p.key === key ? { ...p, ...change } : p)));
  }

  async function openPicker(key: number) {
    if (pickFor === key) {
      setPickFor(0);
      return;
    }
    setPickFor(key);
    setPickSearch("");
    if (rateItems === null && bookId) {
      try {
        setRateItems(await listRateItems(bookId));
      } catch (err) {
        setError(describeError(err, tx("analysisEdit.itemsFailure", "Could not load rates.")));
        setRateItems([]);
      }
    }
  }

  function buildComponents(): AnalysisComponentInput[] | string {
    const out: AnalysisComponentInput[] = [];
    for (const [index, p] of parts.entries()) {
      const label = tx("analysisEdit.ingredient", "Ingredient {{n}}", { n: index + 1 });
      const coefficient = Number(p.coefficient);
      if (!p.description.trim() || !p.unit.trim()) return `${label}: ${tx("analysisEdit.needDescUnit", "enter a description and a unit.")}`;
      if (!p.coefficient.trim() || !Number.isFinite(coefficient) || coefficient < 0) return `${label}: ${tx("analysisEdit.badCoefficient", "enter a quantity of zero or more.")}`;
      const part: AnalysisComponentInput = {
        component_type: p.type,
        description: p.description.trim(),
        work_item_code: p.workItem.trim() || undefined,
        rate_source: p.source,
        unit: p.unit.trim().toLowerCase(),
        coefficient,
      };
      if (p.source === "DIRECT") {
        const rate = Number(p.unitRate);
        if (!p.unitRate.trim() || !Number.isFinite(rate) || rate < 0) return `${label}: ${tx("analysisEdit.needRate", "a direct ingredient needs a rate.")}`;
        part.unit_rate = rate;
      }
      if (p.source === "RATE_ITEM") {
        if (!p.refId) return `${label}: ${tx("analysisEdit.needRef", "choose a rate from this book.")}`;
        part.ref_rate_item_id = p.refId;
      }
      out.push(part);
    }
    return out;
  }

  async function handleSave() {
    if (!bookId) return;
    const basis = Number(head.basis);
    const overhead = Number(head.overhead || "0");
    const profit = Number(head.profit || "0");
    if (!editing && (!head.code.trim() || !head.workItem.trim())) {
      setError(tx("analysisEdit.needCode", "Enter an analysis code and a work item code."));
      return;
    }
    if (!head.description.trim() || !head.unit.trim()) {
      setError(tx("analysisEdit.needDesc", "Enter a description and a unit."));
      return;
    }
    if (!Number.isFinite(basis) || basis <= 0 || !Number.isFinite(overhead) || overhead < 0 || !Number.isFinite(profit) || profit < 0) {
      setError(tx("analysisEdit.badNumbers", "Basis quantity must be above zero. Overhead and profit must be zero or more."));
      return;
    }
    const components = buildComponents();
    if (typeof components === "string") {
      setError(components);
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (editing && analysisId) {
        await updateAnalysis(analysisId, {
          description: head.description.trim(),
          unit: head.unit.trim().toLowerCase(),
          basis_quantity: basis,
          overhead_pct: overhead,
          profit_pct: profit,
          components,
        });
      } else {
        await createAnalysis(bookId, {
          code: head.code.trim(),
          work_item_code: head.workItem.trim(),
          description: head.description.trim(),
          unit: head.unit.trim().toLowerCase(),
          basis_quantity: basis,
          overhead_pct: overhead,
          profit_pct: profit,
          components,
        });
      }
      router.back();
    } catch (err) {
      setError(describeError(err, tx("analysisEdit.saveFailure", "Could not save the analysis.")));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const matches = (rateItems ?? [])
    .filter((item) => {
      const q = pickSearch.trim().toLowerCase();
      return !q || item.work_item_code.toLowerCase().includes(q) || (item.description ?? "").toLowerCase().includes(q);
    })
    .slice(0, 8);

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("analysisEdit.back", "Back to rate book")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>
              {editing ? tx("analysisEdit.editTitle", "Edit analysis") : tx("analysisEdit.newTitle", "New analysis")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {!allowed ? (
          <Text style={[ui.error, isUrdu && ui.rtlText]}>{tx("analysisEdit.noRights", "You do not have permission to change rate books.")}</Text>
        ) : null}
        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        <View style={ui.panel}>
          <Field label={tx("analysisEdit.code", "Analysis code")} value={head.code} editable={!editing} onChangeText={(v) => setHead((h) => ({ ...h, code: v }))} isUrdu={isUrdu} />
          <Field label={tx("pricing.workItemCode", "Work item code")} value={head.workItem} editable={!editing} onChangeText={(v) => setHead((h) => ({ ...h, workItem: v }))} isUrdu={isUrdu} />
          <Field label={tx("rateBook.description", "Description")} value={head.description} onChangeText={(v) => setHead((h) => ({ ...h, description: v }))} isUrdu={isUrdu} />
          <Field label={tx("pricing.unit", "Unit")} value={head.unit} onChangeText={(v) => setHead((h) => ({ ...h, unit: v }))} isUrdu={isUrdu} />
          <Field label={tx("analysisEdit.basis", "Basis quantity (the amount these ingredients make)")} value={head.basis} onChangeText={(v) => setHead((h) => ({ ...h, basis: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
          <Field label={tx("analysisEdit.overhead", "Overhead %")} value={head.overhead} onChangeText={(v) => setHead((h) => ({ ...h, overhead: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
          <Field label={tx("analysisEdit.profit", "Profit %")} value={head.profit} onChangeText={(v) => setHead((h) => ({ ...h, profit: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
        </View>

        <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("analysisEdit.ingredients", "Ingredients")}</Text>

        {parts.map((p, index) => (
          <View key={p.key} style={ui.boqItem}>
            <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("analysisEdit.ingredient", "Ingredient {{n}}", { n: index + 1 })}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {TYPES.map((value) => (
                <Action key={value} title={value} secondary={p.type !== value} isUrdu={isUrdu} onPress={() => patch(p.key, { type: value })} />
              ))}
            </View>
            <Field label={tx("rateBook.description", "Description")} value={p.description} onChangeText={(v) => patch(p.key, { description: v })} isUrdu={isUrdu} />
            <Field label={tx("analysisEdit.workItemOpt", "Work item code (optional)")} value={p.workItem} onChangeText={(v) => patch(p.key, { workItem: v })} isUrdu={isUrdu} />
            <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("analysisEdit.rateFrom", "Where the rate comes from")}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {SOURCES.map((value) => (
                <Action key={value} title={tx(`analysisEdit.source.${value.toLowerCase()}`, value.replaceAll("_", " "))} secondary={p.source !== value} isUrdu={isUrdu} onPress={() => patch(p.key, { source: value })} />
              ))}
            </View>
            {p.source === "DIRECT" ? (
              <Field label={tx("analysisEdit.unitRate", "Rate per unit")} value={p.unitRate} onChangeText={(v) => patch(p.key, { unitRate: v })} keyboardType="decimal-pad" isUrdu={isUrdu} />
            ) : null}
            {p.source === "RATE_ITEM" ? (
              <>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{p.refLabel || tx("analysisEdit.noneChosen", "No rate chosen yet.")}</Text>
                <Action title={pickFor === p.key ? tx("analysisEdit.closePicker", "Close list") : tx("analysisEdit.chooseRate", "Choose a rate from this book")} secondary isUrdu={isUrdu} onPress={() => void openPicker(p.key)} />
                {pickFor === p.key ? (
                  <View style={ui.panel}>
                    <Field label={tx("rateBook.search", "Search by code or description")} value={pickSearch} onChangeText={setPickSearch} isUrdu={isUrdu} />
                    {rateItems === null ? <ActivityIndicator color={COLORS.navy} /> : null}
                    {matches.map((item) => (
                      <Pressable
                        key={item.id}
                        style={ui.boqItem}
                        onPress={() => {
                          patch(p.key, { refId: item.id, refLabel: `${item.work_item_code} · ${item.rate} / ${item.unit}`, unit: p.unit || item.unit });
                          setPickFor(0);
                        }}
                      >
                        <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${item.work_item_code} · ${item.rate} / ${item.unit}`}</Text>
                        <Text style={[ui.muted, isUrdu && ui.rtlText]}>{item.description ?? ""}</Text>
                      </Pressable>
                    ))}
                  </View>
                ) : null}
              </>
            ) : null}
            {p.source === "LABOUR_RATE" || p.source === "MATERIAL_LIBRARY" ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("analysisEdit.byCode", "The rate is looked up from the library using the work item code above.")}
              </Text>
            ) : null}
            <Field label={tx("analysisEdit.ingredientUnit", "Unit of this ingredient")} value={p.unit} onChangeText={(v) => patch(p.key, { unit: v })} isUrdu={isUrdu} />
            <Field label={tx("analysisEdit.coefficient", "Quantity used")} value={p.coefficient} onChangeText={(v) => patch(p.key, { coefficient: v })} keyboardType="decimal-pad" isUrdu={isUrdu} />
            <Action title={tx("analysisEdit.removeIngredient", "Remove ingredient")} secondary isUrdu={isUrdu} onPress={() => setParts((current) => current.filter((x) => x.key !== p.key))} />
          </View>
        ))}

        <Action title={tx("analysisEdit.addIngredient", "Add an ingredient")} secondary isUrdu={isUrdu} onPress={() => setParts((current) => [...current, blank()])} />
        <Action title={tx("analysisEdit.save", "Save analysis")} disabled={busy || !allowed} isUrdu={isUrdu} onPress={() => void handleSave()} />
        <Text style={[ui.muted, isUrdu && ui.rtlText]}>
          {tx("analysisEdit.afterSave", "After saving, open Compute on the rate book screen to calculate the rate, then Apply to put it in the rates list.")}
        </Text>

        {busy ? (
          <View style={ui.busy}>
            <ActivityIndicator color={COLORS.navy} />
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
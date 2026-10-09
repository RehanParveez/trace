import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { getRuleSet, listFormulas, upsertRecipe } from "../../../../api/standards";
import type { Formula, RecipePayload } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, COLORS, Field, ui } from "../../../../features/drawingsBoq/ui";

type ItemType = "MATERIAL" | "LABOUR" | "CUSTOM";
type Part = {
  key: number;
  sequence: string;
  workItem: string;
  description: string;
  unit: string;
  formula: string;
  category: string;
  itemType: ItemType;
  optional: boolean;
};

const ITEM_TYPES: ItemType[] = ["MATERIAL", "LABOUR", "CUSTOM"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

let nextKey = 1;
function blank(sequence: number): Part {
  return { key: nextKey++, sequence: String(sequence), workItem: "", description: "", unit: "", formula: "", category: "", itemType: "MATERIAL", optional: false };
}

export default function RecipeEditScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; ruleSetId?: string; recipeId?: string }>();
  const ruleSetId = first(params.ruleSetId);
  const recipeId = first(params.recipeId);
  const editing = Boolean(recipeId);

  const [allowed, setAllowed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [head, setHead] = useState({ code: "", name: "", description: "", triggers: "", conditions: "{}" });
  const [parts, setParts] = useState<Part[]>([]);
  const [formulas, setFormulas] = useState<Formula[]>([]);
  const [pickFor, setPickFor] = useState(0);
  const [pickSearch, setPickSearch] = useState("");

  const load = useCallback(async () => {
    if (!ruleSetId) {
      setError(tx("recipe.notFound", "Rule set not found."));
      setLoading(false);
      return;
    }
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setAllowed(hasPerm(user.role.permissions.map((p) => p.key), PERM.RULESET_MANAGE));
      const [detail, list] = await Promise.all([getRuleSet(ruleSetId), listFormulas()]);
      setFormulas(list);
      const recipe = recipeId ? detail.recipes.find((r) => r.id === recipeId) : undefined;
      if (recipe) {
        setHead({
          code: recipe.code,
          name: recipe.name,
          description: recipe.description ?? "",
          triggers: recipe.trigger_ifc_types.join(", "),
          conditions: JSON.stringify(recipe.trigger_conditions ?? {}),
        });
        setParts(
          recipe.components.map((c) => ({
            key: nextKey++,
            sequence: String(c.sequence),
            workItem: c.work_item_code ?? "",
            description: c.description_template,
            unit: c.unit,
            formula: c.quantity_formula_code,
            category: c.category ?? "",
            itemType: (c.item_type as ItemType) ?? "MATERIAL",
            optional: c.is_optional,
          })),
        );
      } else {
        setParts([blank(1)]);
      }
    } catch (err) {
      setError(describeError(err, tx("recipe.loadFailure", "Could not load the recipe.")));
    } finally {
      setLoading(false);
    }
  }, [ruleSetId, recipeId]);

  useEffect(() => {
    void load();
  }, [load]);

  function patch(key: number, change: Partial<Part>) {
    setParts((current) => current.map((p) => (p.key === key ? { ...p, ...change } : p)));
  }

  async function handleSave() {
    if (!ruleSetId) return;
    if (!head.code.trim() || !head.name.trim()) {
      setError(tx("recipe.needCodeName", "Enter a code and a name."));
      return;
    }
    const triggers = head.triggers.split(",").map((s) => s.trim()).filter(Boolean);
    if (triggers.length === 0) {
      setError(tx("recipe.needTriggers", "Enter at least one IFC type, for example IfcWall."));
      return;
    }
    let conditions: Record<string, unknown> = {};
    try {
      const parsed = JSON.parse(head.conditions.trim() || "{}");
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("not an object");
      conditions = parsed as Record<string, unknown>;
    } catch {
      setError(tx("recipe.badConditions", "Conditions must be a JSON object, for example {}."));
      return;
    }
    if (parts.length === 0) {
      setError(tx("recipe.needParts", "Add at least one component."));
      return;
    }
    const components: RecipePayload["components"] = [];
    for (const [index, p] of parts.entries()) {
      const label = tx("recipe.component", "Component {{n}}", { n: index + 1 });
      const sequence = Number(p.sequence);
      if (!p.description.trim() || !p.unit.trim() || !p.formula.trim()) {
        return setError(`${label}: ${tx("recipe.needFields", "enter a description, a unit and a formula.")}`);
      }
      if (!Number.isInteger(sequence) || sequence < 0) {
        return setError(`${label}: ${tx("recipe.badSequence", "the order number must be a whole number.")}`);
      }
      components.push({
        sequence,
        work_item_code: p.workItem.trim() || undefined,
        description_template: p.description.trim(),
        unit: p.unit.trim().toLowerCase(),
        quantity_formula_code: p.formula.trim(),
        category: p.category.trim() || undefined,
        item_type: p.itemType,
        is_optional: p.optional,
      });
    }
    setBusy(true);
    setError("");
    try {
      await upsertRecipe(ruleSetId, {
        code: head.code.trim(),
        name: head.name.trim(),
        description: head.description.trim() || undefined,
        trigger_ifc_types: triggers,
        trigger_conditions: conditions,
        components,
      });
      router.back();
    } catch (err) {
      setError(describeError(err, tx("recipe.saveFailure", "Could not save the recipe.")));
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

  const matches = formulas
    .filter((f) => {
      const q = pickSearch.trim().toLowerCase();
      return !q || f.code.toLowerCase().includes(q) || f.description.toLowerCase().includes(q);
    })
    .slice(0, 8);

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("recipe.back", "Back to rule set")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>
              {editing ? tx("recipe.editTitle", "Edit recipe") : tx("recipe.newTitle", "New recipe")}
            </Text>
          </View>
          <LanguageSwitcher />
        </View>

        {!allowed ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{tx("recipe.noRights", "You do not have permission to change rule sets.")}</Text> : null}
        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        <View style={ui.panel}>
          <Field label={tx("recipe.code", "Recipe code")} value={head.code} editable={!editing} onChangeText={(v) => setHead((h) => ({ ...h, code: v }))} isUrdu={isUrdu} />
          <Field label={tx("recipe.name", "Name")} value={head.name} onChangeText={(v) => setHead((h) => ({ ...h, name: v }))} isUrdu={isUrdu} />
          <Field label={tx("recipe.description", "Description (optional)")} value={head.description} onChangeText={(v) => setHead((h) => ({ ...h, description: v }))} isUrdu={isUrdu} />
          <Field label={tx("recipe.triggers", "Applies to IFC types, comma separated (for example IfcWall, IfcWallStandardCase)")} value={head.triggers} onChangeText={(v) => setHead((h) => ({ ...h, triggers: v }))} isUrdu={isUrdu} />
          <Field label={tx("recipe.conditions", "Extra conditions as JSON (advanced, leave as {})")} value={head.conditions} onChangeText={(v) => setHead((h) => ({ ...h, conditions: v }))} multiline isUrdu={isUrdu} />
        </View>

        <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("recipe.components", "Components")}</Text>

        {parts.map((p, index) => (
          <View key={p.key} style={ui.boqItem}>
            <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{tx("recipe.component", "Component {{n}}", { n: index + 1 })}</Text>
            <Field label={tx("recipe.sequence", "Order number")} value={p.sequence} onChangeText={(v) => patch(p.key, { sequence: v })} keyboardType="decimal-pad" isUrdu={isUrdu} />
            <Field label={tx("recipe.descTemplate", "BOQ line description")} value={p.description} onChangeText={(v) => patch(p.key, { description: v })} isUrdu={isUrdu} />
            <Field label={tx("recipe.workItem", "Work item code (optional)")} value={p.workItem} onChangeText={(v) => patch(p.key, { workItem: v })} isUrdu={isUrdu} />
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {p.formula ? `${tx("recipe.formula", "Formula")}: ${p.formula}` : tx("recipe.noFormula", "No formula chosen yet.")}
            </Text>
            <Action title={pickFor === p.key ? tx("recipe.closePicker", "Close list") : tx("recipe.chooseFormula", "Choose a formula")} secondary isUrdu={isUrdu} onPress={() => { setPickFor(pickFor === p.key ? 0 : p.key); setPickSearch(""); }} />
            {pickFor === p.key ? (
              <View style={ui.panel}>
                <Field label={tx("recipe.searchFormula", "Search formulas")} value={pickSearch} onChangeText={setPickSearch} isUrdu={isUrdu} />
                {matches.map((f) => (
                  <Pressable
                    key={f.code}
                    style={ui.boqItem}
                    onPress={() => {
                      patch(p.key, { formula: f.code, unit: f.output_unit });
                      setPickFor(0);
                    }}
                  >
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${f.code} → ${f.output_unit}`}</Text>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>{f.description}</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
            <Field label={tx("recipe.unit", "Unit (must equal the formula's output unit)")} value={p.unit} onChangeText={(v) => patch(p.key, { unit: v })} isUrdu={isUrdu} />
            <Field label={tx("recipe.category", "Category (optional)")} value={p.category} onChangeText={(v) => patch(p.key, { category: v })} isUrdu={isUrdu} />
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {ITEM_TYPES.map((value) => (
                <Action key={value} title={value} secondary={p.itemType !== value} isUrdu={isUrdu} onPress={() => patch(p.key, { itemType: value })} />
              ))}
            </View>
            <Action
              title={p.optional ? tx("recipe.optionalOn", "Optional line") : tx("recipe.optionalOff", "Always included")}
              secondary={!p.optional}
              isUrdu={isUrdu}
              onPress={() => patch(p.key, { optional: !p.optional })}
            />
            <Action title={tx("recipe.removeComponent", "Remove component")} secondary isUrdu={isUrdu} onPress={() => setParts((current) => current.filter((x) => x.key !== p.key))} />
          </View>
        ))}

        <Action title={tx("recipe.addComponent", "Add a component")} secondary isUrdu={isUrdu} onPress={() => setParts((current) => [...current, blank(current.length + 1)])} />
        <Action title={tx("recipe.save", "Save recipe")} disabled={busy || !allowed} isUrdu={isUrdu} onPress={() => void handleSave()} />

        {busy ? (
          <View style={ui.busy}>
            <ActivityIndicator color={COLORS.navy} />
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
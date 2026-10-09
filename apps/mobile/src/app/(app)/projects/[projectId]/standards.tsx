import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {createRuleSetDraft, createWorkItem, getFinishOptions, getResolvedStandards, listConventions, listFormulas, listRuleSets, listWorkItemsFull, updateWorkItem,
} from "../../../../api/standards";
import type { Convention, FinishOptions, Formula, RuleSet, WorkItemFull } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { FieldsForm, parseValues, toValues, type FieldSpec, type Values } from "../../../../features/drawingsBoq/formKit";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, ui } from "../../../../features/drawingsBoq/ui";

type Tab = "rulesets" | "items" | "reference";
type Ref = "" | "formulas" | "conventions" | "finish" | "resolved";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function tone(status: string): "neutral" | "good" | "warn" | "bad" {
  if (status === "ACTIVE" || status === "PUBLISHED") return "good";
  if (status === "DRAFT") return "warn";
  return "neutral";
}

const SHOW_LIMIT = 40;

export default function StandardsScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId) ?? "";

  const [permissions, setPermissions] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>("rulesets");
  const [ruleSets, setRuleSets] = useState<RuleSet[]>([]);
  const [conventions, setConventions] = useState<Convention[]>([]);
  const [workItems, setWorkItems] = useState<WorkItemFull[]>([]);
  const [formulas, setFormulas] = useState<Formula[]>([]);
  const [finish, setFinish] = useState<FinishOptions | null>(null);
  const [ref, setRef] = useState<Ref>("");
  const [resolvedCode, setResolvedCode] = useState("");
  const [resolvedDate, setResolvedDate] = useState("");
  const [resolved, setResolved] = useState<Record<string, unknown> | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [adding, setAdding] = useState(false);
  const [editId, setEditId] = useState("");
  const [values, setValues] = useState<Values>({});

  const canManage = hasPerm(permissions, PERM.RULESET_MANAGE);

  const conventionCodes = conventions.map((c) => c.code);

  const ruleSetFields: FieldSpec[] = [
    { key: "code", label: tx("standards.code", "Code"), required: true, createOnly: true },
    { key: "name", label: tx("standards.name", "Name"), required: true },
    { key: "standard_name", label: tx("standards.standardName", "Standard (for example CSR 2023)") },
    { key: "standard_edition", label: tx("standards.edition", "Edition") },
    { key: "province", label: tx("standards.province", "Province") },
    { key: "city", label: tx("standards.city", "City") },
    { key: "convention_code", label: tx("standards.convention", "Measurement convention"), kind: "choice", choices: conventionCodes },
  ];

  const itemFields: FieldSpec[] = [
    { key: "code", label: tx("standards.itemCode", "Work item code"), required: true, createOnly: true },
    { key: "description", label: tx("standards.description", "Description"), required: true },
    { key: "unit", label: tx("standards.unit", "Unit"), kind: "choice", choices: ["m3", "m2", "m", "kg", "nos"], required: true, createOnly: true },
    { key: "trade", label: tx("standards.trade", "Trade") },
    { key: "wbs_code", label: tx("standards.wbs", "WBS code") },
    { key: "specification", label: tx("standards.spec", "Specification"), multiline: true },
    { key: "csr_ref", label: tx("standards.csr", "CSR reference") },
    { key: "default_formula_code", label: tx("standards.formula", "Default formula code") },
    { key: "is_active", label: tx("standards.active", "Active"), kind: "bool", editOnly: true },
  ];

  const load = useCallback(async () => {
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));
      if (tab === "rulesets") {
        const [sets, conv] = await Promise.all([listRuleSets(), listConventions()]);
        setRuleSets(sets);
        setConventions(conv);
      } else if (tab === "items") {
        setWorkItems(await listWorkItemsFull());
      }
      setError("");
    } catch (err) {
      setError(describeError(err, tx("standards.loadFailure", "Could not load this list.")));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function openReference(which: Ref) {
    if (ref === which) {
      setRef("");
      return;
    }
    setRef(which);
    setError("");
    try {
      if (which === "formulas" && formulas.length === 0) setFormulas(await listFormulas());
      if (which === "conventions" && conventions.length === 0) setConventions(await listConventions());
      if (which === "finish" && !finish) setFinish(await getFinishOptions());
    } catch (err) {
      setError(describeError(err, tx("standards.loadFailure", "Could not load this list.")));
    }
  }

  async function showResolved() {
    if (resolvedDate.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(resolvedDate.trim())) {
      setError(tx("standards.badDate", "Use a date like 2026-10-31."));
      return;
    }
    setBusy(true);
    setError("");
    try {
      setResolved(await getResolvedStandards(resolvedCode, resolvedDate));
    } catch (err) {
      setResolved(null);
      setError(describeError(err, tx("standards.resolveFailure", "Could not resolve the standards.")));
    } finally {
      setBusy(false);
    }
  }

  function beginAddRuleSet() {
    setAdding((open) => !open);
    setEditId("");
    setValues(toValues(ruleSetFields));
  }

  async function saveRuleSet() {
    const parsed = parseValues(ruleSetFields, values, { isNew: true, emptyAsNull: false, tx });
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await createRuleSetDraft(parsed.payload);
      setAdding(false);
      router.push({
        pathname: "/projects/[projectId]/rule-set",
        params: { projectId, ruleSetId: created.rule_set.id },
      });
    } catch (err) {
      setError(describeError(err, tx("standards.saveFailure", "Could not save.")));
    } finally {
      setBusy(false);
    }
  }

  function beginAddItem() {
    setAdding((open) => !open);
    setEditId("");
    setValues(toValues(itemFields, {}, { unit: "m3" }));
  }

  function beginEditItem(item: WorkItemFull) {
    setAdding(false);
    setEditId(item.id);
    setValues(toValues(itemFields, item as unknown as Record<string, unknown>));
  }

  async function saveItem() {
    const isNew = adding;
    const parsed = parseValues(itemFields, values, { isNew, emptyAsNull: false, tx });
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (isNew) await createWorkItem(parsed.payload);
      else await updateWorkItem(editId, parsed.payload);
      setAdding(false);
      setEditId("");
      await load();
    } catch (err) {
      setError(describeError(err, tx("standards.saveFailure", "Could not save.")));
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

  const q = search.trim().toLowerCase();
  const shownItems = workItems.filter(
    (item) => !q || item.code.toLowerCase().includes(q) || item.description.toLowerCase().includes(q),
  );

  const itemForm = (isNew: boolean) => (
    <View style={ui.panel}>
      <FieldsForm fields={itemFields} values={values} onChange={setValues} isNew={isNew} isUrdu={isUrdu} tx={tx} />
      <View style={[ui.row, isUrdu && ui.rtlRow]}>
        <Action title={tx("standards.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void saveItem()} />
        <Action title={tx("drawingsBoq.cancel", "Cancel")} secondary isUrdu={isUrdu} onPress={() => { setAdding(false); setEditId(""); }} />
      </View>
    </View>
  );

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("standards.back", "Back to drawings & BOQ")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("standards.title", "Standards & rules")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {(
            [
              ["rulesets", tx("standards.tabRuleSets", "Rule sets")],
              ["items", tx("standards.tabItems", "Work items")],
              ["reference", tx("standards.tabReference", "Reference")],
            ] as [Tab, string][]
          ).map(([value, label]) => (
            <Action key={value} title={label} secondary={tab !== value} isUrdu={isUrdu} onPress={() => { setTab(value); setAdding(false); setEditId(""); setError(""); }} />
          ))}
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {tab === "rulesets" ? (
          <>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("standards.ruleSetHelp", "A rule set decides how the engine measures: opening deductions, wastage, steel rules, IFC mappings, finishes and recipes. System rule sets are read-only; clone one to make your own.")}
            </Text>
            {canManage ? (
              <Action title={tx("standards.newRuleSet", "New rule set draft")} secondary={!adding} isUrdu={isUrdu} onPress={beginAddRuleSet} />
            ) : null}
            {adding ? (
              <View style={ui.panel}>
                <FieldsForm fields={ruleSetFields} values={values} onChange={setValues} isNew isUrdu={isUrdu} tx={tx} />
                <Action title={tx("standards.create", "Create draft")} disabled={busy} isUrdu={isUrdu} onPress={() => void saveRuleSet()} />
              </View>
            ) : null}
            {ruleSets.map((rs) => (
              <Pressable
                key={rs.id}
                style={ui.card}
                accessibilityRole="button"
                onPress={() => router.push({ pathname: "/projects/[projectId]/rule-set", params: { projectId, ruleSetId: rs.id } })}
              >
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${rs.code} v${rs.immutable_version} · ${rs.name}`}</Text>
                  <Badge label={rs.status} tone={tone(rs.status)} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[rs.standard_name, rs.standard_edition, rs.province, rs.convention_code, rs.is_system ? tx("standards.system", "System") : null].filter(Boolean).join(" · ")}
                </Text>
              </Pressable>
            ))}
            {ruleSets.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("standards.noRuleSets", "No rule sets found.")}</Text> : null}
          </>
        ) : null}

        {tab === "items" ? (
          <>
            <Field label={tx("standards.search", "Search by code or description")} value={search} onChangeText={setSearch} isUrdu={isUrdu} />
            {canManage ? (
              <Action title={tx("standards.newItem", "Add a work item")} secondary={!adding} isUrdu={isUrdu} onPress={beginAddItem} />
            ) : null}
            {adding ? itemForm(true) : null}
            {shownItems.length > SHOW_LIMIT ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("standards.firstN", "Showing the first {{count}} of {{total}}. Search to narrow the list.", { count: SHOW_LIMIT, total: shownItems.length })}
              </Text>
            ) : null}
            {shownItems.slice(0, SHOW_LIMIT).map((item) => (
              <View key={item.id} style={ui.boqItem}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${item.code} · ${item.unit}`}</Text>
                  {item.is_system ? <Badge label={tx("standards.system", "System")} tone="neutral" /> : null}
                  {!item.is_active ? <Badge label={tx("standards.inactive", "Inactive")} tone="warn" /> : null}
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[item.description, item.trade, item.default_formula_code].filter(Boolean).join(" · ")}
                </Text>
                {canManage && !item.is_system ? (
                  <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => beginEditItem(item)} />
                ) : null}
                {editId === item.id ? itemForm(false) : null}
              </View>
            ))}
          </>
        ) : null}

        {tab === "reference" ? (
          <>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Action title={tx("standards.formulas", "Formulas")} secondary={ref !== "formulas"} isUrdu={isUrdu} onPress={() => void openReference("formulas")} />
              <Action title={tx("standards.conventions", "Conventions")} secondary={ref !== "conventions"} isUrdu={isUrdu} onPress={() => void openReference("conventions")} />
              <Action title={tx("standards.finishOptions", "Finish options")} secondary={ref !== "finish"} isUrdu={isUrdu} onPress={() => void openReference("finish")} />
              <Action title={tx("standards.resolvedTitle", "Resolved standards")} secondary={ref !== "resolved"} isUrdu={isUrdu} onPress={() => void openReference("resolved")} />
            </View>

            {ref === "formulas"
              ? formulas.map((f) => (
                  <View key={f.code} style={ui.boqItem}>
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${f.code} → ${f.output_unit}`}</Text>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {[f.description, f.input_unit ? `${tx("standards.input", "input")} ${f.input_unit}` : null, f.needs_kernel ? tx("standards.needsKernel", "needs model geometry") : null].filter(Boolean).join(" · ")}
                    </Text>
                  </View>
                ))
              : null}

            {ref === "conventions"
              ? conventions.map((c) => (
                  <View key={c.id} style={ui.boqItem}>
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${c.code} · ${c.name}`}</Text>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {[c.description, c.conserves_volume ? tx("standards.conserves", "conserves volume") : null].filter(Boolean).join(" · ")}
                    </Text>
                    {Object.keys(c.parameters).length > 0 ? (
                      <Text style={[ui.muted, isUrdu && ui.rtlText]}>{JSON.stringify(c.parameters)}</Text>
                    ) : null}
                  </View>
                ))
              : null}

            {ref === "finish" && finish ? (
              <>
                {finish.surfaces.map((s) => (
                  <Text key={s.surface} style={[ui.muted, isUrdu && ui.rtlText]}>
                    {`${s.surface}: ${s.unit}${s.needs_height ? ` · ${tx("standards.needsHeight", "needs a height")}` : ""}`}
                  </Text>
                ))}
                <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("standards.categories", "Room categories")}</Text>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>{finish.categories.join(", ")}</Text>
              </>
            ) : null}

            {ref === "resolved" ? (
              <View style={ui.panel}>
                <Field label={tx("standards.resolvedCode", "Rule set code (blank = the active one)")} value={resolvedCode} onChangeText={setResolvedCode} isUrdu={isUrdu} />
                <Field label={tx("standards.resolvedDate", "As of (2026-10-31, optional)")} value={resolvedDate} onChangeText={setResolvedDate} isUrdu={isUrdu} />
                <Action title={tx("standards.show", "Show")} disabled={busy} isUrdu={isUrdu} onPress={() => void showResolved()} />
                {resolved ? (
                  <>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>{JSON.stringify(resolved, null, 2).slice(0, 6000)}</Text>
                    {JSON.stringify(resolved).length > 6000 ? (
                      <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("standards.truncated", "Only the first part is shown.")}</Text>
                    ) : null}
                  </>
                ) : null}
              </View>
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
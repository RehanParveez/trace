import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {cloneRuleSet, deleteRecipe, getRuleSet, listConventions, publishRuleSet, updateRuleSetDraft, validateRuleSet,
} from "../../../../api/standards";
import type {Convention, RuleRow, RuleSectionKey, RuleSetDetail, RuleValidation, RuleValidationIssue,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { FieldsForm, parseValues, toValues, type FieldSpec, type Values } from "../../../../features/drawingsBoq/formKit";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, InfoRow, ui } from "../../../../features/drawingsBoq/ui";

const PAGE = 10;
const SURFACES = ["FLOOR", "WALL", "CEILING", "SKIRTING", "DADO"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function severityTone(severity: string): "neutral" | "good" | "warn" | "bad" {
  if (severity === "error") return "bad";
  if (severity === "warning") return "warn";
  return "neutral";
}

export default function RuleSetScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; ruleSetId?: string }>();
  const projectId = first(params.projectId) ?? "";
  const ruleSetId = first(params.ruleSetId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [detail, setDetail] = useState<RuleSetDetail | null>(null);
  const [conventions, setConventions] = useState<Convention[]>([]);
  const [validation, setValidation] = useState<RuleValidation | null>(null);
  const [warnings, setWarnings] = useState<RuleValidationIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [headerOpen, setHeaderOpen] = useState(false);
  const [headerValues, setHeaderValues] = useState<Values>({});
  const [section, setSection] = useState<RuleSectionKey | "recipes" | "">("");
  const [page, setPage] = useState(1);
  const [editIndex, setEditIndex] = useState<number | null>(null); 
  const [rowValues, setRowValues] = useState<Values>({});

  const canManage = hasPerm(permissions, PERM.RULESET_MANAGE);
  const canPublish = hasPerm(permissions, PERM.RULESET_PUBLISH);
  const rs = detail?.rule_set;
  const editable = Boolean(canManage && rs && rs.status === "DRAFT" && !rs.is_system && rs.organization_id);

  const headerFields: FieldSpec[] = [
    { key: "name", label: tx("ruleSet.name", "Name"), required: true },
    { key: "description", label: tx("ruleSet.description", "Description") },
    { key: "jurisdiction", label: tx("ruleSet.jurisdiction", "Jurisdiction") },
    { key: "province", label: tx("ruleSet.province", "Province") },
    { key: "city", label: tx("ruleSet.city", "City") },
    { key: "standard_name", label: tx("ruleSet.standardName", "Standard") },
    { key: "standard_edition", label: tx("ruleSet.edition", "Edition") },
    { key: "effective_from", label: tx("ruleSet.from", "Effective from (2026-10-31)"), kind: "date" },
    { key: "effective_to", label: tx("ruleSet.to", "Effective to"), kind: "date" },
    { key: "convention_code", label: tx("ruleSet.convention", "Measurement convention"), kind: "choice", choices: conventions.map((c) => c.code) },
    { key: "wall_measurement_method", label: tx("ruleSet.wallMethod", "Wall measurement method") },
    { key: "net_vs_gross_preference", label: tx("ruleSet.netGross", "Net or gross"), kind: "choice", choices: ["net", "gross"] },
  ];

  const SECTIONS: { key: RuleSectionKey; title: string; fields: FieldSpec[]; defaults: Record<string, string> }[] = [
    {
      key: "opening_rules",
      title: tx("ruleSet.openings", "Opening rules"),
      defaults: { element_scope: "ALL", lower_area_m2: "0", deduction_behavior: "DEDUCT" },
      fields: [
        { key: "element_scope", label: tx("ruleSet.scope", "Applies to (ALL or an element type)"), required: true },
        { key: "lower_area_m2", label: tx("ruleSet.lowerArea", "Opening area from (m²)"), kind: "number", min: "nonneg", required: true },
        { key: "upper_area_m2", label: tx("ruleSet.upperArea", "Opening area up to (m², blank = no limit)"), kind: "number", min: "positive" },
        { key: "deduction_behavior", label: tx("ruleSet.behavior", "What to do"), kind: "choice", choices: ["DEDUCT", "IGNORE", "PARTIAL"], required: true },
        { key: "deduction_fraction", label: tx("ruleSet.fraction", "Fraction to deduct (0 to 1, for PARTIAL)"), kind: "number", min: "nonneg" },
        { key: "edge_behavior", label: tx("ruleSet.edge", "Edge behaviour (optional)") },
      ],
    },
    {
      key: "wastage_rules",
      title: tx("ruleSet.wastage", "Wastage rules"),
      defaults: { procurement_stage: "SITE", factor: "1.0" },
      fields: [
        { key: "material_class", label: tx("ruleSet.materialClass", "Material class (for example CONCRETE)"), required: true },
        { key: "procurement_stage", label: tx("ruleSet.stage", "Stage"), required: true },
        { key: "factor", label: tx("ruleSet.factor", "Factor (1.03 = 3% extra, between 1 and 2)"), kind: "number", min: "positive", required: true },
        { key: "unit", label: tx("ruleSet.unit", "Unit (optional)") },
        { key: "justification", label: tx("ruleSet.justification", "Reason (optional)") },
      ],
    },
    {
      key: "reinforcement_rules",
      title: tx("ruleSet.reinforcement", "Reinforcement rules"),
      defaults: { element_scope: "ALL", weight_tolerance_pct: "2.0", use_couplers: "false" },
      fields: [
        { key: "element_scope", label: tx("ruleSet.scope", "Applies to (ALL or an element type)"), required: true },
        { key: "bar_role", label: tx("ruleSet.barRole", "Bar role (for example MAIN)"), required: true },
        { key: "lap_basis", label: tx("ruleSet.lapBasis", "Lap basis") },
        { key: "lap_coefficient", label: tx("ruleSet.lapCoef", "Lap coefficient"), kind: "number", min: "nonneg" },
        { key: "dev_length_method", label: tx("ruleSet.devMethod", "Development length method") },
        { key: "stock_length_mm", label: tx("ruleSet.stock", "Stock length (mm)"), kind: "number", min: "positive" },
        { key: "cover_mm", label: tx("ruleSet.cover", "Cover (mm)"), kind: "number", min: "nonneg" },
        { key: "min_lap_mm", label: tx("ruleSet.minLap", "Minimum lap (mm)"), kind: "number", min: "nonneg" },
        { key: "use_couplers", label: tx("ruleSet.couplers", "Use couplers"), kind: "bool" },
        { key: "weight_tolerance_pct", label: tx("ruleSet.tolerance", "Weight tolerance (%)"), kind: "number", min: "nonneg", required: true },
      ],
    },
    {
      key: "mappings",
      title: tx("ruleSet.mappings", "IFC mappings"),
      defaults: { quantity_source_preference: "qto_first", confidence_base: "0.85" },
      fields: [
        { key: "ifc_type", label: tx("ruleSet.ifcType", "IFC type (for example IfcWall)"), required: true },
        { key: "work_item_code", label: tx("ruleSet.workItem", "Work item code") },
        { key: "default_category", label: tx("ruleSet.category", "Default category") },
        { key: "quantity_source_preference", label: tx("ruleSet.qtySource", "Quantity source"), required: true },
        { key: "unit_override", label: tx("ruleSet.unitOverride", "Unit override") },
        { key: "confidence_base", label: tx("ruleSet.confidence", "Base confidence (0 to 1)"), kind: "number", min: "nonneg", required: true },
      ],
    },
    {
      key: "finish_rules",
      title: tx("ruleSet.finishes", "Finish rules"),
      defaults: { space_category: "ALL", surface: "FLOOR", deduct_openings: "true", priority: "0", exclude: "false" },
      fields: [
        { key: "space_category", label: tx("ruleSet.spaceCategory", "Room category (ALL, BATHROOM, ...)"), required: true },
        { key: "surface", label: tx("ruleSet.surface", "Surface"), kind: "choice", choices: SURFACES, required: true },
        { key: "work_item_code", label: tx("ruleSet.workItem", "Work item code"), required: true },
        { key: "height_mm", label: tx("ruleSet.heightMm", "Height (mm, for walls, skirting, dado)"), kind: "number", min: "positive" },
        { key: "deduct_openings", label: tx("ruleSet.deductOpenings", "Deduct openings"), kind: "bool" },
        { key: "priority", label: tx("ruleSet.priority", "Priority"), kind: "number", min: "nonneg" },
        { key: "exclude", label: tx("ruleSet.exclude", "Remove this finish for the category"), kind: "bool" },
      ],
    },
  ];

  const active = SECTIONS.find((s) => s.key === section);
  const sectionRows: RuleRow[] = active && detail ? (detail[active.key] as RuleRow[]) : [];
  const pages = Math.max(1, Math.ceil(sectionRows.length / PAGE));

  const load = useCallback(async () => {
    if (!ruleSetId) {
      setError(tx("ruleSet.notFound", "Rule set not found."));
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
      const [result, conv] = await Promise.all([getRuleSet(ruleSetId), listConventions()]);
      setDetail(result);
      setConventions(conv);
      setError("");
    } catch (err) {
      setError(describeError(err, tx("ruleSet.loadFailure", "Could not load the rule set.")));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ruleSetId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(action: () => Promise<unknown>, done?: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      if (done) setNotice(done);
    } catch (err) {
      setError(describeError(err, tx("ruleSet.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  function openHeader() {
    if (!rs) return;
    setHeaderValues(toValues(headerFields, rs as unknown as Record<string, unknown>));
    setHeaderOpen((open) => !open);
  }

  async function saveHeader() {
    const parsed = parseValues(headerFields, headerValues, { isNew: false, emptyAsNull: false, tx });
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    await act(async () => {
      setDetail(await updateRuleSetDraft(ruleSetId!, parsed.payload));
      setHeaderOpen(false);
    }, tx("ruleSet.saved", "Saved."));
  }

  async function replaceSection(key: RuleSectionKey, rows: RuleRow[]) {
    await act(async () => {
      setDetail(await updateRuleSetDraft(ruleSetId!, { [key]: rows }));
      setEditIndex(null);
    }, tx("ruleSet.saved", "Saved."));
  }

  function beginRow(index: number) {
    if (!active) return;
    setEditIndex(index);
    setRowValues(
      index === -1
        ? toValues(active.fields, {}, active.defaults)
        : toValues(active.fields, sectionRows[index]),
    );
  }

  async function saveRow() {
    if (!active || editIndex === null) return;
    const parsed = parseValues(active.fields, rowValues, { isNew: editIndex === -1, emptyAsNull: true, tx });
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    const rows = [...sectionRows];
    if (editIndex === -1) rows.push(parsed.payload);
    else rows[editIndex] = { ...rows[editIndex], ...parsed.payload };
    await replaceSection(active.key, rows);
    if (editIndex === -1) setPage(Math.max(1, Math.ceil(rows.length / PAGE)));
  }

  function deleteRow(index: number) {
    if (!active) return;
    Alert.alert(tx("ruleSet.deleteRowTitle", "Delete this row?"), "", [
      { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
      {
        text: tx("ruleSet.delete", "Delete"),
        style: "destructive",
        onPress: () => void replaceSection(active.key, sectionRows.filter((_, i) => i !== index)),
      },
    ]);
  }

  function summary(row: RuleRow, fields: FieldSpec[]) {
    return fields
      .map((field) => {
        const value = row[field.key];
        if (value === null || value === undefined || value === "") return null;
        return `${field.key.replaceAll("_", " ")}: ${String(value)}`;
      })
      .filter(Boolean)
      .join(" · ");
  }

  async function handleClone() {
    if (!ruleSetId) return;
    setBusy(true);
    setError("");
    try {
      const copy = await cloneRuleSet(ruleSetId);
      router.replace({ pathname: "/projects/[projectId]/rule-set", params: { projectId, ruleSetId: copy.rule_set.id } });
    } catch (err) {
      setError(describeError(err, tx("ruleSet.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  async function handleValidate() {
    await act(async () => {
      setValidation(await validateRuleSet(ruleSetId!));
    });
  }

  function handlePublish() {
    Alert.alert(
      tx("ruleSet.publishTitle", "Publish this rule set?"),
      tx("ruleSet.publishBody", "It becomes locked. Changes after that need a new draft."),
      [
        { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
        {
          text: tx("ruleSet.publish", "Publish"),
          onPress: () =>
            void act(async () => {
              const result = await publishRuleSet(ruleSetId!);
              setWarnings(result.warnings);
              await load();
            }, tx("ruleSet.published", "Published.")),
        },
      ],
    );
  }

  function handleDeleteRecipe(recipeId: string) {
    Alert.alert(tx("ruleSet.deleteRecipeTitle", "Delete this recipe?"), "", [
      { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
      {
        text: tx("ruleSet.delete", "Delete"),
        style: "destructive",
        onPress: () =>
          void act(async () => {
            await deleteRecipe(ruleSetId!, recipeId);
            await load();
          }),
      },
    ]);
  }

  function openRecipe(recipeId?: string) {
    router.push({
      pathname: "/projects/[projectId]/recipe-edit",
      params: { projectId, ruleSetId: ruleSetId ?? "", recipeId: recipeId ?? "" },
    });
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const issueList = (issues: RuleValidationIssue[]) =>
    issues.map((issue, index) => (
      <View key={index} style={ui.boqItem}>
        <View style={[ui.heading, isUrdu && ui.rtlRow]}>
          <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{issue.code}</Text>
          <Badge label={issue.severity} tone={severityTone(issue.severity)} />
        </View>
        <Text style={[ui.muted, isUrdu && ui.rtlText]}>{issue.message}</Text>
        {issue.ref ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{issue.ref}</Text> : null}
      </View>
    ));

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("ruleSet.back", "Back to standards")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{rs ? `${rs.code} v${rs.immutable_version}` : ""}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}

        {rs ? (
          <>
            <View style={ui.summaryBox}>
              <InfoRow label={tx("ruleSet.name", "Name")} value={rs.name} isUrdu={isUrdu} />
              <InfoRow label={tx("ruleSet.status", "Status")} value={rs.is_system ? `${rs.status} · ${tx("standards.system", "System")}` : rs.status} isUrdu={isUrdu} />
              <InfoRow label={tx("ruleSet.standardName", "Standard")} value={[rs.standard_name, rs.standard_edition].filter(Boolean).join(" ") || "-"} isUrdu={isUrdu} />
              <InfoRow label={tx("ruleSet.convention", "Convention")} value={rs.convention_code ?? "-"} isUrdu={isUrdu} />
              <InfoRow label={tx("ruleSet.effective", "Effective")} value={`${rs.effective_from ?? "…"} → ${rs.effective_to ?? "…"}`} isUrdu={isUrdu} />
              <InfoRow label={tx("ruleSet.netGross", "Net or gross")} value={`${rs.net_vs_gross_preference} · ${rs.wall_measurement_method}`} isUrdu={isUrdu} />
            </View>

            {!editable ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {rs.is_system
                  ? tx("ruleSet.systemNote", "System rule set. Read only. Clone it to make your own draft.")
                  : rs.status !== "DRAFT"
                    ? tx("ruleSet.publishedNote", "Published rule sets are locked. Clone to start a new draft.")
                    : tx("ruleSet.noRights", "You can view this rule set but not change it.")}
              </Text>
            ) : null}

            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {canManage ? <Action title={tx("ruleSet.clone", "Clone to a new draft")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void handleClone()} /> : null}
              {canManage ? <Action title={tx("ruleSet.validate", "Validate")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => void handleValidate()} /> : null}
              {editable ? <Action title={tx("ruleSet.editHeader", "Edit details")} secondary={!headerOpen} isUrdu={isUrdu} onPress={openHeader} /> : null}
              {editable && canPublish ? <Action title={tx("ruleSet.publish", "Publish")} disabled={busy} isUrdu={isUrdu} onPress={handlePublish} /> : null}
            </View>

            {headerOpen ? (
              <View style={ui.panel}>
                <FieldsForm fields={headerFields} values={headerValues} onChange={setHeaderValues} isNew={false} isUrdu={isUrdu} tx={tx} />
                <Action title={tx("ruleSet.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void saveHeader()} />
              </View>
            ) : null}

            {validation ? (
              <View style={ui.panel}>
                <Badge label={validation.valid ? tx("ruleSet.valid", "Ready to publish") : tx("ruleSet.invalid", "Has errors")} tone={validation.valid ? "good" : "bad"} />
                {validation.issues.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("ruleSet.noIssues", "No issues found.")}</Text> : null}
                {issueList(validation.issues)}
              </View>
            ) : null}

            {warnings.length > 0 ? (
              <View style={ui.panel}>
                <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("ruleSet.publishWarnings", "Warnings at publish")}</Text>
                {issueList(warnings)}
              </View>
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("ruleSet.sections", "Rules")}</Text>
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {SECTIONS.map((s) => (
                <Action
                  key={s.key}
                  title={`${s.title} (${(detail![s.key] as RuleRow[]).length})`}
                  secondary={section !== s.key}
                  isUrdu={isUrdu}
                  onPress={() => { setSection(section === s.key ? "" : s.key); setPage(1); setEditIndex(null); }}
                />
              ))}
              <Action
                title={`${tx("ruleSet.recipes", "Recipes")} (${detail!.recipes.length})`}
                secondary={section !== "recipes"}
                isUrdu={isUrdu}
                onPress={() => { setSection(section === "recipes" ? "" : "recipes"); setEditIndex(null); }}
              />
            </View>

            {active ? (
              <>
                {editable ? <Action title={tx("ruleSet.addRow", "Add a row")} secondary={editIndex !== -1} isUrdu={isUrdu} onPress={() => beginRow(editIndex === -1 ? -2 : -1)} /> : null}
                {editIndex === -1 ? (
                  <View style={ui.panel}>
                    <FieldsForm fields={active.fields} values={rowValues} onChange={setRowValues} isNew isUrdu={isUrdu} tx={tx} />
                    <View style={[ui.row, isUrdu && ui.rtlRow]}>
                      <Action title={tx("ruleSet.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void saveRow()} />
                      <Action title={tx("drawingsBoq.cancel", "Cancel")} secondary isUrdu={isUrdu} onPress={() => setEditIndex(null)} />
                    </View>
                  </View>
                ) : null}
                {sectionRows.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("ruleSet.noRows", "No rows.")}</Text> : null}
                {sectionRows.slice((page - 1) * PAGE, page * PAGE).map((row, offset) => {
                  const index = (page - 1) * PAGE + offset;
                  return (
                    <View key={index} style={ui.boqItem}>
                      <Text style={[ui.muted, isUrdu && ui.rtlText]}>{summary(row, active.fields)}</Text>
                      {editable ? (
                        <View style={[ui.row, isUrdu && ui.rtlRow]}>
                          <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => beginRow(index)} />
                          <Action title={tx("ruleSet.delete", "Delete")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => deleteRow(index)} />
                        </View>
                      ) : null}
                      {editIndex === index ? (
                        <View style={ui.panel}>
                          <FieldsForm fields={active.fields} values={rowValues} onChange={setRowValues} isNew={false} isUrdu={isUrdu} tx={tx} />
                          <View style={[ui.row, isUrdu && ui.rtlRow]}>
                            <Action title={tx("ruleSet.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void saveRow()} />
                            <Action title={tx("drawingsBoq.cancel", "Cancel")} secondary isUrdu={isUrdu} onPress={() => setEditIndex(null)} />
                          </View>
                        </View>
                      ) : null}
                    </View>
                  );
                })}
                {sectionRows.length > PAGE ? (
                  <View style={[ui.pagination, isUrdu && ui.rtlRow]}>
                    <Action title={tx("drawingsBoq.previous", "Previous")} secondary disabled={page <= 1} isUrdu={isUrdu} onPress={() => setPage((p) => Math.max(1, p - 1))} />
                    <Text style={[ui.pageText, isUrdu && ui.rtlText]}>{`${page} / ${pages}`}</Text>
                    <Action title={tx("drawingsBoq.next", "Next")} secondary disabled={page >= pages} isUrdu={isUrdu} onPress={() => setPage((p) => Math.min(pages, p + 1))} />
                  </View>
                ) : null}
              </>
            ) : null}

            {section === "recipes" ? (
              <>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("ruleSet.recipeHelp", "A recipe turns one model element into several BOQ lines, for example a wall into brickwork, plaster and paint.")}
                </Text>
                {editable ? <Action title={tx("ruleSet.newRecipe", "New recipe")} secondary isUrdu={isUrdu} onPress={() => openRecipe()} /> : null}
                {detail!.recipes.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("ruleSet.noRecipes", "No recipes.")}</Text> : null}
                {detail!.recipes.map((recipe) => (
                  <View key={recipe.id} style={ui.boqItem}>
                    <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                      <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${recipe.code} · ${recipe.name}`}</Text>
                      {!recipe.is_active ? <Badge label={tx("standards.inactive", "Inactive")} tone="warn" /> : null}
                    </View>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>{`${tx("ruleSet.triggers", "Triggers")}: ${recipe.trigger_ifc_types.join(", ")}`}</Text>
                    {recipe.components.map((c, index) => (
                      <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>
                        {`${c.sequence}. ${c.description_template} · ${c.quantity_formula_code} → ${c.output_unit}${c.work_item_code ? ` · ${c.work_item_code}` : ""}${c.is_optional ? ` · ${tx("ruleSet.optional", "optional")}` : ""}`}
                      </Text>
                    ))}
                    {editable ? (
                      <View style={[ui.row, isUrdu && ui.rtlRow]}>
                        <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => openRecipe(recipe.id)} />
                        <Action title={tx("ruleSet.delete", "Delete")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => handleDeleteRecipe(recipe.id)} />
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
import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import {createBarSize, createLabourRate, createMaterial, createRebarShape, listBarSizes, listLabourRates, listMaterials, listRebarShapes, updateLabourRate, updateMaterial,
} from "../../../../api/libraries";
import type { BarSize, LabourRateEntry, MaterialEntry, RebarShape } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, formatMoney, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

type Tab = "materials" | "labour" | "sizes" | "shapes";
type Tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) => string;
type Values = Record<string, string>;
type Payload = Record<string, string | number>;

type FieldSpec = {
  key: string;
  label: string;
  required?: boolean;
  number?: "positive" | "nonneg";
  date?: boolean;
  createOnly?: boolean;
  multiline?: boolean;
};

type Row = { id: string; title: string; sub: string; badge?: string; values: Values };

const DATE = /^\d{4}-\d{2}-\d{2}$/;

// One add/edit list used by every tab.
function CrudSection(props: {
  fields: FieldSpec[];
  rows: Row[];
  canManage: boolean;
  addLabel: string;
  emptyText: string;
  onCreate: (payload: Payload) => Promise<void>;
  onUpdate?: (id: string, payload: Payload) => Promise<void>;
  isUrdu: boolean;
  tx: Tx;
}) {
  const { fields, rows, canManage, isUrdu, tx } = props;
  const [mode, setMode] = useState<"" | "add" | string>(""); // "", "add" or a row id
  const [values, setValues] = useState<Values>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function begin(next: string, initial: Values) {
    setMode(next);
    setValues(initial);
    setError("");
  }

  async function submit() {
    const editing = mode !== "add";
    const payload: Payload = {};
    for (const field of fields) {
      if (editing && field.createOnly) continue;
      const raw = (values[field.key] ?? "").trim();
      if (!raw) {
        if (field.required && !editing) {
          setError(tx("libraries.required", "Fill in: {{field}}", { field: field.label }));
          return;
        }
        continue;
      }
      if (field.number) {
        const n = Number(raw);
        if (!Number.isFinite(n) || (field.number === "positive" ? n <= 0 : n < 0)) {
          setError(tx("libraries.badNumber", "Enter a valid number in: {{field}}", { field: field.label }));
          return;
        }
        payload[field.key] = n;
      } else if (field.date) {
        if (!DATE.test(raw)) {
          setError(tx("libraries.badDate", "Use a date like 2026-10-31 in: {{field}}", { field: field.label }));
          return;
        }
        payload[field.key] = raw;
      } else {
        payload[field.key] = raw;
      }
    }
    setBusy(true);
    setError("");
    try {
      if (editing) await props.onUpdate!(mode, payload);
      else await props.onCreate(payload);
      setMode("");
    } catch (err) {
      setError(describeError(err, tx("libraries.saveFailure", "Could not save.")));
    } finally {
      setBusy(false);
    }
  }

  const form = (
    <View style={ui.panel}>
      {fields
        .filter((field) => !(mode !== "add" && field.createOnly))
        .map((field) => (
          <Field
            key={field.key}
            label={field.label}
            value={values[field.key] ?? ""}
            onChangeText={(v) => setValues((current) => ({ ...current, [field.key]: v }))}
            keyboardType={field.number ? "decimal-pad" : "default"}
            multiline={field.multiline}
            isUrdu={isUrdu}
          />
        ))}
      {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
      <View style={[ui.row, isUrdu && ui.rtlRow]}>
        <Action title={tx("libraries.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void submit()} />
        <Action title={tx("drawingsBoq.cancel", "Cancel")} secondary isUrdu={isUrdu} onPress={() => setMode("")} />
      </View>
    </View>
  );

  return (
    <>
      {canManage ? (
        <Action title={props.addLabel} secondary={mode !== "add"} isUrdu={isUrdu} onPress={() => (mode === "add" ? setMode("") : begin("add", {}))} />
      ) : null}
      {mode === "add" ? form : null}
      {rows.length === 0 ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{props.emptyText}</Text> : null}
      {rows.map((row) => (
        <View key={row.id} style={ui.boqItem}>
          <View style={[ui.heading, isUrdu && ui.rtlRow]}>
            <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{row.title}</Text>
            {row.badge ? <Badge label={row.badge} tone="neutral" /> : null}
          </View>
          {row.sub ? <Text style={[ui.muted, isUrdu && ui.rtlText]}>{row.sub}</Text> : null}
          {canManage && props.onUpdate ? (
            <Action title={tx("drawingsBoq.edit", "Edit")} secondary isUrdu={isUrdu} onPress={() => begin(row.id, row.values)} />
          ) : null}
          {mode === row.id ? form : null}
        </View>
      ))}
    </>
  );
}

export default function LibrariesScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";
  const tx: Tx = (key, defaultValue, vars) => t(key, { defaultValue, ...vars }) as string;

  const [permissions, setPermissions] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>("materials");
  const [materials, setMaterials] = useState<MaterialEntry[]>([]);
  const [labour, setLabour] = useState<LabourRateEntry[]>([]);
  const [sizes, setSizes] = useState<BarSize[]>([]);
  const [shapes, setShapes] = useState<RebarShape[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));
      if (tab === "materials") setMaterials(await listMaterials());
      else if (tab === "labour") setLabour(await listLabourRates());
      else if (tab === "sizes") setSizes(await listBarSizes());
      else setShapes(await listRebarShapes());
      setError("");
    } catch (err) {
      setError(describeError(err, tx("libraries.loadFailure", "Could not load this list.")));
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

  const str = (v: unknown) => (v == null ? "" : String(v));

  const materialFields: FieldSpec[] = [
    { key: "raw_text", label: tx("libraries.rawText", "Text as written on drawings"), required: true, createOnly: true },
    { key: "normalized_name", label: tx("libraries.normalized", "Standard name"), required: true },
    { key: "category", label: tx("libraries.category", "Category") },
    { key: "default_unit", label: tx("libraries.defaultUnit", "Default unit") },
    { key: "default_rate", label: tx("libraries.defaultRate", "Default rate"), number: "nonneg" },
    { key: "work_item_code", label: tx("libraries.workItem", "Work item code") },
    { key: "effective_from", label: tx("libraries.effective", "Effective from (2026-10-31)"), date: true },
  ];
  const labourFields: FieldSpec[] = [
    { key: "trade", label: tx("libraries.trade", "Trade"), required: true },
    { key: "unit", label: tx("libraries.unit", "Unit"), required: true },
    { key: "rate", label: tx("libraries.rate", "Rate"), required: true, number: "nonneg" },
    { key: "work_item_code", label: tx("libraries.workItem", "Work item code") },
    { key: "effective_from", label: tx("libraries.effective", "Effective from (2026-10-31)"), date: true },
  ];
  const sizeFields: FieldSpec[] = [
    { key: "standard", label: tx("libraries.standard", "Standard (for example ASTM A615)"), required: true },
    { key: "designation", label: tx("libraries.designation", "Designation (for example T12)"), required: true },
    { key: "grade", label: tx("libraries.grade", "Grade (blank = ALL)") },
    { key: "nominal_dia_mm", label: tx("libraries.dia", "Diameter (mm)"), required: true, number: "positive" },
    { key: "unit_weight_kg_m", label: tx("libraries.weight", "Weight (kg per metre)"), required: true, number: "positive" },
  ];
  const shapeFields: FieldSpec[] = [
    { key: "code", label: tx("libraries.shapeCode", "Shape code"), required: true },
    { key: "name", label: tx("libraries.shapeName", "Name"), required: true },
    { key: "standard", label: tx("libraries.standardOpt", "Standard (optional)") },
    { key: "segments", label: tx("libraries.segments", "Segment names, comma separated (for example A,B,C)"), required: true },
    { key: "hook_ends", label: tx("libraries.hooks", "Hooked ends (0, 1 or 2)"), number: "nonneg" },
    { key: "bend_spec", label: tx("libraries.bendSpec", "Bend details as a JSON list (advanced, optional)"), multiline: true },
    { key: "description", label: tx("libraries.description", "Description (optional)") },
  ];

  const canMaterials = hasPerm(permissions, PERM.MATERIAL_LIBRARY_MANAGE);
  const canLabour = hasPerm(permissions, PERM.LABOUR_RATE_MANAGE);
  const canRebar = hasPerm(permissions, PERM.RULESET_MANAGE);

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
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("libraries.back", "Back to drawings & BOQ")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("libraries.title", "Libraries & set-up")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          {(
            [
              ["materials", tx("libraries.tabMaterials", "Materials")],
              ["labour", tx("libraries.tabLabour", "Labour rates")],
              ["sizes", tx("libraries.tabSizes", "Bar sizes")],
              ["shapes", tx("libraries.tabShapes", "Bar shapes")],
            ] as [Tab, string][]
          ).map(([value, label]) => (
            <Action key={value} title={label} secondary={tab !== value} isUrdu={isUrdu} onPress={() => { setTab(value); setError(""); }} />
          ))}
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {tab === "materials" ? (
          <CrudSection
            key="materials"
            fields={materialFields}
            canManage={canMaterials}
            addLabel={tx("libraries.addMaterial", "Add a material")}
            emptyText={tx("libraries.noMaterials", "No materials in the library.")}
            isUrdu={isUrdu}
            tx={tx}
            rows={materials.map((m) => ({
              id: m.id,
              title: m.normalized_name,
              sub: [m.raw_text !== m.normalized_name ? `"${m.raw_text}"` : null, m.category, m.work_item_code, m.default_rate != null ? `${formatMoney(m.default_rate, locale, "-")} / ${m.default_unit ?? "-"}` : null].filter(Boolean).join(" · "),
              values: {
                normalized_name: m.normalized_name,
                category: str(m.category),
                default_unit: str(m.default_unit),
                default_rate: str(m.default_rate),
                work_item_code: str(m.work_item_code),
                effective_from: str(m.effective_from),
              },
            }))}
            onCreate={async (payload) => {
              await createMaterial(payload);
              await load();
            }}
            onUpdate={async (id, payload) => {
              await updateMaterial(id, payload);
              await load();
            }}
          />
        ) : null}

        {tab === "labour" ? (
          <CrudSection
            key="labour"
            fields={labourFields}
            canManage={canLabour}
            addLabel={tx("libraries.addLabour", "Add a labour rate")}
            emptyText={tx("libraries.noLabour", "No labour rates.")}
            isUrdu={isUrdu}
            tx={tx}
            rows={labour.map((l) => ({
              id: l.id,
              title: `${l.trade} · ${formatMoney(l.rate, locale, "-")} / ${l.unit}`,
              sub: [l.work_item_code, l.effective_from ? `${tx("libraries.from", "from")} ${l.effective_from}` : null].filter(Boolean).join(" · "),
              values: {
                trade: l.trade,
                unit: l.unit,
                rate: str(l.rate),
                work_item_code: str(l.work_item_code),
                effective_from: str(l.effective_from),
              },
            }))}
            onCreate={async (payload) => {
              await createLabourRate(payload);
              await load();
            }}
            onUpdate={async (id, payload) => {
              await updateLabourRate(id, payload);
              await load();
            }}
          />
        ) : null}

        {tab === "sizes" ? (
          <CrudSection
            key="sizes"
            fields={sizeFields}
            canManage={canRebar}
            addLabel={tx("libraries.addSize", "Add a bar size")}
            emptyText={tx("libraries.noSizes", "No bar sizes.")}
            isUrdu={isUrdu}
            tx={tx}
            rows={sizes.map((s) => ({
              id: s.id,
              title: `${s.designation} · ${formatNumber(s.nominal_dia_mm, 2)} mm`,
              sub: `${s.standard} · ${s.grade} · ${formatNumber(s.unit_weight_kg_m, 4)} kg/m${s.is_active ? "" : ` · ${tx("libraries.inactive", "inactive")}`}`,
              badge: s.is_system ? tx("libraries.system", "System") : undefined,
              values: {},
            }))}
            onCreate={async (payload) => {
              await createBarSize(payload);
              await load();
            }}
          />
        ) : null}

        {tab === "shapes" ? (
          <CrudSection
            key="shapes"
            fields={shapeFields}
            canManage={canRebar}
            addLabel={tx("libraries.addShape", "Add a bar shape")}
            emptyText={tx("libraries.noShapes", "No bar shapes.")}
            isUrdu={isUrdu}
            tx={tx}
            rows={shapes.map((s) => ({
              id: s.id,
              title: `${s.code} · ${s.name}`,
              sub: `${tx("libraries.segmentsList", "segments")}: ${s.segments.join(", ")} · ${tx("libraries.bends", "{{count}} bends", { count: s.bend_count })} · ${tx("libraries.hookEnds", "{{count}} hooked ends", { count: s.hook_ends })}`,
              badge: s.is_system ? tx("libraries.system", "System") : undefined,
              values: {},
            }))}
            onCreate={async (payload) => {
              const segments = String(payload.segments ?? "")
                .split(",")
                .map((part) => part.trim())
                .filter(Boolean);
              let bendSpec: unknown[] = [];
              if (payload.bend_spec) {
                try {
                  const parsed = JSON.parse(String(payload.bend_spec));
                  if (!Array.isArray(parsed)) throw new Error("not a list");
                  bendSpec = parsed;
                } catch {
                  throw new Error(tx("libraries.badJson", "Bend details must be a valid JSON list, for example []."));
                }
              }
              await createRebarShape({
                code: payload.code,
                name: payload.name,
                standard: payload.standard,
                description: payload.description,
                segments,
                bend_spec: bendSpec,
                hook_ends: Math.round(Number(payload.hook_ends ?? 0)),
              });
              await load();
            }}
          />
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
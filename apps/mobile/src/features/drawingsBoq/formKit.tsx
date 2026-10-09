import { Text, View } from "react-native";
import { Action, Field, ui } from "./ui";

export type Tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) => string;
export type FieldKind = "text" | "number" | "bool" | "choice" | "date";
export type Values = Record<string, string>;

export type FieldSpec = {
  key: string;
  label: string;
  kind?: FieldKind;
  min?: "positive" | "nonneg";
  choices?: string[];
  required?: boolean;
  createOnly?: boolean;
  editOnly?: boolean;
  multiline?: boolean;
};

const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function toValues(
  fields: FieldSpec[],
  source: Record<string, unknown> = {},
  defaults: Record<string, string> = {},
): Values {
  const out: Values = {};
  for (const field of fields) {
    const raw = source[field.key];
    if (raw === undefined || raw === null) {
      out[field.key] = defaults[field.key] ?? (field.kind === "bool" ? "false" : "");
    } else {
      out[field.key] = String(raw);
    }
  }
  return out;
}

export function parseValues(
  fields: FieldSpec[],
  values: Values,
  options: { isNew: boolean; emptyAsNull: boolean; tx: Tx },
): { payload: Record<string, unknown> } | { error: string } {
  const { isNew, emptyAsNull, tx } = options;
  const payload: Record<string, unknown> = {};
  for (const field of fields) {
    if (isNew && field.editOnly) continue;
    if (!isNew && field.createOnly) continue;
    const kind = field.kind ?? "text";
    const raw = (values[field.key] ?? "").trim();

    if (kind === "bool") {
      payload[field.key] = raw === "true";
      continue;
    }
    if (raw === "") {
      if (field.required) {
        return { error: tx("formKit.required", "Fill in: {{field}}", { field: field.label }) };
      }
      if (emptyAsNull) payload[field.key] = null;
      continue;
    }
    if (kind === "number") {
      const n = Number(raw.replace(/,/g, ""));
      const bad = !Number.isFinite(n) || (field.min === "positive" ? n <= 0 : n < 0);
      if (bad) {
        return { error: tx("formKit.badNumber", "Enter a valid number in: {{field}}", { field: field.label }) };
      }
      payload[field.key] = n;
    } else if (kind === "date") {
      if (!DATE.test(raw)) {
        return { error: tx("formKit.badDate", "Use a date like 2026-10-31 in: {{field}}", { field: field.label }) };
      }
      payload[field.key] = raw;
    } else {
      payload[field.key] = raw;
    }
  }
  return { payload };
}

export function FieldsForm(props: {
  fields: FieldSpec[];
  values: Values;
  onChange: (values: Values) => void;
  isNew: boolean;
  isUrdu: boolean;
  tx: Tx;
}) {
  const { fields, values, onChange, isNew, isUrdu, tx } = props;
  const set = (key: string, value: string) => onChange({ ...values, [key]: value });

  return (
    <>
      {fields
        .filter((field) => !(isNew && field.editOnly) && !(!isNew && field.createOnly))
        .map((field) => {
          const kind = field.kind ?? "text";
          if (kind === "bool") {
            const on = values[field.key] === "true";
            return (
              <View key={field.key}>
                <Text style={[ui.label, isUrdu && ui.rtlText]}>{field.label}</Text>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  <Action title={tx("formKit.yes", "Yes")} secondary={!on} isUrdu={isUrdu} onPress={() => set(field.key, "true")} />
                  <Action title={tx("formKit.no", "No")} secondary={on} isUrdu={isUrdu} onPress={() => set(field.key, "false")} />
                </View>
              </View>
            );
          }
          if (kind === "choice") {
            return (
              <View key={field.key}>
                <Text style={[ui.label, isUrdu && ui.rtlText]}>{field.label}</Text>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  {(field.choices ?? []).map((choice) => (
                    <Action key={choice} title={choice} secondary={values[field.key] !== choice} isUrdu={isUrdu} onPress={() => set(field.key, choice)} />
                  ))}
                </View>
              </View>
            );
          }
          return (
            <Field
              key={field.key}
              label={field.label}
              value={values[field.key] ?? ""}
              onChangeText={(value) => set(field.key, value)}
              keyboardType={kind === "number" ? "decimal-pad" : "default"}
              multiline={field.multiline}
              isUrdu={isUrdu}
            />
          );
        })}
    </>
  );
}
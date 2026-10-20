import { useTranslation } from "react-i18next";
import { DERIVED_FIELDS, mmToInches, paramSourceView, parseDerivedField } from "../utils/derived";
import type { DerivedInput, PrintedNotes } from "../utils/derived";
import type { DerivedParamName } from "../types/drawings-boq.types";
import { qsFlagText } from "../utils/qsReadings";
import { useQsProposed } from "../hooks/useProposed";
import { proposedParamText } from "../utils/qsProposed";
import { ProposedAnswersPanel } from "./ProposedAnswersPanel";

interface DerivedParamsFormProps {
  value: DerivedInput;
  onChange: (next: DerivedInput) => void;
  disabled?: boolean;
  onSave?: () => void;
  printed?: PrintedNotes;
  conflicts?: { param: string; values: { value_mm: number; text?: string | null; pages?: number[] }[] }[];
  lapTable?: Record<string, number>;
  qs?: Partial<Record<DerivedParamName, number>>;
  saving?: boolean;
}

export function DerivedParamsForm({ value, onChange, disabled = false, onSave, saving = false, printed = {}, conflicts = [], lapTable = {}, qs }: DerivedParamsFormProps) {
  const { t } = useTranslation();
  const { data: proposedSet } = useQsProposed();
  return (
     <details className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
      <summary className="cursor-pointer text-[12px] font-semibold text-[var(--color-text-primary)]">
        {t("boq.derived.formTitle", "Site assumptions for below-ground works, formwork and steel")}
      </summary>
      <p className="mt-2 text-[11px] leading-snug text-[var(--color-text-muted)]">
        {t(
          "boq.derived.formHint",
          "Used when the run works out excavation, PCC and backfill from the footings, and formwork and steel for the concrete read from a drawing. Leave a box empty to use the standard value; the result is then marked as assumed.",
        )}
      </p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {DERIVED_FIELDS.map((def) => {
          const parsed = parseDerivedField(value[def.key], def);
          const src = paramSourceView(def, value[def.key], printed);
          const standard =
            def.flag
              ? qs?.[def.key] !== undefined
                ? t("boq.derived.flagQs", { defaultValue: "Empty: {{v}}, as the QS gave it", v: qsFlagText(qs?.[def.key]) })
                : t("boq.derived.flagStandard", "Empty: standard choice")
              : def.asked
              ? t("boq.derived.askedStandard", "Empty: footings read from a drawing are not dug until this is given")
              : def.unit === "pct"
              ? t("boq.derived.standardPct", { defaultValue: "Standard {{n}} percent: the bare weight", n: def.defaultMm })
              : def.unit === "dia"
              ? t("boq.derived.standardDia", { defaultValue: "Standard {{n}} bar diameters", n: def.defaultMm })
              : def.defaultMm === null
              ? t("boq.derived.nglStandard", "Empty: the model's zero level is taken as ground")
              : t("boq.derived.standard", {
                  defaultValue: "Standard {{mm}} mm (about {{in}} in)",
                  mm: def.defaultMm,
                  in: mmToInches(def.defaultMm),
                });
          return (
            <label key={def.key} className="block">
              <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                {t(`boq.derived.param.${def.key}`, def.label ?? def.key)}
              </span>
              {def.flag ? (
                <select
                  value={value[def.key] ?? ""}
                  disabled={disabled}
                  onChange={(event) => onChange({ ...value, [def.key]: event.target.value })}
                  className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]"
                >
                  <option value="">{t("boq.derived.flag.standard", "Standard")}</option>
                  <option value="0">{t(`boq.derived.flag.${def.key}.0`, "No")}</option>
                  <option value="1">{t(`boq.derived.flag.${def.key}.1`, "Yes")}</option>
                </select>
              ) : (
                <input
                  value={value[def.key] ?? ""}
                  disabled={disabled}
                  inputMode="decimal"
                  placeholder={src.source === "default" ? (def.defaultMm === null ? "" : String(def.defaultMm)) : String(src.value ?? "")}
                  onChange={(event) => onChange({ ...value, [def.key]: event.target.value })}
                  className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 font-mono text-[12px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]"
                />
              )}
              {parsed.error ? (
                <span className="mt-1 block text-[11px] text-[var(--color-danger)]">
                  {parsed.error === "NOT_A_NUMBER"
                    ? t("boq.derived.error.NOT_A_NUMBER", "Enter a number")
                    : t("boq.derived.error.OUT_OF_RANGE", {
                        defaultValue: "Enter a value from {{min}} to {{max}}",
                        min: def.min,
                        max: def.max,
                      })}
                </span>
              ) : (
                <span className="mt-1 block text-[11px] text-[var(--color-text-muted)]" data-testid={`param-source-${def.key}`} data-source={src.source}>
                  {src.source === "drawing"
                    ? t("boq.derived.fromDrawing", {
                        defaultValue: "From the drawing: {{value}}{{note}}{{pages}}",
                        value: src.value,
                        note: src.text ? ` (${src.text})` : "",
                        pages: src.pages.length > 0 ? `, page ${src.pages.join(", ")}` : "",
                      })
                    : src.source === "qs"
                    ? t("boq.derived.fromQs", { defaultValue: "From the QS answer: {{value}}", value: src.value })
                    : src.source === "default" && proposedParamText(def.key, proposedSet, { flag: def.flag, unit: def.unit })
                    ? proposedParamText(def.key, proposedSet, { flag: def.flag, unit: def.unit })
                    : def.hint && src.source === "default"
                    ? def.hint
                    : standard}
                </span>
              )}
            </label>
          );
        })}
      </div>
      {conflicts.length > 0 ? (
        <div className="mt-3 rounded-[8px] border border-[var(--color-warning)] px-3 py-2 text-[11px] text-[var(--color-text-secondary)]" data-testid="param-conflicts">
          <div className="font-semibold">{t("boq.derived.conflictsTitle", "The drawings print different values, so none is used")}</div>
          <ul className="mt-1 space-y-0.5">
            {conflicts.map((c) => (
              <li key={c.param}>
                {t(`boq.derived.param.${c.param}`, c.param)}: {c.values.map((v) => `${v.value_mm} mm${v.pages && v.pages.length > 0 ? ` (page ${v.pages.join(", ")})` : ""}`).join(" / ")}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {Object.keys(lapTable).length > 0 ? (
        <p className="mt-3 text-[11px] text-[var(--color-text-muted)]" data-testid="param-lap-table">
          {t("boq.derived.lapTable", "Lap lengths printed on the drawing")}: {Object.entries(lapTable).map(([bar, mm]) => `#${bar} = ${mm} mm`).join(", ")}
        </p>
      ) : null}
      <ProposedAnswersPanel />
      {onSave ? (
        <div className="mt-3 flex items-center gap-3">
          <button
            type="button"
            disabled={disabled || saving}
            onClick={onSave}
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[12px] font-semibold text-[var(--color-text-primary)] disabled:opacity-50"
          >
            {saving ? t("boq.derived.saving", "Saving...") : t("boq.derived.saveDefaults", "Save as this project's defaults")}
          </button>
          <span className="text-[11px] text-[var(--color-text-muted)]">
            {t("boq.derived.saveHint", "Saved values fill these boxes the next time you open this project. An empty box goes back to the standard value.")}
          </span>
        </div>
      ) : null}
    </details>
  );
}

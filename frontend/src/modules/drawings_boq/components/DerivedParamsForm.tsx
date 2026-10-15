import { useTranslation } from "react-i18next";
import { DERIVED_FIELDS, mmToInches, parseDerivedField } from "../utils/derived";
import type { DerivedInput } from "../utils/derived";

interface DerivedParamsFormProps {
  value: DerivedInput;
  onChange: (next: DerivedInput) => void;
  disabled?: boolean;
  onSave?: () => void;
  saving?: boolean;
}

export function DerivedParamsForm({ value, onChange, disabled = false, onSave, saving = false }: DerivedParamsFormProps) {
  const { t } = useTranslation();
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
          const standard =
            def.flag
              ? t("boq.derived.flagStandard", "Empty: standard choice")
              : def.asked
              ? t("boq.derived.askedStandard", "Empty: footings read from a drawing are not dug until this is given")
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
                {t(`boq.derived.param.${def.key}`, def.key)}
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
                  placeholder={def.defaultMm === null ? "" : String(def.defaultMm)}
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
                <span className="mt-1 block text-[11px] text-[var(--color-text-muted)]">{standard}</span>
              )}
            </label>
          );
        })}
      </div>
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

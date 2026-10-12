import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Field, inputClass } from "../../../organizations/components/OrganizationUi";
import { useWorkItems } from "../../standards/hooks";
import type { MeasureKind, ModeOption, ReconMode } from "../types/takeoff.types";
import {DIMENSION_FIELDS, DIMENSION_LABEL, RECON_HELP, RESERVED_WORK_ITEMS, modeOption, modesFor, supportsOpenings,
} from "../utils/measureForm";
import type { MeasureFormValue } from "../utils/measureForm";

interface Props {
  kind: MeasureKind;
  value: MeasureFormValue;
  onChange: (next: MeasureFormValue) => void;
  modes: ModeOption[] | undefined;
  disabled?: boolean;
}

const MODE_TEXT: Record<string, string> = {
  DIRECT: "Direct (as drawn)",
  LENGTH_X_HEIGHT: "Length × height (area)",
  LENGTH_X_HEIGHT_X_THICKNESS: "Length × height × thickness (volume)",
  LENGTH_X_SECTION: "Length × section (volume)",
  AREA_X_THICKNESS: "Area × thickness (volume)",
  COUNT_X_LENGTH: "Count × length",
  COUNT_X_AREA: "Count × area",
  COUNT_X_VOLUME: "Count × volume",
};

export function MeasureForm({ kind, value, onChange, modes, disabled }: Props) {
  const { t } = useTranslation();
  const workItems = useWorkItems();
  const options = modesFor(modes, kind);
  const current = modeOption(modes, kind, value.quantity_mode);
  const required = current?.required_params ?? [];

  const items = useMemo(
    () => (workItems.data ?? []).filter((w) => w.is_active && !RESERVED_WORK_ITEMS.includes(w.code)).sort((a, b) => a.code.localeCompare(b.code)),
    [workItems.data],
  );
  const chosen = items.find((w) => w.code === value.work_item_code.trim());
  const reserved = RESERVED_WORK_ITEMS.includes(value.work_item_code.trim().toUpperCase());
  const unitMismatch = Boolean(chosen && current && chosen.unit && chosen.unit.toLowerCase() !== current.output_unit.toLowerCase());

  const set = (patch: Partial<MeasureFormValue>) => onChange({ ...value, ...patch });

  return (
    <div className="space-y-3" data-testid="measure-form">
      <Field label={t("boq.takeoff.form.mode", "How to measure")}>
        <select className={inputClass} value={value.quantity_mode} disabled={disabled} onChange={(e) => set({ quantity_mode: e.target.value })}>
          {options.map((o) => (
            <option key={o.quantity_mode} value={o.quantity_mode}>
              {MODE_TEXT[o.quantity_mode] ?? o.quantity_mode} → {o.output_unit}
            </option>
          ))}
        </select>
      </Field>

      <Field
        label={t("boq.takeoff.form.workItem", "Work item")}
        error={reserved ? t("boq.takeoff.err.reserved", "Steel items are measured from the model and cannot be used here.") : unitMismatch
          ? t("boq.takeoff.err.unitMismatch", "This work item is measured in {{unit}} but this way of measuring gives {{out}}. Pick another mode or work item.", { unit: chosen?.unit, out: current?.output_unit })
          : undefined}
        hint={chosen ? `${chosen.description} · ${chosen.unit}` : t("boq.takeoff.form.workItemHint", "Needed to confirm. You can save a draft without it.")}
      >
        <input
          className={inputClass}
          list="takeoff-work-items"
          value={value.work_item_code}
          disabled={disabled}
          placeholder="e.g. CON-RCC"
          onChange={(e) => set({ work_item_code: e.target.value.toUpperCase() })}
        />
        <datalist id="takeoff-work-items">
          {items.map((w) => (
            <option key={w.id} value={w.code}>{`${w.description} (${w.unit})`}</option>
          ))}
        </datalist>
      </Field>

      {required.length > 0 ? (
        <div className="grid grid-cols-2 gap-3">
          {DIMENSION_FIELDS.filter((f) => required.includes(f)).map((f) => (
            <Field key={f} label={`${DIMENSION_LABEL[f]} (mm)`} hint={t("boq.takeoff.form.lengthHint", "3000, 3m or 10ft 6in")}>
              <input
                className={inputClass}
                value={value.dims[f]}
                disabled={disabled}
                inputMode="decimal"
                data-testid={`dim-${f}`}
                onChange={(e) => set({ dims: { ...value.dims, [f]: e.target.value } })}
              />
            </Field>
          ))}
          <div className="col-span-2">
            <Field label={t("boq.takeoff.form.basis", "Where do these sizes come from?")}>
              <select className={inputClass} value={value.dims_basis} disabled={disabled} onChange={(e) => set({ dims_basis: e.target.value as MeasureFormValue["dims_basis"] })}>
                <option value="SPECIFIED">{t("boq.takeoff.form.basisSpecified", "Specification / schedule")}</option>
                <option value="DRAWN">{t("boq.takeoff.form.basisDrawn", "Read from the drawing")}</option>
                <option value="ASSUMED">{t("boq.takeoff.form.basisAssumed", "Assumed (flags a review issue)")}</option>
              </select>
            </Field>
          </div>
        </div>
      ) : null}

      {supportsOpenings(value.quantity_mode) ? (
        <div className="rounded-[8px] border border-[var(--color-border)] p-3">
          <div className="mb-2 flex items-center justify-between text-[12px] font-semibold text-[var(--color-text-secondary)]">
            {t("boq.takeoff.form.openings", "Openings to deduct")}
            <button
              type="button"
              className="text-[var(--color-info)]"
              disabled={disabled}
              onClick={() => set({ openings: [...value.openings, { role: "DOOR", width: "", height: "", nos: "1", label: "" }] })}
            >
              + {t("boq.takeoff.form.add", "Add")}
            </button>
          </div>
          {value.openings.map((o, i) => (
            <div key={i} className="mb-2 grid grid-cols-[84px_1fr_1fr_52px_24px] items-center gap-1.5">
              <select className={inputClass} value={o.role} onChange={(e) => set({ openings: value.openings.map((x, j) => (j === i ? { ...x, role: e.target.value as typeof o.role } : x)) })}>
                <option value="DOOR">Door</option>
                <option value="WINDOW">Window</option>
                <option value="OPENING">Opening</option>
              </select>
              <input className={inputClass} placeholder="width" value={o.width} onChange={(e) => set({ openings: value.openings.map((x, j) => (j === i ? { ...x, width: e.target.value } : x)) })} />
              <input className={inputClass} placeholder="height" value={o.height} onChange={(e) => set({ openings: value.openings.map((x, j) => (j === i ? { ...x, height: e.target.value } : x)) })} />
              <input className={inputClass} placeholder="nos" value={o.nos} onChange={(e) => set({ openings: value.openings.map((x, j) => (j === i ? { ...x, nos: e.target.value } : x)) })} />
              <button type="button" aria-label="Remove opening" className="text-[var(--color-danger)]" onClick={() => set({ openings: value.openings.filter((_, j) => j !== i) })}>×</button>
            </div>
          ))}
        </div>
      ) : null}

      <div className="rounded-[8px] border border-[var(--color-border)] p-3">
        <div className="mb-2 flex items-center justify-between text-[12px] font-semibold text-[var(--color-text-secondary)]">
          {t("boq.takeoff.form.adjustments", "Adjustments (in the result unit)")}
          <button type="button" className="text-[var(--color-info)]" disabled={disabled} onClick={() => set({ adjustments: [...value.adjustments, { op: "LESS", value: "", label: "" }] })}>
            + {t("boq.takeoff.form.add", "Add")}
          </button>
        </div>
        {value.adjustments.map((a, i) => (
          <div key={i} className="mb-2 grid grid-cols-[76px_1fr_1.4fr_24px] items-center gap-1.5">
            <select className={inputClass} value={a.op} onChange={(e) => set({ adjustments: value.adjustments.map((x, j) => (j === i ? { ...x, op: e.target.value as "LESS" | "ADD" } : x)) })}>
              <option value="LESS">Less</option>
              <option value="ADD">Add</option>
            </select>
            <input className={inputClass} placeholder="amount" value={a.value} onChange={(e) => set({ adjustments: value.adjustments.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)) })} />
            <input className={inputClass} placeholder="why" value={a.label} onChange={(e) => set({ adjustments: value.adjustments.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)) })} />
            <button type="button" aria-label="Remove adjustment" className="text-[var(--color-danger)]" onClick={() => set({ adjustments: value.adjustments.filter((_, j) => j !== i) })}>×</button>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label={t("boq.takeoff.form.label", "Label")}>
          <input className={inputClass} value={value.label} disabled={disabled} onChange={(e) => set({ label: e.target.value })} />
        </Field>
        <Field label={t("boq.takeoff.form.tag", "Tag")}>
          <input className={inputClass} value={value.tag} disabled={disabled} onChange={(e) => set({ tag: e.target.value })} />
        </Field>
        <Field label={t("boq.takeoff.form.grade", "Material grade")}>
          <input className={inputClass} value={value.material_grade} disabled={disabled} onChange={(e) => set({ material_grade: e.target.value })} />
        </Field>
        <Field label={t("boq.takeoff.form.repeat", "Repeat (× floors / units)")}>
          <input className={inputClass} value={value.repeat} disabled={disabled} inputMode="numeric" onChange={(e) => set({ repeat: e.target.value })} />
        </Field>
      </div>

      <Field label={t("boq.takeoff.form.recon", "If the model already measures this")} hint={RECON_HELP[value.recon_mode]}>
        <select className={inputClass} value={value.recon_mode} disabled={disabled} onChange={(e) => set({ recon_mode: e.target.value as ReconMode })}>
          <option value="AUTO">{t("boq.takeoff.recon.auto", "Automatic (verify the model)")}</option>
          <option value="ADD">{t("boq.takeoff.recon.add", "Add to the model")}</option>
          <option value="REPLACE_MODEL">{t("boq.takeoff.recon.replace", "Replace the model")}</option>
          <option value="VERIFY_ONLY">{t("boq.takeoff.recon.verify", "Verify only")}</option>
        </select>
      </Field>
    </div>
  );
}

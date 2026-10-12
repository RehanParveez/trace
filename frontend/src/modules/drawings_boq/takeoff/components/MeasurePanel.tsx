import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import type { PreviewState } from "../hooks/useLivePreview";
import type { MeasureKind, ModeOption } from "../types/takeoff.types";
import type { MeasureFormValue } from "../utils/measureForm";
import { MeasureForm } from "./MeasureForm";
import { PreviewCard } from "./PreviewCard";

interface Props {
  kind: MeasureKind | null;
  editingLabel: string | null;
  form: MeasureFormValue;
  onForm: (v: MeasureFormValue) => void;
  modes: ModeOption[] | undefined;
  preview: PreviewState;
  geometryHint: string | null;
  formErrors: string[];
  pointCount: number;
  originNote: string | null;
  blockedReason: string | null;
  saving: boolean;
  canEdit: boolean;
  onSave: (confirm: boolean) => void;
  onCancel: () => void;
  onAddHole?: () => void;
  onFinishHole?: () => void;
  drawingHole?: boolean;
  onToggleClosed?: () => void;
  closed?: boolean;
}

export function MeasurePanel(p: Props) {
  const { t } = useTranslation();
  if (!p.kind) {
    return (
      <div className="p-4 text-[13px] text-[var(--color-text-secondary)]">
        {t("boq.takeoff.measure.pickTool", "Choose Length (L), Area (A) or Count (C) in the toolbar, or pick a wall (W) or room (P), then click on the drawing.")}
      </div>
    );
  }
  const disabled = !p.canEdit;
  return (
    <div className="space-y-3 p-4" data-testid="measure-panel">
      <div className="flex items-center gap-2">
        <Badge tone="gold">{p.kind}</Badge>
        {p.editingLabel ? <span className="text-[12px] font-semibold text-[var(--color-text-secondary)]">{t("boq.takeoff.measure.editing", "Editing")} {p.editingLabel}</span> : null}
        {p.pointCount > 0 ? <span className="ml-auto text-[12px] text-[var(--color-text-muted)]">{p.pointCount} {t("boq.takeoff.measure.points", "points")}</span> : null}
      </div>
      {p.originNote ? <div className="rounded-[7px] bg-[var(--color-info-bg)] px-2.5 py-1.5 text-[12px] text-[var(--color-info)]">{p.originNote}</div> : null}
      {p.blockedReason ? <div className="rounded-[7px] bg-[var(--color-danger-bg)] px-2.5 py-1.5 text-[12px] text-[var(--color-danger)]">{p.blockedReason}</div> : null}

      {p.kind === "LENGTH" && !p.editingLabel ? (
        <label className="flex items-center gap-2 text-[12.5px] text-[var(--color-text-secondary)]">
          <input type="checkbox" checked={Boolean(p.closed)} onChange={p.onToggleClosed} /> {t("boq.takeoff.measure.closed", "Close the line into a loop")}
        </label>
      ) : null}
      {p.kind === "AREA" && !p.editingLabel ? (
        <div className="flex gap-2">
          {p.drawingHole ? (
            <Button size="sm" onClick={p.onFinishHole}>{t("boq.takeoff.measure.finishHole", "Finish hole")}</Button>
          ) : (
            <Button size="sm" onClick={p.onAddHole} disabled={p.pointCount < 3}>{t("boq.takeoff.measure.addHole", "Cut a hole (H)")}</Button>
          )}
        </div>
      ) : null}

      <PreviewCard state={p.preview} hint={p.geometryHint} />

      {p.formErrors.length > 0 ? (
        <ul className="space-y-1 text-[12px] text-[var(--color-danger)]">
          {p.formErrors.map((e) => (<li key={e}>{e}</li>))}
        </ul>
      ) : null}

      <MeasureForm kind={p.kind} value={p.form} onChange={p.onForm} modes={p.modes} disabled={disabled} />

      <div className="flex flex-wrap gap-2 pt-1">
        <Button variant="primary" disabled={disabled || p.saving || Boolean(p.geometryHint) || p.formErrors.length > 0 || Boolean(p.blockedReason)} onClick={() => p.onSave(false)} data-testid="save-draft">
          {p.editingLabel ? t("boq.takeoff.measure.saveChanges", "Save changes") : t("boq.takeoff.measure.saveDraft", "Save draft")}
        </Button>
        {!p.editingLabel ? (
          <Button disabled={disabled || p.saving || Boolean(p.geometryHint) || p.formErrors.length > 0 || Boolean(p.blockedReason) || !p.form.work_item_code.trim()} onClick={() => p.onSave(true)} data-testid="save-confirm">
            {t("boq.takeoff.measure.saveConfirm", "Save & confirm")}
          </Button>
        ) : null}
        <Button variant="ghost" onClick={p.onCancel}>{t("boq.takeoff.measure.cancel", "Cancel (Esc)")}</Button>
      </div>
    </div>
  );
}

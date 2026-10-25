import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../organizations/components/OrganizationUi";
import { useUpdateSheet } from "../hooks/useTakeoff";
import type { TakeoffSheet } from "../types/takeoff.types";
import { BASIS_TEXT, DISCIPLINES, DISCIPLINE_TEXT, SHEET_TYPES, SHEET_TYPE_TEXT, identityLine, leavesBackdropOut } from "../utils/sheetIdentity";

interface Props {
  sheet: TakeoffSheet;
  drawingId: string | undefined;
  canEdit: boolean;
}

const SELECT = "rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-1.5 py-0.5 text-[12px]";

export function SheetIdentityBar({ sheet, drawingId, canEdit }: Props) {
  const { t } = useTranslation();
  const update = useUpdateSheet(drawingId);
  const identity = sheet.identity ?? null;
  const [editing, setEditing] = useState(false);
  const [discipline, setDiscipline] = useState<string>("");
  const [sheetType, setSheetType] = useState<string>("");
  if (!identity) return null;
  const line = identityLine(identity);
  const basis = identity.basis ?? "NONE";
  const gated = leavesBackdropOut(identity);
  const person = basis === "PERSON";

  const open = () => {
    setDiscipline(identity.discipline ?? "");
    setSheetType(identity.sheet_type ?? "");
    setEditing(true);
  };
  const save = () => {
    update.mutate(
      { sheetId: sheet.id, body: { identity: { discipline: discipline || null, sheet_type: sheetType || null } } },
      { onSuccess: () => setEditing(false) },
    );
  };
  const clear = () => {
    update.mutate({ sheetId: sheet.id, body: { identity: null } }, { onSuccess: () => setEditing(false) });
  };

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-1 text-[12px] text-[var(--color-text-secondary)]" data-testid="sheet-identity" data-gated={gated ? "true" : "false"}>
      <span>
        <span className="font-semibold text-[var(--color-text-primary)]">{line || t("boq.takeoff.identity.unknown", "Kind of sheet not found")}</span>
        {identity.title ? <span> — {identity.title}</span> : null}
        <span className="text-[var(--color-text-muted)]"> ({t(`boq.takeoff.identity.basis.${basis}`, BASIS_TEXT[basis] ?? basis)})</span>
      </span>
      {gated ? (
        <span data-testid="sheet-identity-gated">
          {t("boq.takeoff.identity.gated", "The walls and rooms drawn behind these symbols belong to the architectural drawing, so they are left out of this sheet.")}
        </span>
      ) : null}
      {canEdit && !editing ? (
        <button type="button" className="underline" onClick={open} data-testid="sheet-identity-edit">
          {t("boq.takeoff.identity.change", "Change")}
        </button>
      ) : null}
      {editing ? (
        <span className="flex flex-wrap items-center gap-2" data-testid="sheet-identity-form">
          <select className={SELECT} value={discipline} onChange={(e) => setDiscipline(e.target.value)} aria-label={t("boq.takeoff.identity.discipline", "Discipline")}>
            <option value="">{t("boq.takeoff.identity.notSet", "Not set")}</option>
            {DISCIPLINES.map((d) => (
              <option key={d} value={d}>{t(`boq.takeoff.identity.discipline.${d}`, DISCIPLINE_TEXT[d])}</option>
            ))}
          </select>
          <select className={SELECT} value={sheetType} onChange={(e) => setSheetType(e.target.value)} aria-label={t("boq.takeoff.identity.sheetType", "Kind of sheet")}>
            <option value="">{t("boq.takeoff.identity.notSet", "Not set")}</option>
            {SHEET_TYPES.map((s) => (
              <option key={s} value={s}>{t(`boq.takeoff.identity.type.${s}`, SHEET_TYPE_TEXT[s])}</option>
            ))}
          </select>
          <Button size="sm" disabled={update.isPending} onClick={save}>{t("boq.takeoff.identity.save", "Save")}</Button>
          {person ? <Button size="sm" disabled={update.isPending} onClick={clear}>{t("boq.takeoff.identity.useRead", "Use what was read")}</Button> : null}
          <button type="button" className="underline" onClick={() => setEditing(false)}>{t("boq.takeoff.identity.cancel", "Cancel")}</button>
          <span className="text-[var(--color-text-muted)]">{t("boq.takeoff.identity.applies", "Applies the next time the items of this sheet are read.")}</span>
        </span>
      ) : null}
    </div>
  );
}

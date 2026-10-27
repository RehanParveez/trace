import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import { useExtractSheet, useTakeoffFloorSources, useUpdateSheet } from "../hooks/useTakeoff";
import type { TakeoffSheet } from "../types/takeoff.types";
import { READ_AS_PLAN_BODY, rowsOf, summary, summaryText } from "../utils/sheetRole";
import type { SheetRoleRow } from "../utils/sheetRole";

interface Props {
  sheets: TakeoffSheet[];
  drawingId: string | undefined;
  canEdit: boolean;
  currentSheetId: string;
  onSelect: (sheetId: string) => void;
}

export function SheetRolePanel(p: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const floorSources = useTakeoffFloorSources(p.drawingId, open);
  const update = useUpdateSheet(p.drawingId);
  const extract = useExtractSheet(p.drawingId);
  const ordered = floorSources.data?.ordered ?? [];
  const rows = rowsOf(p.sheets, ordered);
  if (!rows.some((r) => r.role || r.readAs)) return null;
  const sum = summary(rows);
  const busy = update.isPending || extract.isPending;
  function readAsPlan(row: SheetRoleRow) {
    update.mutate({ sheetId: row.sheetId, body: READ_AS_PLAN_BODY }, { onSuccess: () => extract.mutate({ sheetId: row.sheetId, autoCalibrate: true }) });
  }
  return (
    <section className="border-b border-[var(--color-border)] px-4 py-2 text-[12px]" data-testid="sheet-roles" data-skipped={sum.skipped} data-guessed={sum.guessed}>
      <button type="button" className="flex w-full items-center gap-2 text-left" onClick={() => setOpen(!open)} aria-expanded={open} data-testid="sheet-roles-toggle">
        <span className="font-semibold">{t("boq.takeoff.roles.title", "What each sheet is")}</span>
        <span className="text-[11.5px] text-[var(--color-text-secondary)]">{summaryText(sum)}</span>
        {sum.guessed > 0 ? <Badge tone="gold">{t("boq.takeoff.roles.guessed", "floor guessed on {{n}}", { n: sum.guessed })}</Badge> : null}
        <span className="ml-auto text-[11.5px] text-[var(--color-text-secondary)]">{open ? t("boq.takeoff.roles.hide", "Hide") : t("boq.takeoff.roles.show", "Show")}</span>
      </button>
      {open ? (
        <div className="mt-2 space-y-2">
          <p className="text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.takeoff.roles.help", "Covers, dividers, sections, elevations, legends and specifications are not read for walls, rooms, finishes or openings. Details and schedules are read for their marks only, services sheets for their symbols only. If a sheet was set aside wrongly, use Read as plan. A floor that is guessed from the sheet order is a guess: set the floor on the sheet if it is wrong.")}
          </p>
          {update.error || extract.error ? <p className="text-[11.5px] text-[var(--color-danger)]" data-testid="sheet-roles-error">{t("boq.takeoff.roles.failed", "The sheet could not be changed. Try again.")}</p> : null}
          <ul className="space-y-1">
            {rows.map((r) => (
              <li key={r.sheetId} className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-[8px] border border-[var(--color-border)] px-2 py-1" data-testid={`sheet-role-${r.pageNo}`} data-state={r.state} data-role={r.role ?? ""} data-floor={r.floor ?? ""} data-floor-basis={r.basis ?? ""}>
                <button type="button" className={`font-semibold underline-offset-2 hover:underline ${r.sheetId === p.currentSheetId ? "text-[var(--color-primary)]" : ""}`} onClick={() => p.onSelect(r.sheetId)}>
                  {t("boq.takeoff.roles.page", "Page {{n}}", { n: r.pageNo })}
                </button>
                {r.title ? <span className="max-w-[26ch] truncate text-[11.5px] text-[var(--color-text-secondary)]" title={r.title}>{r.title}</span> : null}
                {r.roleText ? <Badge tone="slate">{r.roleText}</Badge> : null}
                {r.disciplineText ? <Badge tone="slate">{r.disciplineText}</Badge> : null}
                {r.planKindText ? <Badge tone="slate">{r.planKindText}</Badge> : null}
                {r.floorText ? <Badge tone={r.guessed ? "gold" : "blue"}>{r.floorText}</Badge> : null}
                {r.basisText ? <span className="text-[11.5px] text-[var(--color-text-secondary)]">{r.basisText}</span> : null}
                <Badge tone={r.tone}>{r.stateText}</Badge>
                {r.person ? <Badge tone="blue">{t("boq.takeoff.roles.person", "set by you")}</Badge> : null}
                {r.canReadAsPlan && p.canEdit ? (
                  <Button size="sm" className="ml-auto" disabled={busy} onClick={() => readAsPlan(r)} data-testid={`sheet-read-as-plan-${r.pageNo}`}>
                    {t("boq.takeoff.roles.readAsPlan", "Read as plan")}
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

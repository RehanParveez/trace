import { useTranslation } from "react-i18next";
import { sheetTitle } from "../utils/sheetTitle";
import type { TakeoffCalibration, TakeoffMeasurement, TakeoffSheet } from "../types/takeoff.types";

interface Props {
  sheets: TakeoffSheet[];
  calibrations: TakeoffCalibration[];
  measurements: TakeoffMeasurement[];
  currentId: string | null;
  onSelect: (id: string) => void;
}

export function SheetStrip({ sheets, calibrations, measurements, currentId, onSelect }: Props) {
  const { t } = useTranslation();
  if (sheets.length <= 1) return null;
  return (
    <div className="flex gap-1.5 overflow-x-auto border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-1.5" role="tablist" aria-label="Sheets" data-testid="sheet-strip">
      {sheets.map((s) => {
        const calibrated = calibrations.some((c) => c.sheet_id === s.id && c.is_default && c.usable);
        const mine = measurements.filter((m) => m.sheet_id === s.id);
        const drafts = mine.filter((m) => m.status === "DRAFT").length;
        const confirmed = mine.length - drafts;
        const active = s.id === currentId;
        const state = s.prep_status === "FAILED" ? t("boq.takeoff.sheet.failed", "could not be read") : s.prep_status === "PENDING" ? t("boq.takeoff.sheet.reading", "reading…") : calibrated ? "" : t("boq.takeoff.sheet.noScale", "no scale");
        return (
          <button
            key={s.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onSelect(s.id)}
            data-testid="sheet-tab"
            className={`flex shrink-0 items-center gap-2 rounded-[7px] border px-2.5 py-1 text-left text-[12.5px] ${active ? "border-[var(--color-trace-gold)] bg-[var(--color-surface)] font-semibold" : "border-transparent hover:bg-[var(--color-surface)]"}`}
          >
            <span className={`h-2 w-2 rounded-full ${s.prep_status === "FAILED" ? "bg-[var(--color-danger)]" : s.prep_status === "PENDING" ? "bg-[var(--color-warning)]" : calibrated ? "bg-[var(--color-success)]" : "bg-[var(--color-border-strong,#bbb)]"}`} />
            <span>{sheetTitle(s)}</span>
            {state ? <span className="text-[11px] text-[var(--color-text-muted)]">{state}</span> : null}
            {mine.length > 0 ? <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{confirmed}✓{drafts > 0 ? ` ${drafts}d` : ""}</span> : null}
          </button>
        );
      })}
    </div>
  );
}

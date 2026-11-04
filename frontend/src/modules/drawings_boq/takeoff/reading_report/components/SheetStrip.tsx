import type { ReportSheet } from "../types/readingReport.types";
import { sheetHeading, sheetsByFloor, STATUS_VAR, statusText } from "../utils/readingReport";

interface Props {
  sheets: ReportSheet[];
  currentId: string | null;
  onSelect: (id: string) => void;
}

export function SheetStrip({ sheets, currentId, onSelect }: Props) {
  return (
    <div className="flex gap-3 overflow-x-auto border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-1.5" role="tablist" aria-label="Sheets" data-testid="report-sheet-strip">
      {sheetsByFloor(sheets).map((g) => (
        <div key={g.floor || "none"} className="flex shrink-0 items-center gap-1.5">
          {g.floor ? <span className="text-[10.5px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{g.floor.toLowerCase()}</span> : null}
          {g.sheets.map((s) => {
            const status = s.status ?? "NOT_RUN";
            const active = s.sheet_id === currentId;
            return (
              <button
                key={s.sheet_id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => onSelect(s.sheet_id)}
                data-testid="report-sheet-tab"
                title={`${sheetHeading(s)} — ${statusText(status)}`}
                className={`flex items-center gap-1.5 rounded-[7px] border px-2 py-1 text-[12px] ${active ? "border-[var(--color-trace-gold)] bg-[var(--color-surface)] font-semibold" : "border-transparent hover:bg-[var(--color-surface)]"}`}
              >
                <span className="h-2 w-2 rounded-full" style={{ background: STATUS_VAR[status] }} />
                <span>{s.page_no}</span>
                <span className="font-mono text-[10.5px] text-[var(--color-text-muted)]">{s.items}</span>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

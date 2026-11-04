import type { ReportSheet } from "../types/readingReport.types";
import { emptyCardLines, roleText, SCALE_TEXT, sheetHeading, sheetSubline, STATUS_VAR, statusText, TEXT_TYPE_TEXT, totalsLine } from "../utils/readingReport";
import { CoverageBars } from "./CoverageBars";

interface Props {
  sheet: ReportSheet;
  active: boolean;
  onSelect: (id: string) => void;
  compact?: boolean;
}

export function SheetCard({ sheet, active, onSelect, compact = false }: Props) {
  const status = sheet.status ?? "NOT_RUN";
  const empty = sheet.items === 0;
  return (
    <article
      className={`rounded-[10px] border bg-[var(--color-surface)] p-3 text-[12.5px] ${active ? "border-[var(--color-trace-gold)]" : "border-[var(--color-border)]"} ${compact ? "w-[260px] shrink-0" : ""}`}
      data-testid="report-sheet-card"
      data-status={status}
    >
      <button type="button" onClick={() => onSelect(sheet.sheet_id)} className="block w-full text-left" aria-current={active ? "true" : undefined}>
        <span className="flex items-start justify-between gap-2">
          <span>
            <span className="block font-semibold">{sheetHeading(sheet)}</span>
            <span className="block text-[11.5px] text-[var(--color-text-secondary)]">p. {sheet.page_no} · {sheetSubline(sheet)}</span>
          </span>
          <span className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold text-white" style={{ background: STATUS_VAR[status] }} data-testid="sheet-status">{statusText(status)}</span>
        </span>
        <span className="mt-1 flex flex-wrap gap-1 text-[10.5px] text-[var(--color-text-secondary)]">
          <span className="rounded bg-[var(--color-surface-muted)] px-1.5 py-0.5" data-testid="chip-role">{roleText(sheet.role)}</span>
          {sheet.floor ? <span className="rounded bg-[var(--color-surface-muted)] px-1.5 py-0.5" data-testid="chip-floor">{sheet.floor.toLowerCase()}</span> : null}
          {sheet.text_type ? <span className="rounded bg-[var(--color-surface-muted)] px-1.5 py-0.5" data-testid="chip-text-type">{TEXT_TYPE_TEXT[sheet.text_type] ?? sheet.text_type}</span> : null}
          <span className={`rounded px-1.5 py-0.5 ${sheet.scale === "SET" ? "bg-[var(--color-surface-muted)]" : "bg-[var(--color-warning-bg)] text-[var(--color-warning)]"}`} data-testid="chip-scale">{SCALE_TEXT[sheet.scale]}</span>
        </span>
        <span className="mt-1 block text-[11.5px] text-[var(--color-text-muted)]">{totalsLine(sheet.by_status)}</span>
      </button>
      {compact ? null : (
        <div className="mt-2">
          <CoverageBars rows={sheet.classes} />
          {empty || sheet.classes.length === 0 ? (
            <ul className="mt-2 list-disc space-y-0.5 pl-4 text-[11.5px] text-[var(--color-text-secondary)]" data-testid="empty-reasons">
              {emptyCardLines(sheet).map((l) => <li key={l}>{l}</li>)}
            </ul>
          ) : null}
        </div>
      )}
      {sheet.overrides + sheet.misreads > 0 ? (
        <p className="mt-2 text-[11px] text-[var(--color-text-muted)]">{sheet.overrides ? `${sheet.overrides} marked by hand` : ""}{sheet.overrides && sheet.misreads ? " · " : ""}{sheet.misreads ? `${sheet.misreads} misread reported` : ""}</p>
      ) : null}
    </article>
  );
}

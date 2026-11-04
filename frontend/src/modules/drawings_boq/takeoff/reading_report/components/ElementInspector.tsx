import type { ReportItem } from "../types/readingReport.types";
import { classText, confidenceText, itemNotes, MISREAD_TEXT, sourceText, STATUS_VAR, statusText } from "../utils/readingReport";
import { ReasonChips } from "./ReasonChips";

interface Props {
  item: ReportItem | null;
  canEdit: boolean;
  onReport: (item: ReportItem) => void;
  onMark: () => void;
}

export function ElementInspector({ item, canEdit, onReport, onMark }: Props) {
  if (!item) {
    return (
      <section className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12.5px]" data-testid="element-inspector">
        <h3 className="font-semibold">Inspector</h3>
        <p className="mt-1 text-[var(--color-text-secondary)]">Click an item on the sheet to see where it was read from, how sure the reader is and what is missing.</p>
        {canEdit ? <button type="button" onClick={onMark} className="mt-2 rounded-[8px] border border-[var(--color-border)] px-2 py-1 text-[11.5px]" data-testid="mark-manually">Mark manually</button> : null}
      </section>
    );
  }
  const notes = itemNotes(item);
  return (
    <section className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12.5px]" data-testid="element-inspector">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold">{item.mark ? `${classText(item.class)} ${item.mark}` : item.label}</h3>
          <p className="text-[11.5px] text-[var(--color-text-secondary)]">{item.label}</p>
        </div>
        <span className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold text-white" style={{ background: STATUS_VAR[item.status] }} data-testid="item-status">{statusText(item.status)}</span>
      </div>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11.5px]">
        <dt className="text-[var(--color-text-muted)]">Read from</dt><dd data-testid="item-source">{sourceText(item.source)}</dd>
        <dt className="text-[var(--color-text-muted)]">Confidence</dt><dd data-testid="item-confidence">{confidenceText(item.confidence)}</dd>
        <dt className="text-[var(--color-text-muted)]">Count</dt><dd>{item.count}</dd>
        <dt className="text-[var(--color-text-muted)]">Decision</dt><dd>{item.decision.toLowerCase()}</dd>
      </dl>
      {item.reasons.length ? <div className="mt-2"><ReasonChips codes={item.reasons} limit={8} /></div> : null}
      {notes.length ? <ul className="mt-2 list-disc space-y-0.5 pl-4 text-[11.5px] text-[var(--color-text-secondary)]" data-testid="item-notes">{notes.map((n) => <li key={n}>{n}</li>)}</ul> : null}
      {item.joins.length ? (
        <div className="mt-2" data-testid="item-joins">
          <h4 className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Joins</h4>
          <ul className="mt-0.5 space-y-0.5 text-[11.5px]">{item.joins.map((j, i) => <li key={`${j.kind}-${i}`}>{j.kind.replace(/_/g, " ")}: {j.status ?? "—"}{j.note ? ` — ${j.note}` : ""}</li>)}</ul>
        </div>
      ) : null}
      <button type="button" onClick={() => onReport(item)} className="mt-3 rounded-[8px] border border-[var(--color-border)] px-2 py-1 text-[11.5px]" data-testid="report-misread">Report misread</button>
      {canEdit ? <button type="button" onClick={onMark} className="ml-2 mt-3 rounded-[8px] border border-[var(--color-border)] px-2 py-1 text-[11.5px]" data-testid="mark-manually">Mark manually</button> : null}
      <p className="mt-2 text-[10.5px] text-[var(--color-text-muted)]">Wrong kinds you can report: {Object.values(MISREAD_TEXT).slice(0, 3).join("; ").toLowerCase()}…</p>
    </section>
  );
}

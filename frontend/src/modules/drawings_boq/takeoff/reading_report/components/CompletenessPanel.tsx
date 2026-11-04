import type { Completeness } from "../types/readingReport.types";
import { classText } from "../utils/readingReport";

interface Props {
  data: Completeness | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}

const STATE_TEXT = { COMPLETE: "Complete", PARTLY: "Partly complete", BLOCKED: "Blocked" } as const;
const STATE_CLASS = {
  COMPLETE: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  PARTLY: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  BLOCKED: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
} as const;

export function CompletenessPanel({ data, loading, error, onRetry }: Props) {
  return (
    <section className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12.5px]" data-testid="completeness-panel">
      <h3 className="font-semibold">Inputs the BOQ still needs</h3>
      {loading ? <p className="mt-1 text-[var(--color-text-muted)]">Checking the inputs…</p> : null}
      {error ? <p className="mt-1 text-[var(--color-danger)]">The inputs could not be checked. <button type="button" className="underline" onClick={onRetry}>Try again</button></p> : null}
      {data && data.items === 0 ? <p className="mt-1 text-[var(--color-text-secondary)]">Nothing has been read in this project yet, so no inputs are known.</p> : null}
      {data && data.items > 0 ? (
        <>
          <p className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]" data-testid="completeness-summary">{data.complete} of {data.items} items have every input. {data.blocking.length ? `${data.blocking.length} missing input${data.blocking.length === 1 ? "" : "s"} hold back BOQ lines.` : "Nothing holds back a BOQ line."}</p>
          <ul className="mt-2 space-y-1" data-testid="completeness-elements">
            {data.elements.map((e) => (
              <li key={e.element} className="flex items-center justify-between gap-2">
                <span>{classText(e.element)} <span className="text-[var(--color-text-muted)]">({e.complete}/{e.items})</span></span>
                <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${STATE_CLASS[e.state]}`}>{STATE_TEXT[e.state]}</span>
              </li>
            ))}
          </ul>
          {data.blocking.length ? (
            <div className="mt-3" data-testid="completeness-blocking">
              <h4 className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Missing inputs</h4>
              <ul className="mt-1 space-y-1">
                {data.blocking.map((b) => (
                  <li key={`${b.element}-${b.input}`} className="rounded-[8px] bg-[var(--color-surface-muted)] px-2 py-1">
                    <span className="font-medium">{classText(b.element)}: {b.label}</span>
                    <span className="text-[var(--color-text-muted)]"> — {b.items} item{b.items === 1 ? "" : "s"}{b.marks.length ? ` (${b.marks.join(", ")})` : ""}</span>
                    {b.blocks.length ? <span className="block text-[11px] text-[var(--color-text-secondary)]">Holds back: {b.blocks.map((w) => w.replace(/_/g, " ").toLowerCase()).join(", ")}</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

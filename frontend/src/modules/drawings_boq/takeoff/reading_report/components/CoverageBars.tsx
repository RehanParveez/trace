import type { ClassRow } from "../types/readingReport.types";
import { barLabel, barParts, classText, STATUS_VAR } from "../utils/readingReport";
import { ReasonChips } from "./ReasonChips";

interface Props {
  rows: ClassRow[];
  activeClass?: string | null;
  onPick?: (cls: string | null) => void;
}

export function CoverageBars({ rows, activeClass = null, onPick }: Props) {
  if (!rows.length) return null;
  return (
    <ul className="space-y-1.5" data-testid="coverage-bars">
      {rows.map((r) => {
        const parts = barParts(r);
        const active = activeClass === r.class;
        return (
          <li key={r.class} data-testid="coverage-row">
            <button
              type="button"
              disabled={!onPick}
              onClick={() => onPick?.(active ? null : r.class)}
              aria-pressed={active}
              className={`block w-full rounded-[6px] px-1 py-0.5 text-left ${active ? "bg-[var(--color-surface-muted)]" : ""} ${onPick ? "hover:bg-[var(--color-surface-muted)]" : "cursor-default"}`}
            >
              <span className="flex items-baseline justify-between gap-2 text-[11.5px]">
                <span className="font-medium">{classText(r.class)}{r.expected ? "" : " (not expected)"}</span>
                <span className="text-[var(--color-text-muted)]">{barLabel(r)}</span>
              </span>
              <span className="mt-0.5 flex h-1.5 overflow-hidden rounded-full bg-[var(--color-surface-muted)]" role="img" aria-label={`${classText(r.class)}: ${barLabel(r)}`}>
                {parts.map((p) => <span key={p.status} style={{ width: `${p.pct}%`, background: STATUS_VAR[p.status] }} className={p.count === 0 ? "opacity-35" : ""} />)}
              </span>
              {r.reasons.length ? <span className="mt-0.5 block"><ReasonChips codes={r.reasons} />{r.no_reader ? <span className="ml-1 text-[10.5px] text-[var(--color-text-muted)]">no reader for this yet</span> : null}</span> : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

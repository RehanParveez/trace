import { reasonText } from "../utils/readingReport";

export function ReasonChips({ codes, limit = 4 }: { codes: string[]; limit?: number }) {
  const shown = codes.slice(0, limit);
  const more = codes.length - shown.length;
  if (!codes.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1" data-testid="reason-chips">
      {shown.map((c) => (
        <span key={c} className="rounded-full bg-[var(--color-surface-muted)] px-2 py-0.5 text-[10.5px] text-[var(--color-text-secondary)]" title={c}>{reasonText(c)}</span>
      ))}
      {more > 0 ? <span className="px-1 text-[10.5px] text-[var(--color-text-muted)]">+{more}</span> : null}
    </span>
  );
}

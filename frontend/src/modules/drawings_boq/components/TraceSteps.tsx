import type { TraceStep } from "../types/drawings-boq.types";
import { formatPrecise, TRACE_OP_LABEL, traceStepDetail, traceStepValue } from "../utils/drawings-boq.utils";

export function TraceSteps({ steps }: { steps: TraceStep[] }) {
  if (!steps || steps.length === 0) return null;
  return (
    <ol className="space-y-1 text-[12px] text-[var(--color-text-secondary)]">
      {steps.map((s, i) => {
        const v = traceStepValue(s);
        const detail = traceStepDetail(s);
        return (
          <li key={i} className="flex flex-wrap items-baseline gap-x-3">
            <span className="w-5 font-mono text-[11px] text-[var(--color-text-muted)]">{i + 1}</span>
            <span className="font-semibold text-[var(--color-text-primary)]">
              {TRACE_OP_LABEL[s.op] ?? s.op}
            </span>
            {v ? (
              <span className="font-mono text-[12.5px]">
                {formatPrecise(v.value, 6)} {v.unit}
              </span>
            ) : null}
            {detail ? (
              <span className="text-[11px] text-[var(--color-text-muted)]">{detail}</span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
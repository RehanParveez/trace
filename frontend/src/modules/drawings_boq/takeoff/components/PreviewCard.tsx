import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../organizations/components/OrganizationUi";
import { isLowConfidence, warningInfo } from "../../utils/drawings-boq.utils";
import type { PreviewState } from "../hooks/useLivePreview";
import type { ComputedResult } from "../types/takeoff.types";
import { takeoffErrorMessage } from "../utils/errors";
import { fmtDecimal, fmtPct, fmtPlain } from "../utils/format";

export function ResultView({ result, compact = false }: { result: ComputedResult; compact?: boolean }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  if (result.error) {
    return (
      <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] p-3 text-[12.5px] text-[var(--color-danger)]">
        {takeoffErrorMessage({ response: { data: { error: { code: result.error.code, message: result.error.message } } } }, result.error.message)}
      </div>
    );
  }
  const low = isLowConfidence(result.confidence);
  const warnings = result.warnings ?? [];
  return (
    <div className="space-y-2" data-testid="preview-result">
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="font-mono text-[26px] font-semibold text-[var(--color-text-primary)]" data-testid="preview-quantity">
          {fmtDecimal(result.quantity, 4)}
        </span>
        <span className="text-[14px] font-semibold text-[var(--color-text-secondary)]">{result.unit}</span>
        <span className="ml-auto flex items-center gap-2">
          <Badge tone={low ? "gold" : "green"}>{t("boq.takeoff.confidence", "Confidence")} {fmtPct(result.confidence)}</Badge>
          {result.uncertainty_pct ? <Badge tone="slate">±{fmtPlain(result.uncertainty_pct, 1)}%</Badge> : null}
        </span>
      </div>
      {!compact && result.formula ? <div className="font-mono text-[11px] text-[var(--color-text-muted)]">{result.formula}</div> : null}
      {warnings.length > 0 ? (
        <ul className="space-y-1.5">
          {warnings.map((w) => {
            const info = warningInfo(w);
            return (
              <li key={w} className="rounded-[7px] bg-[var(--color-warning-bg)] px-2.5 py-1.5 text-[12px] text-[var(--color-text-primary)]">
                <span className="font-mono text-[11px] font-semibold text-[var(--color-warning)]">{w}</span> {info.message}
                {info.fix ? <div className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">{info.fix}</div> : null}
              </li>
            );
          })}
        </ul>
      ) : null}
      {!compact && result.steps && result.steps.length > 0 ? (
        <div>
          <button type="button" className="text-[12px] font-semibold text-[var(--color-info)]" onClick={() => setOpen((v) => !v)}>
            {open ? t("boq.takeoff.hideWorking", "Hide working") : t("boq.takeoff.showWorking", "Show working")}
          </button>
          {open ? (
            <ol className="mt-1.5 space-y-1 rounded-[7px] bg-[var(--color-surface-muted)] p-2.5 font-mono text-[11px] text-[var(--color-text-secondary)]">
              {result.steps.map((s, i) => (
                <li key={i}>{Object.entries(s).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join("  ·  ")}</li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function PreviewCard({ state, hint }: { state: PreviewState; hint?: string | null }) {
  const { t } = useTranslation();
  if (hint) {
    return <div className="rounded-[8px] border border-dashed border-[var(--color-border-strong)] p-3 text-[12.5px] text-[var(--color-text-secondary)]">{hint}</div>;
  }
  if (state.status === "idle") return null;
  if (state.status === "failed") {
    return <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] p-3 text-[12.5px] text-[var(--color-danger)]">{state.message}</div>;
  }
  if (state.status === "loading") {
    return (
      <div className="rounded-[8px] border border-[var(--color-border)] p-3 opacity-70">
        {state.last && state.last.ok ? <ResultView result={state.last} compact /> : <div className="text-[12.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.calculating", "Calculating…")}</div>}
      </div>
    );
  }
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <ResultView result={state.result} />
    </div>
  );
}
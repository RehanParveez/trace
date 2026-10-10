import {Badge, ErrorState, LoadingState, ProgressBar, SectionLabel,
} from "../../../organizations/components/OrganizationUi";
import { useRunMetrics } from "../hooks/useRecalculation";
import type { RunBudget, RunMetrics } from "../types/recalculation.types";
import {budgetLabel, fallbackReasonText, formatCount, formatDurationMs, formatMb, formatSeconds, runFailureInfo, usagePercent,
} from "../utils/recalculation.utils";
import { useScaleT, type Translate } from "../utils/useRecalculationT";
import { RunModeBadge } from "./RunModeBadge";

const COUNT_KEYS: Array<[string, string, string]> = [
  ["elements", "scale.counts.elements", "Elements read"],
  ["accepted", "scale.counts.accepted", "Measured"],
  ["rejected", "scale.counts.rejected", "Rejected"],
  ["solids", "scale.counts.solids", "Solids"],
  ["ledger_rows", "scale.counts.ledger_rows", "Ledger rows"],
  ["deductions", "scale.counts.deductions", "Deductions"],
  ["bar_marks", "scale.counts.bar_marks", "Bar marks"],
  ["warnings", "scale.counts.warnings", "Warnings"],
];

function budgetValue(unit: string, value: number | null): string {
  if (value === null) return "—";
  return unit === "MB" ? formatMb(value) : formatSeconds(value);
}

function BudgetCard({ budget, t }: { budget: RunBudget; t: Translate }) {
  const pct = usagePercent(budget.actual ?? 0, budget.limit);
  const tone = budget.ok === false ? "red" : pct >= 80 ? "gold" : "green";
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[12.5px] font-semibold text-[var(--color-text-primary)]">{budgetLabel(t, budget.name)}</div>
        {budget.ok === null ? (
          <Badge tone="slate">{t("scale.budget.notMeasured", "Not measured")}</Badge>
        ) : budget.ok ? (
          <Badge tone="green">{t("scale.budget.within", "Within limit")}</Badge>
        ) : (
          <Badge tone="red">{t("scale.budget.over", "Over limit")}</Badge>
        )}
      </div>
      <div className="mt-2 font-mono text-[13px] text-[var(--color-text-primary)]">
        {budgetValue(budget.unit, budget.actual)}
        <span className="text-[var(--color-text-muted)]"> / {budgetValue(budget.unit, budget.limit)}</span>
      </div>
      <div className="mt-2">
        <ProgressBar value={pct} tone={tone} size="sm" />
      </div>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{label}</div>
      <div className="mt-1.5 font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

function AllocationBlock({ metrics, t }: { metrics: RunMetrics; t: Translate }) {
  const a = metrics.allocation;
  const fallback = fallbackReasonText(t, a.fallback_reason);

  if (metrics.mode !== "INCREMENTAL") {
    return (
      <div className="text-[12px] text-[var(--color-text-secondary)]">
        {fallback ?? t("scale.alloc.fullAll", "Every element was calculated in this run.")}
      </div>
    );
  }

  const total = Number(a.participating ?? 0);
  const reused = Number(a.reused ?? 0);
  const recomputed = Number(a.recompute ?? 0);
  const reusedPct = total > 0 ? (reused / total) * 100 : 0;

  return (
    <div className="space-y-3">
      <div className="text-[12px] text-[var(--color-text-secondary)]">
        {t("scale.alloc.summary", "{{reused}} of {{total}} elements reused from the earlier run; {{recomputed}} recalculated.", {
          reused: formatCount(reused), total: formatCount(total), recomputed: formatCount(recomputed),
        })}
      </div>
      <div
        className="flex h-2.5 overflow-hidden rounded-full bg-[var(--color-surface-muted)]"
        role="img"
        aria-label={t("scale.alloc.barLabel", "{{pct}}% reused", { pct: Math.round(reusedPct) })}
      >
        <div className="h-full bg-[var(--color-success)]" style={{ width: `${reusedPct}%` }} />
        <div className="h-full bg-[var(--color-warning)]" style={{ width: `${100 - reusedPct}%` }} />
      </div>
      <div className="flex gap-4 text-[11px] text-[var(--color-text-muted)]">
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-[var(--color-success)]" />{t("scale.alloc.reused", "Reused")}</span>
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-[var(--color-warning)]" />{t("scale.alloc.recomputed", "Recalculated")}</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label={t("scale.alloc.added", "New elements")} value={formatCount(a.added ?? 0)} />
        <Tile label={t("scale.alloc.modified", "Changed elements")} value={formatCount(a.modified ?? 0)} />
        <Tile label={t("scale.alloc.removed", "Removed elements")} value={formatCount(a.removed ?? 0)} />
        <Tile label={t("scale.alloc.neighbours", "Recalculated as neighbours")} value={formatCount(a.affected_by_neighbourhood ?? 0)} />
      </div>
      {Number(a.order_flips ?? 0) + Number(a.remap_misses ?? 0) > 0 ? (
        <div className="text-[11px] text-[var(--color-text-muted)]">
          {t("scale.alloc.extra", "{{flips}} recalculated because the order of overlapping elements changed, {{misses}} because their earlier result could not be carried over.", {
            flips: formatCount(a.order_flips ?? 0), misses: formatCount(a.remap_misses ?? 0),
          })}
        </div>
      ) : null}
    </div>
  );
}

export function RunMetricsPanel({ runId, status }: { runId: string; status: string }) {
  const t = useScaleT();
  const query = useRunMetrics(runId, status);

  if (query.isLoading) return <LoadingState label={t("scale.metrics.loading", "Loading run metrics…")} />;
  if (query.isError || !query.data) {
    return <ErrorState title={t("scale.metrics.loadError", "Couldn't load run metrics")} onRetry={() => void query.refetch()} />;
  }

  const m = query.data;
  const stageTotal = m.stages.reduce((sum, s) => sum + (s.duration_ms ?? 0), 0);
  const failure = m.failure ? runFailureInfo(t, m.failure.code) : null;
  const extraTimings = Object.entries(m.timings_ms).filter(([k]) => !m.stages.some((s) => s.stage === k));

  return (
    <div className="space-y-6 p-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label={t("scale.metrics.duration", "Total time")} value={formatDurationMs(m.duration_ms)} />
        <Tile label={t("scale.metrics.peakMemory", "Peak memory")} value={formatMb(m.peak_rss_mb)} />
        <Tile label={t("scale.metrics.attempts", "Attempts")} value={String(m.attempts)} />
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            {t("scale.metrics.mode", "Mode")}
          </div>
          <div className="mt-1.5"><RunModeBadge mode={m.mode} fallbackReason={m.allocation.fallback_reason} /></div>
        </div>
      </div>

      {failure && m.failure ? (
        <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] p-3 text-[12px] text-[#c24a3a]">
          <div className="font-semibold">{failure.title}</div>
          <div className="mt-1 text-[var(--color-text-secondary)]">
            {m.failure.stage
              ? t("scale.metrics.failedAt", "It stopped at the “{{stage}}” stage.", { stage: m.failure.stage })
              : failure.hint}
          </div>
        </div>
      ) : null}

      <section>
        <SectionLabel>{t("scale.metrics.budgets", "Limits")}</SectionLabel>
        {m.budgets.length === 0 ? (
          <div className="text-[12px] text-[var(--color-text-muted)]">
            {t("scale.metrics.budgetsPending", "Time and memory are checked against their limits once a run has completed.")}
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {m.budgets.map((b) => <BudgetCard key={b.name} budget={b} t={t} />)}
          </div>
        )}
      </section>

      <section>
        <SectionLabel>{t("scale.metrics.allocation", "What was recalculated")}</SectionLabel>
        <AllocationBlock metrics={m} t={t} />
        {m.baseline_run_id ? (
          <div className="mt-3 text-[11px] text-[var(--color-text-muted)]">
            {t("scale.metrics.baseline", "Built on run {{id}}", { id: m.baseline_run_id.slice(0, 8) })}
          </div>
        ) : null}
      </section>

      {m.verify ? (
        <section>
          <SectionLabel>{t("scale.metrics.verify", "Check against a full calculation")}</SectionLabel>
          {m.verify.matched ? (
            <Badge tone="green">{t("scale.metrics.verifyMatched", "Identical to the full calculation")}</Badge>
          ) : (
            <div className="space-y-2">
              <Badge tone="red">{t("scale.metrics.verifyMismatch", "Differences found, full result kept")}</Badge>
              <ul className="list-disc pl-5 text-[12px] text-[var(--color-text-secondary)]">
                {(m.verify.problems ?? []).map((p, i) => <li key={i}>{String(p)}</li>)}
              </ul>
            </div>
          )}
        </section>
      ) : null}

      <section>
        <SectionLabel>{t("scale.metrics.stages", "Time and memory by stage")}</SectionLabel>
        {m.stages.length === 0 ? (
          <div className="text-[12px] text-[var(--color-text-muted)]">{t("scale.metrics.noStages", "No stage timings recorded yet.")}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr>
                  {[
                    t("scale.metrics.colStage", "Stage"), t("scale.metrics.colStatus", "Status"),
                    t("scale.metrics.colTime", "Time"), t("scale.metrics.colShare", "Share"),
                    t("scale.metrics.colMemory", "Peak memory"),
                  ].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {m.stages.map((s) => {
                  const share = stageTotal > 0 && s.duration_ms !== null ? (s.duration_ms / stageTotal) * 100 : 0;
                  return (
                    <tr key={s.stage} className="border-t border-[var(--color-border)]">
                      <td className="px-3 py-2.5 font-mono text-[12px] font-semibold">{s.stage}</td>
                      <td className="px-3 py-2.5 text-[11.5px] text-[var(--color-text-secondary)]">{s.status}</td>
                      <td className="px-3 py-2.5 font-mono text-[12px]">{formatDurationMs(s.duration_ms)}</td>
                      <td className="w-40 px-3 py-2.5"><ProgressBar value={share} tone="blue" size="sm" /></td>
                      <td className="px-3 py-2.5 font-mono text-[12px]">{formatMb(s.peak_rss_mb)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {extraTimings.length > 0 ? (
          <details className="mt-3">
            <summary className="cursor-pointer text-[11.5px] text-[var(--color-text-muted)]">
              {t("scale.metrics.otherTimings", "Other timings")}
            </summary>
            <dl className="mt-2 grid gap-x-6 gap-y-1 text-[11.5px] sm:grid-cols-2">
              {extraTimings.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3 border-b border-[var(--color-border)] py-1">
                  <dt className="font-mono text-[var(--color-text-secondary)]">{k}</dt>
                  <dd className="font-mono">{formatDurationMs(Number(v))}</dd>
                </div>
              ))}
            </dl>
          </details>
        ) : null}
      </section>

      <section>
        <SectionLabel>{t("scale.metrics.counts", "What it produced")}</SectionLabel>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {COUNT_KEYS.filter(([k]) => m.counts[k] !== undefined).map(([k, key, fallback]) => (
            <Tile key={k} label={t(key, fallback)} value={formatCount(m.counts[k])} />
          ))}
        </div>
      </section>
    </div>
  );
}

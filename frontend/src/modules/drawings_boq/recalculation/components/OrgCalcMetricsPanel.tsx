import { useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, ErrorState, LoadingState, Panel, PanelHeader, SectionLabel, StatCard } from "../../../organizations/components/OrganizationUi";
import { useOrgCalcMetrics } from "../hooks/useRecalculation";
import { formatCount, formatShare, formatSeconds, runFailureInfo } from "../utils/recalculation.utils";
import { useScaleT } from "../utils/useRecalculationT";
import { RunModeBadge } from "./RunModeBadge";

const WINDOWS = [7, 30, 90];

export function OrgCalcMetricsPanel() {
  const t = useScaleT();
  const [days, setDays] = useState(30);
  const query = useOrgCalcMetrics(days);

  const header = (
    <PanelHeader
      eyebrow={t("scale.org.eyebrow", "CALCULATION")}
      title={t("scale.org.title", "Run history")}
      description={t("scale.org.description", "How calculations have been going across all projects: how many ran, how fast, how often a partial update was enough, and what failed.")}
      action={
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          aria-label={t("scale.org.window", "Time window")}
          className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
        >
          {WINDOWS.map((d) => (
            <option key={d} value={d}>{t("scale.org.lastDays", "Last {{count}} days", { count: d })}</option>
          ))}
        </select>
      }
    />
  );

  if (query.isLoading) return <Panel>{header}<LoadingState label={t("scale.org.loading", "Loading run history…")} /></Panel>;
  if (query.isError || !query.data) {
    return <Panel>{header}<div className="p-5"><ErrorState title={t("scale.org.loadError", "Couldn't load run history")} onRetry={() => void query.refetch()} /></div></Panel>;
  }

  const m = query.data;
  if (m.runs_total === 0) {
    return (
      <Panel>
        {header}
        <EmptyState
          icon="clock"
          title={t("scale.org.emptyTitle", "No calculation runs yet")}
          description={t("scale.org.emptyDesc", "Runs started in this period will show up here.")}
        />
      </Panel>
    );
  }

  const failedTotal = Object.values(m.failure_codes).reduce((a, b) => a + b, 0);
  const statusEntries = Object.entries(m.runs_by_status).sort((a, b) => b[1] - a[1]);

  return (
    <Panel>
      {header}
      <div className="space-y-6 p-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("scale.org.statRuns", "Runs")} value={formatCount(m.runs_total)} note={t("scale.org.statRunsNote", "{{n}} running now", { n: m.active_now })} icon="trend" tone="blue" />
          <StatCard label={t("scale.org.statMedian", "Median time")} value={formatSeconds(m.duration_seconds.p50)} note={t("scale.org.statP95", "95% finish within {{time}}", { time: formatSeconds(m.duration_seconds.p95) })} icon="clock" tone="green" />
          <StatCard label={t("scale.org.statIncremental", "Partial updates")} value={formatShare(m.incremental_share)} note={t("scale.org.statIncrementalNote", "of finished runs reused earlier work")} icon="refresh" tone="blue" />
          <StatCard label={t("scale.org.statFailed", "Failed")} value={formatCount(failedTotal)} note={t("scale.org.statElements", "{{n}} elements measured", { n: formatCount(m.elements_processed) })} icon="alert" tone={failedTotal > 0 ? "red" : "green"} />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <section>
            <SectionLabel>{t("scale.org.byStatus", "Runs by outcome")}</SectionLabel>
            <ul className="divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
              {statusEntries.map(([status, count]) => (
                <li key={status} className="flex items-center justify-between px-3 py-2 text-[12px]">
                  <span className="font-mono text-[var(--color-text-secondary)]">{status}</span>
                  <span className="font-mono font-semibold">{formatCount(count)}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <SectionLabel>{t("scale.org.failures", "Why runs failed")}</SectionLabel>
            {failedTotal === 0 ? (
              <div className="rounded-[8px] border border-[var(--color-border)] p-3 text-[12px] text-[var(--color-text-muted)]">
                {t("scale.org.noFailures", "No failed runs in this period.")}
              </div>
            ) : (
              <ul className="divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
                {Object.entries(m.failure_codes).sort((a, b) => b[1] - a[1]).map(([code, count]) => (
                  <li key={code} className="px-3 py-2 text-[12px]">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[var(--color-text-secondary)]">{code}</span>
                      <span className="font-mono font-semibold">{formatCount(count)}</span>
                    </div>
                    <div className="mt-0.5 text-[11px] text-[var(--color-text-muted)]">{runFailureInfo(t, code).title}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <section>
          <SectionLabel>{t("scale.org.slowest", "Slowest runs")}</SectionLabel>
          {m.slowest_runs.length === 0 ? (
            <div className="text-[12px] text-[var(--color-text-muted)]">{t("scale.org.noSlow", "No finished runs to rank yet.")}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left">
                <thead className="bg-[var(--color-surface-muted)]">
                  <tr>
                    {[t("scale.org.colRun", "Run"), t("scale.org.colMode", "Mode"), t("scale.org.colTime", "Time"), t("scale.org.colElements", "Elements"), ""].map((h, i) => (
                      <th key={i} className="px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {m.slowest_runs.map((r) => (
                    <tr key={r.run_id} className="border-t border-[var(--color-border)]">
                      <td className="px-3 py-2.5 font-mono text-[12px]">{r.run_id.slice(0, 8)}</td>
                      <td className="px-3 py-2.5"><RunModeBadge mode={r.mode} /></td>
                      <td className="px-3 py-2.5 font-mono text-[12px]">{formatSeconds(r.duration_seconds)}</td>
                      <td className="px-3 py-2.5 font-mono text-[12px]">{formatCount(r.elements)}</td>
                      <td className="px-3 py-2.5 text-right">
                        <Link to={`/app/projects/${r.project_id}`} className="text-[11.5px] font-semibold text-[var(--color-info)] underline">
                          {t("scale.org.openProject", "Open project")}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </Panel>
  );
}

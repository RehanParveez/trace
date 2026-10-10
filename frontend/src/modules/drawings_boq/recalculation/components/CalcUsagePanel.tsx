import { Link } from "react-router-dom";
import { Badge, ErrorState, LoadingState, Panel, PanelHeader, ProgressBar } from "../../../organizations/components/OrganizationUi";
import { useCalcUsage } from "../hooks/useRecalculation";
import type { CalcUsage } from "../types/recalculation.types";
import { formatCount, formatSeconds, formatWindow, usagePercent, usageTone } from "../utils/recalculation.utils";
import { useScaleT, type Translate } from "../utils/useRecalculationT";

function Meter({ label, used, limit, note }: { label: string; used: number; limit: number | null; note?: string }) {
  const unlimited = limit === null || limit <= 0;
  const pct = usagePercent(used, limit);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-[12px] font-semibold text-[var(--color-text-primary)]">{label}</div>
        <div className="font-mono text-[12px]">
          {formatCount(used)}
          <span className="text-[var(--color-text-muted)]"> / {unlimited ? "∞" : formatCount(limit)}</span>
        </div>
      </div>
      <div className="mt-1.5"><ProgressBar value={unlimited ? 0 : pct} tone={usageTone(pct)} size="sm" /></div>
      {note ? <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">{note}</div> : null}
    </div>
  );
}

function UsageBody({ usage, t }: { usage: CalcUsage; t: Translate }) {
  const quota = usage.quota;
  const quotaLeft = quota?.remaining ?? null;
  const concurrentFull = usage.concurrent.limit > 0 && usage.concurrent.active >= usage.concurrent.limit;
  const rateFull = usage.rate_limits.some((w) => w.limit > 0 && w.remaining <= 0);

  return (
    <div className="space-y-4">
      {quota ? (
        <Meter
          label={t("scale.usage.quota", "Calculation runs in your plan")}
          used={quota.used}
          limit={quota.limit}
          note={
            quota.period_end
              ? t("scale.usage.quotaPeriod", "Resets {{date}}", { date: new Date(quota.period_end).toLocaleDateString() })
              : undefined
          }
        />
      ) : (
        <div className="text-[12px] text-[var(--color-text-muted)]">
          {t("scale.usage.noQuota", "No plan limit applies to calculation runs.")}
        </div>
      )}
      {quotaLeft !== null && quotaLeft <= 0 ? (
        <div className="flex flex-wrap items-center gap-2 text-[11.5px] text-[var(--color-danger)]">
          {t("scale.usage.quotaOut", "No runs left in this period.")}
          <Link to="/app/subscription" className="font-semibold underline">{t("scale.start.viewSubscription", "View subscription")}</Link>
        </div>
      ) : null}

      <Meter
        label={t("scale.usage.concurrent", "Running now")}
        used={usage.concurrent.active}
        limit={usage.concurrent.limit}
        note={concurrentFull ? t("scale.usage.concurrentFull", "At the limit. New runs wait until one finishes.") : undefined}
      />

      {usage.rate_limits.length > 0 ? (
        <div className="space-y-3">
          {usage.rate_limits.map((w) => (
            <Meter
              key={w.window_seconds}
              label={t("scale.usage.rate", "Runs started in the last {{window}}", { window: formatWindow(w.window_seconds) })}
              used={w.used}
              limit={w.limit}
              note={
                w.remaining <= 0 && w.resets_in_seconds > 0
                  ? t("scale.usage.rateResets", "Opens again in {{time}}", { time: formatSeconds(w.resets_in_seconds) })
                  : undefined
              }
            />
          ))}
        </div>
      ) : null}

      {rateFull ? (
        <Badge tone="gold">{t("scale.usage.rateFull", "Start limit reached")}</Badge>
      ) : null}
    </div>
  );
}

interface CalcUsagePanelProps {
  compact?: boolean;
  enabled?: boolean;
}

export function CalcUsagePanel({ compact = false, enabled = true }: CalcUsagePanelProps) {
  const t = useScaleT();
  const query = useCalcUsage(enabled);

  if (query.isLoading) {
    return compact ? (
      <div className="text-[11.5px] text-[var(--color-text-muted)]">{t("scale.usage.loading", "Loading usage…")}</div>
    ) : (
      <LoadingState label={t("scale.usage.loading", "Loading usage…")} />
    );
  }
  if (query.isError || !query.data) {
    return compact ? null : <ErrorState title={t("scale.usage.loadError", "Couldn't load usage")} onRetry={() => void query.refetch()} />;
  }

  if (compact) {
    return (
      <details className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)]">
        <summary className="cursor-pointer px-3 py-2 text-[11.5px] font-semibold text-[var(--color-text-secondary)]">
          {t("scale.usage.summary", "{{active}} running · {{left}} runs left in plan", {
            active: query.data.concurrent.active,
            left: query.data.quota?.remaining ?? "∞",
          })}
        </summary>
        <div className="border-t border-[var(--color-border)] p-3"><UsageBody usage={query.data} t={t} /></div>
      </details>
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("scale.usage.eyebrow", "LIMITS")}
        title={t("scale.usage.title", "Calculation usage")}
        description={t("scale.usage.description", "What your plan allows, how many runs are going now, and how many more can be started.")}
      />
      <div className="p-5"><UsageBody usage={query.data} t={t} /></div>
    </Panel>
  );
}
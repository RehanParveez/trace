import type { UsageMetric } from "../types/subscription.types";
import {Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {formatMetricLabel, formatQuota,
} from "../utils/subscription.utils";

interface UsageOverviewProps {
  metrics: UsageMetric[];
}

export function UsageOverview({
  metrics,
}: UsageOverviewProps) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="CURRENT PERIOD"
        title="Usage"
        description="Usage reported by the subscription service for the current billing period."
      />

      <div className="divide-y divide-[var(--color-border)] bg-[var(--color-surface-muted)]">
        {metrics.length === 0 ? (
          <div className="p-5 sm:p-6 text-[12px] text-[var(--color-text-secondary)]">
            No usage metrics have been reported for this period.
          </div>
        ) : (
          metrics.map((metric) => {
            const percentage =
              metric.percentage === null
                ? null
                : Math.min(
                    Math.max(metric.percentage, 0),
                    100,
                  );

            const isExceeded =
              metric.limit !== null &&
              metric.used >= metric.limit;

            const isNearLimit =
              metric.limit !== null &&
              metric.limit > 0 &&
              metric.used / metric.limit >= 0.8;

            return (
              <div
                key={metric.metric}
                className="p-5 sm:p-6"
              >
                <div className="flex items-start justify-between gap-5">
                  <div className="min-w-0">
                    <div className="text-[14px] font-semibold text-[var(--color-text-primary)]">
                      {formatMetricLabel(
                        metric.metric,
                      )}
                    </div>

                    <div className="mt-1.5 text-[12px] text-[var(--color-text-secondary)]">
                      {metric.limit === null
                        ? `${metric.used.toLocaleString("en-PK")} used`
                        : `${metric.used.toLocaleString(
                            "en-PK",
                          )} of ${formatQuota(
                            metric.metric,
                            metric.limit,
                          )}`}
                    </div>
                  </div>

                  <div className="shrink-0 text-right">
                    <div
                      className={`font-mono text-[13px] font-bold ${
                        isExceeded
                          ? "text-[var(--color-danger)]"
                          : isNearLimit
                            ? "text-[var(--color-warning)]"
                            : "text-[var(--color-text-primary)]"
                      }`}
                    >
                      {metric.limit === null
                        ? "Unlimited"
                        : `${Math.round(
                            percentage ?? 0,
                          )}%`}
                    </div>

                    {metric.remaining !== null ? (
                      <div className="mt-1 font-mono text-[11px] text-[var(--color-text-muted)]">
                        {metric.remaining.toLocaleString(
                          "en-PK",
                        )}{" "}
                        remaining
                      </div>
                    ) : null}
                  </div>
                </div>

                {percentage !== null ? (
                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-[var(--color-surface)]">
                    <div
                      className={`h-full rounded-full transition-all ${
                        isExceeded
                          ? "bg-[var(--color-danger)]"
                          : isNearLimit
                            ? "bg-[var(--color-warning)]"
                            : "bg-[var(--color-success)]"
                      }`}
                      style={{
                        width: `${percentage}%`,
                      }}
                    />
                  </div>
                ) : (
                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-[var(--color-surface)]">
                    <div className="h-full w-full rounded-full bg-[var(--color-trace-gold)]/30" />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </Panel>
  );
}
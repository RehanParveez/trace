import type { UsageMetric } from "../types/subscription.types";
import {Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {formatMetricLabel, formatQuota,
} from "../utils/subscription.utils";
import { useTranslation } from "react-i18next";

interface UsageOverviewProps {
  metrics: UsageMetric[];
}

export function UsageOverview({
  metrics,
}: UsageOverviewProps) {
  const { t } = useTranslation();

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow={t("subscription.usage.eyebrow")}
        title={t("subscription.usage.title")}
        description={t("subscription.usage.description")}
      />

      <div className="divide-y divide-[var(--color-border)] bg-[var(--color-surface-muted)]">
        {metrics.length === 0 ? (
          <div className="p-5 sm:p-6 text-[11px] text-[#756957]">
            {t("subscription.usage.empty")}
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

                    <div className="mt-1.5 text-[10.5px] text-[#756957]">
                      {metric.limit === null
                        ? t("subscription.usage.used", {
                            used: metric.used.toLocaleString("en-PK"),
                          })
                        : t("subscription.usage.usedOf", {
                            used: metric.used.toLocaleString("en-PK"),
                            limit: formatQuota(metric.metric, metric.limit),
                          })}
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
                        ? t("subscription.usage.unlimited")
                        : `${Math.round(percentage ?? 0)}%`}
                    </div>

                    {metric.remaining !== null ? (
                      <div className="mt-1 font-mono text-[9.5px] text-[#9a8c75]">
                        {t("subscription.usage.remaining", {
                          count: metric.remaining.toLocaleString("en-PK"),
                        })}
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
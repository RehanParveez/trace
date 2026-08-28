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
    <Panel>
      <PanelHeader
        eyebrow="CURRENT PERIOD"
        title="Usage"
        description="Usage reported by the subscription service for the current billing period."
      />

      <div className="divide-y divide-[#e1d5bc]">
        {metrics.length === 0 ? (
          <div className="p-5 text-[11px] text-[#6b6152]">
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
                className="p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="text-[12px] font-semibold text-[#191410]">
                      {formatMetricLabel(
                        metric.metric,
                      )}
                    </div>

                    <div className="mt-1 text-[10.5px] text-[#6b6152]">
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
                      className={`font-mono text-[12px] font-bold ${
                        isExceeded
                          ? "text-[#c24a3a]"
                          : isNearLimit
                            ? "text-[#b17a18]"
                            : "text-[#332a21]"
                      }`}
                    >
                      {metric.limit === null
                        ? "Unlimited"
                        : `${Math.round(
                            percentage ?? 0,
                          )}%`}
                    </div>

                    {metric.remaining !== null ? (
                      <div className="mt-0.5 font-mono text-[9.5px] text-[#a2957c]">
                        {metric.remaining.toLocaleString(
                          "en-PK",
                        )} remaining
                      </div>
                    ) : null}
                  </div>
                </div>

                {percentage !== null ? (
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#efe6d3]">
                    <div
                      className={`h-full rounded-full transition-all ${
                        isExceeded
                          ? "bg-[#c24a3a]"
                          : isNearLimit
                            ? "bg-[#c39a38]"
                            : "bg-[#2f7d5a]"
                      }`}
                      style={{
                        width: `${percentage}%`,
                      }}
                    />
                  </div>
                ) : (
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#efe6d3]">
                    <div className="h-full w-full rounded-full bg-[#d6b86a]/40" />
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
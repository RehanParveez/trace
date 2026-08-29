import type { Plan } from "../types/subscription.types";
import {Badge, Icon, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import { formatPrice, formatQuota,
} from "../utils/subscription.utils";

interface CurrentPlanCardProps {
  plan: Plan;
}

const quotaOrder = [
  "projects",
  "storage_bytes",
  "site_photos",
  "drawings",
  "ai_requests",
];

export function CurrentPlanCard({
  plan,
}: CurrentPlanCardProps) {
  const quotas = quotaOrder.filter(
    (metric) =>
      Object.prototype.hasOwnProperty.call(
        plan.quotas,
        metric,
      ),
  );

  const features = Object.entries(
    plan.features ?? {},
  );

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="PLAN CONFIGURATION"
        title={plan.name}
        description={
          plan.description ??
          "Current plan capabilities and limits."
        }
        action={
          <Badge tone="blue">
            {formatPrice(
              plan.price_monthly,
              plan.currency,
            )}
            {" / month"}
          </Badge>
        }
      />

      <div className="grid gap-0 divide-y divide-[#e1d5bc] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <div className="p-5 sm:p-6">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            Quotas
          </div>

          <div className="mt-4 space-y-2.5">
            {quotas.length === 0 ? (
              <div className="rounded-[9px] border border-[#e1d5bc] bg-white px-3.5 py-3 text-[11px] text-[#6b6152]">
                No quota configuration supplied.
              </div>
            ) : (
              quotas.map((metric) => (
                <div
                  key={metric}
                  className="flex items-center justify-between gap-4 rounded-[9px] border border-[#e1d5bc] bg-white px-3.5 py-3"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-[#fbefd9] text-[#b98626]">
                      <Icon
                        name="building"
                        size={12}
                      />
                    </div>

                    <span className="text-[11.5px] font-semibold text-[#191410]">
                      {metric
                        .replaceAll("_", " ")
                        .replace(
                          /\b\w/g,
                          (letter) =>
                            letter.toUpperCase(),
                        )}
                    </span>
                  </div>

                  <span className="shrink-0 font-mono text-[10.5px] font-semibold text-[#6b6152]">
                    {formatQuota(
                      metric,
                      plan.quotas[metric],
                    )}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-5 sm:p-6">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            Included capabilities
          </div>

          <div className="mt-4 space-y-2.5">
            {features.length === 0 ? (
              <div className="rounded-[9px] border border-[#e1d5bc] bg-white px-3.5 py-3 text-[11px] text-[#6b6152]">
                No feature configuration supplied.
              </div>
            ) : (
              features.map(([feature, enabled]) => (
                <div
                  key={feature}
                  className="flex items-center gap-3 rounded-[9px] border border-[#e1d5bc] bg-white px-3.5 py-3"
                >
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] ${
                      enabled
                        ? "bg-[#e4f5ec] text-[#1e9d63]"
                        : "bg-[#efe6d3] text-[#6b6152]"
                    }`}
                  >
                    <Icon
                      name={
                        enabled
                          ? "check"
                          : "lock"
                      }
                      size={12}
                    />
                  </div>

                  <span className="text-[11.5px] font-semibold text-[#191410]">
                    {feature
                      .replaceAll("_", " ")
                      .replace(
                        /\b\w/g,
                        (letter) =>
                          letter.toUpperCase(),
                      )}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}
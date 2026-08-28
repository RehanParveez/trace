import type { Plan } from "../types/subscription.types";
import {Badge, Icon, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {formatPrice, formatQuota,
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
    <Panel>
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
        <div className="p-5">
          <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
            Quotas
          </div>

          <div className="mt-3 space-y-2">
            {quotas.map((metric) => (
              <div
                key={metric}
                className="flex items-center justify-between gap-3 rounded-[8px] border border-[#e1d5bc] bg-white px-3 py-2.5"
              >
                <span className="text-[11.5px] font-medium text-[#332a21]">
                  {metric
                    .replaceAll("_", " ")
                    .replace(/\b\w/g, (letter) =>
                      letter.toUpperCase(),
                    )}
                </span>

                <span className="font-mono text-[10.5px] font-semibold text-[#6b6152]">
                  {formatQuota(
                    metric,
                    plan.quotas[metric],
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="p-5">
          <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
            Included capabilities
          </div>

          <div className="mt-3 space-y-2">
            {features.length === 0 ? (
              <div className="text-[11px] text-[#6b6152]">
                No feature configuration supplied.
              </div>
            ) : (
              features.map(([feature, enabled]) => (
                <div
                  key={feature}
                  className="flex items-center gap-2.5 rounded-[8px] border border-[#e1d5bc] bg-white px-3 py-2.5"
                >
                  <div
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-[7px] ${
                      enabled
                        ? "bg-[#e4f5ec] text-[#1e9d63]"
                        : "bg-[#f5efe3] text-[#a2957c]"
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

                  <span className="text-[11.5px] font-medium text-[#332a21]">
                    {feature
                      .replaceAll("_", " ")
                      .replace(/\b\w/g, (letter) =>
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
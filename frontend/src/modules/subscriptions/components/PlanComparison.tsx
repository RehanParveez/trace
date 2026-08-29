import type {BillingInterval, Plan, Subscription,
} from "../types/subscription.types";
import {Badge, Button, Icon, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {formatPrice, formatQuota,
} from "../utils/subscription.utils";

interface PlanComparisonProps {
  plans: Plan[];
  subscription: Subscription;
  billingInterval: BillingInterval;
  canManage: boolean;
  onChangePlan: (plan: Plan) => void;
}

const quotaRows = [
  "projects",
  "storage_bytes",
  "site_photos",
  "drawings",
  "ai_requests",
];

const featureRows = [
  "projects",
  "site_logs",
  "basic_boq",
  "ai",
  "advanced_boq",
];

export function PlanComparison({
  plans,
  subscription,
  billingInterval,
  canManage,
  onChangePlan,
}: PlanComparisonProps) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="PLAN CATALOG"
        title="Available plans"
        description="Compare the public plans configured by the subscription service."
        action={
          <Badge tone="gold">
            {billingInterval === "YEARLY"
              ? "Yearly"
              : "Monthly"}
          </Badge>
        }
      />

      <div className="grid gap-4 p-5 md:grid-cols-3">
        {plans.map((plan) => {
          const current =
            plan.id === subscription.plan_id;

          const price =
            billingInterval === "YEARLY"
              ? plan.price_yearly
              : plan.price_monthly;

          return (
            <div
              key={plan.id}
              className={`relative flex flex-col rounded-[11px] border p-5 transition ${
                current
                  ? "border-[#d9a441] bg-[#fbefd9] shadow-[0_10px_28px_rgba(90,70,40,0.08)]"
                  : "border-[#e1d5bc] bg-white hover:border-[#cdbd9c] hover:shadow-[0_8px_22px_rgba(90,70,40,0.05)]"
              }`}
            >
              {current ? (
                <div className="absolute left-5 top-0 h-0.5 w-12 rounded-b-full bg-[#d9a441]" />
              ) : null}

              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-[Archivo] text-[19px] font-bold tracking-[-0.015em] text-[#191410]">
                    {plan.name}
                  </div>

                  <div className="mt-1.5 min-h-[36px] text-[10.5px] leading-4 text-[#6b6152]">
                    {plan.description}
                  </div>
                </div>

                {current ? (
                  <Badge tone="green">
                    Current
                  </Badge>
                ) : null}
              </div>

              <div className="mt-5">
                <span className="font-[Archivo] text-[27px] font-bold tracking-[-0.02em] text-[#191410]">
                  {formatPrice(
                    price,
                    plan.currency,
                  )}
                </span>

                {price !== 0 ? (
                  <span className="ml-1.5 text-[10px] text-[#7c7060]">
                    /
                    {billingInterval ===
                    "YEARLY"
                      ? " year"
                      : " month"}
                  </span>
                ) : null}
              </div>

              <div className="mt-5 border-t border-[#e1d5bc] pt-4">
                <div className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
                  Resource limits
                </div>

                <div className="mt-3 space-y-2.5">
                  {quotaRows.map((metric) => (
                    <div
                      key={metric}
                      className="flex items-center justify-between gap-3"
                    >
                      <span className="text-[10.5px] text-[#6b6152]">
                        {metric
                          .replaceAll("_", " ")
                          .replace(
                            /\b\w/g,
                            (letter) =>
                              letter.toUpperCase(),
                          )}
                      </span>

                      <span className="font-mono text-[9.5px] font-semibold text-[#191410]">
                        {formatQuota(
                          metric,
                          plan.quotas[metric] ??
                            null,
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 border-t border-[#e1d5bc] pt-4">
                <div className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
                  Included capabilities
                </div>

                <div className="mt-3 space-y-2.5">
                  {featureRows.map((feature) => (
                    <div
                      key={feature}
                      className="flex items-center gap-2.5"
                    >
                      <div
                        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] ${
                          plan.features[feature]
                            ? "bg-[#e4f5ec] text-[#1e9d63]"
                            : "bg-[#f5efe3] text-[#a2957c]"
                        }`}
                      >
                        <Icon
                          name={
                            plan.features[feature]
                              ? "check"
                              : "lock"
                          }
                          size={10}
                        />
                      </div>

                      <span className="text-[10.5px] text-[#6b6152]">
                        {feature
                          .replaceAll("_", " ")
                          .replace(
                            /\b\w/g,
                            (letter) =>
                              letter.toUpperCase(),
                          )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-auto pt-6">
                {current ? (
                  <Button
                    variant="ghost"
                    disabled
                    className="w-full"
                  >
                    Current plan
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    disabled={!canManage}
                    onClick={() =>
                      onChangePlan(plan)
                    }
                    className="w-full"
                  >
                    {canManage
                      ? "Select plan"
                      : "No permission"}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
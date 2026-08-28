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
    <Panel>
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

      <div className="grid gap-3 p-4 md:grid-cols-3">
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
              className={`rounded-[12px] border p-4 transition ${
                current
                  ? "border-[#c6a449] bg-[#fffaf0] shadow-[0_8px_25px_rgba(80,60,20,0.08)]"
                  : "border-[#e1d5bc] bg-white hover:border-[#cdbd9c]"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-[Archivo] text-[15px] font-bold text-[#191410]">
                    {plan.name}
                  </div>

                  <div className="mt-1 min-h-[32px] text-[10.5px] leading-4 text-[#6b6152]">
                    {plan.description}
                  </div>
                </div>

                {current ? (
                  <Badge tone="green">
                    Current
                  </Badge>
                ) : null}
              </div>

              <div className="mt-4">
                <span className="font-[Archivo] text-[23px] font-bold text-[#191410]">
                  {formatPrice(
                    price,
                    plan.currency,
                  )}
                </span>

                {price !== 0 ? (
                  <span className="ml-1 text-[10px] text-[#7c7060]">
                    /{" "}
                    {billingInterval === "YEARLY"
                      ? "year"
                      : "month"}
                  </span>
                ) : null}
              </div>

              <div className="mt-4 space-y-2 border-t border-[#e1d5bc] pt-4">
                {quotaRows.map((metric) => (
                  <div
                    key={metric}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="text-[10.5px] text-[#6b6152]">
                      {metric
                        .replaceAll("_", " ")
                        .replace(/\b\w/g, (letter) =>
                          letter.toUpperCase(),
                        )}
                    </span>

                    <span className="font-mono text-[9.5px] font-semibold text-[#332a21]">
                      {formatQuota(
                        metric,
                        plan.quotas[metric] ??
                          null,
                      )}
                    </span>
                  </div>
                ))}

                {featureRows.map((feature) => (
                  <div
                    key={feature}
                    className="flex items-center gap-2"
                  >
                    <Icon
                      name={
                        plan.features[feature]
                          ? "check"
                          : "lock"
                      }
                      size={11}
                      className={
                        plan.features[feature]
                          ? "text-[#2f7d5a]"
                          : "text-[#a2957c]"
                      }
                    />

                    <span className="text-[10.5px] text-[#6b6152]">
                      {feature
                        .replaceAll("_", " ")
                        .replace(/\b\w/g, (letter) =>
                          letter.toUpperCase(),
                        )}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-5">
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
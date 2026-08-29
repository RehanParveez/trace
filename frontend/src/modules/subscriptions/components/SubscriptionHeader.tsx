import type { Subscription, Plan } from "../types/subscription.types";
import {Badge, Button, Icon, Panel,
} from "../../organizations/components/OrganizationUi";
import {formatBillingInterval, formatDate, formatSubscriptionStatus, getSubscriptionStatusTone,
} from "../utils/subscription.utils";

interface SubscriptionHeaderProps {
  subscription: Subscription;
  plan: Plan;
  canManage?: boolean;
  canManageBilling?: boolean;
  onChangePlan?: () => void;
  onCancel?: () => void;
}

export function SubscriptionHeader({
  subscription,
  plan,
  canManage = false,
  canManageBilling = false,
  onChangePlan,
  onCancel,
}: SubscriptionHeaderProps) {
  return (
    <Panel className="overflow-hidden">
      <div className="relative bg-[linear-gradient(120deg,#080d18_0%,#0d1424_60%,#192640_100%)] p-6 text-white sm:p-7">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.028)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.028)_1px,transparent_1px)] bg-[length:28px_28px]" />

        <div className="pointer-events-none absolute -right-20 -top-24 h-56 w-56 rounded-full bg-[#d9a441]/[0.07] blur-3xl" />

        <div className="relative flex flex-col gap-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-[#8f9bb0]">
                  Current subscription
                </span>

                <Badge
                  tone={getSubscriptionStatusTone(
                    subscription.status,
                  )}
                >
                  {formatSubscriptionStatus(
                    subscription.status,
                  )}
                </Badge>
              </div>

              <h2 className="mt-3 font-[Archivo] text-[28px] font-bold leading-tight tracking-[-0.03em] text-white sm:text-[32px]">
                {plan.name}
              </h2>

              <p className="mt-2 max-w-[700px] text-[12px] leading-5 text-[#b9c5d5]">
                {plan.description ??
                  "Your organization's current Trace subscription."}
              </p>
            </div>

            {(canManage || canManageBilling) && (
              <div className="flex shrink-0 flex-wrap gap-2">
                {canManage ? (
                  <Button
                    variant="primary"
                    onClick={onChangePlan}
                  >
                    <Icon
                      name="settings"
                      size={13}
                    />
                    Change plan
                  </Button>
                ) : null}

                {canManageBilling &&
                subscription.status !== "CANCELLED" &&
                subscription.status !== "EXPIRED" ? (
                  <Button
                    variant="secondary"
                    onClick={onCancel}
                    className="border-[#34415f] bg-[#141c30] text-white hover:border-[#465576] hover:bg-[#1b2540]"
                  >
                    Cancel subscription
                  </Button>
                ) : null}
              </div>
            )}
          </div>

          <div className="border-t border-[#263356]" />
        </div>
      </div>

      <div className="grid gap-0 divide-y divide-[#e1d5bc] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-5 sm:p-6">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            Billing
          </div>

          <div className="mt-2 text-[14px] font-semibold text-[#191410]">
            {formatBillingInterval(
              subscription.billing_interval,
            )}
          </div>

          <div className="mt-1 text-[11px] text-[#7c7060]">
            Provider: {subscription.provider}
          </div>
        </div>

        <div className="p-5 sm:p-6">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            Period started
          </div>

          <div className="mt-2 font-mono text-[13px] font-semibold text-[#191410]">
            {formatDate(
              subscription.current_period_start,
            )}
          </div>

          <div className="mt-1 text-[11px] text-[#7c7060]">
            Current billing period
          </div>
        </div>

        <div className="p-5 sm:p-6">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            Period ends
          </div>

          <div className="mt-2 font-mono text-[13px] font-semibold text-[#191410]">
            {formatDate(
              subscription.current_period_end,
            )}
          </div>

          <div className="mt-1 text-[11px] text-[#7c7060]">
            {subscription.cancel_at_period_end
              ? "Scheduled for cancellation"
              : "Renews normally"}
          </div>
        </div>
      </div>
    </Panel>
  );
}
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
      <div className="bg-[#0f172a] p-5 text-white sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[9.5px] font-bold uppercase tracking-[0.14em] text-[#d6b86a]">
                CURRENT SUBSCRIPTION
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

            <h2 className="mt-2 font-[Archivo] text-[22px] font-bold tracking-[-0.02em] text-white">
              {plan.name}
            </h2>

            <p className="mt-1 max-w-[650px] text-[11.5px] leading-5 text-[#c9d0dc]">
              {plan.description ??
                "Your organization's current Trace subscription."}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {canManage ? (
              <Button
                variant="primary"
                onClick={onChangePlan}
              >
                <Icon name="settings" size={13} />
                Change plan
              </Button>
            ) : null}

            {canManageBilling &&
            subscription.status !== "CANCELLED" &&
            subscription.status !== "EXPIRED" ? (
              <Button
                variant="ghost"
                onClick={onCancel}
              >
                Cancel subscription
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid gap-0 divide-y divide-[#e1d5bc] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-5">
          <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
            Billing
          </div>

          <div className="mt-1.5 text-[13px] font-semibold text-[#191410]">
            {formatBillingInterval(
              subscription.billing_interval,
            )}
          </div>

          <div className="mt-1 text-[10.5px] text-[#6b6152]">
            Provider: {subscription.provider}
          </div>
        </div>

        <div className="p-5">
          <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
            Period started
          </div>

          <div className="mt-1.5 font-mono text-[11.5px] font-semibold text-[#332a21]">
            {formatDate(
              subscription.current_period_start,
            )}
          </div>

          <div className="mt-1 text-[10.5px] text-[#6b6152]">
            Current billing period
          </div>
        </div>

        <div className="p-5">
          <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">
            Period ends
          </div>

          <div className="mt-1.5 font-mono text-[11.5px] font-semibold text-[#332a21]">
            {formatDate(
              subscription.current_period_end,
            )}
          </div>

          <div className="mt-1 text-[10.5px] text-[#6b6152]">
            {subscription.cancel_at_period_end
              ? "Scheduled for cancellation"
              : "Renews normally"}
          </div>
        </div>
      </div>
    </Panel>
  );
}
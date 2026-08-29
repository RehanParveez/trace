import { useState } from "react";
import {useCancelSubscription, useChangePlan, useSubscription, useSubscriptionPlans, useSubscriptionUsage,
} from "../hooks";
import type {BillingInterval, Plan,
} from "../types/subscription.types";
import { CancelSubscriptionDialog } from "../components/CancelSubscriptionDialog";
import { ChangePlanDialog } from "../components/ChangePlanDialog";
import { CurrentPlanCard } from "../components/CurrentPlanCard";
import { PlanComparison } from "../components/PlanComparison";
import { SubscriptionHeader } from "../components/SubscriptionHeader";
import { UsageOverview } from "../components/UsageOverview";
import {ErrorState, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import { SUBSCRIPTION_PERMISSIONS } from "../permissions";
import {formatBillingInterval, formatDate, formatSubscriptionStatus,
} from "../utils/subscription.utils";

interface SubscriptionPageProps {
  permissions?: string[];
}

export function SubscriptionPage({
  permissions = [],
}: SubscriptionPageProps) {
  const [changePlanOpen, setChangePlanOpen] =
    useState(false);

  const [cancelOpen, setCancelOpen] =
    useState(false);

  const [selectedPlan, setSelectedPlan] =
    useState<Plan | undefined>();

  const subscriptionQuery =
    useSubscription();

  const plansQuery =
    useSubscriptionPlans();

  const usageQuery =
    useSubscriptionUsage();

  const changePlan =
    useChangePlan();

  const cancelSubscription =
    useCancelSubscription();

  const canRead = permissions.includes(
    SUBSCRIPTION_PERMISSIONS.SUBSCRIPTION_READ,
  );

  const canManage = permissions.includes(
    SUBSCRIPTION_PERMISSIONS.SUBSCRIPTION_MANAGE,
  );

  const canManageBilling =
    permissions.includes(
      SUBSCRIPTION_PERMISSIONS
        .SUBSCRIPTION_BILLING_MANAGE,
    );

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title="Subscription access unavailable"
        description="You do not have permission to view this organization's subscription."
      />
    );
  }

  if (
    subscriptionQuery.isLoading ||
    plansQuery.isLoading ||
    usageQuery.isLoading
  ) {
    return <LoadingState />;
  }

  if (
    subscriptionQuery.isError ||
    plansQuery.isError ||
    usageQuery.isError ||
    !subscriptionQuery.data ||
    !plansQuery.data ||
    !usageQuery.data
  ) {
    return (
      <ErrorState
        title="We couldn't load subscription details"
        description="The subscription, plans or usage information could not be loaded."
        onRetry={() => {
          void subscriptionQuery.refetch();
          void plansQuery.refetch();
          void usageQuery.refetch();
        }}
      />
    );
  }

  const subscription =
    subscriptionQuery.data;

  const plans = plansQuery.data;

  const usage = usageQuery.data;

  const currentPlan =
    plans.find(
      (plan) => plan.id === subscription.plan_id,
    ) ?? plans[0];

  if (!currentPlan) {
    return (
      <ErrorState
        title="Current plan unavailable"
        description="The subscription references a plan that is not available in the public plan catalog."
      />
    );
  }

  const activeFeatures = Object.values(
    currentPlan.features ?? {},
  ).filter(Boolean).length;

  const usedMetrics = usage.metrics;

  const totalUsed = usedMetrics.reduce(
    (sum, metric) => sum + metric.used,
    0,
  );

  const limitedMetrics =
    usedMetrics.filter(
      (metric) => metric.limit !== null,
    );

  const nearLimitCount =
    limitedMetrics.filter(
      (metric) =>
        metric.limit !== null &&
        metric.limit > 0 &&
        metric.used / metric.limit >= 0.8,
    ).length;

  function openChangePlan(plan?: Plan) {
    setSelectedPlan(plan);
    setChangePlanOpen(true);
  }

  function handleChangePlan(
    planId: string,
    billingInterval: BillingInterval,
  ) {
    changePlan.mutate(
      {
        plan_id: planId,
        billing_interval:
          billingInterval,
      },
      {
        onSuccess: () => {
          setChangePlanOpen(false);
          setSelectedPlan(undefined);
        },
      },
    );
  }

  function handleCancel(
    cancelAtPeriodEnd: boolean,
  ) {
    cancelSubscription.mutate(
      {
        cancel_at_period_end:
          cancelAtPeriodEnd,
      },
      {
        onSuccess: () => {
          setCancelOpen(false);
        },
      },
    );
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="SUBSCRIPTION & BILLING"
        title="Subscription control"
        description="Manage the organization's Trace plan, billing interval and current-period usage."
      />

      <SubscriptionHeader
        subscription={subscription}
        plan={currentPlan}
        canManage={canManage}
        canManageBilling={canManageBilling}
        onChangePlan={() =>
          openChangePlan()
        }
        onCancel={() =>
          setCancelOpen(true)
        }
      />

      <section>
        <SectionDivider
          title="Subscription pulse"
          description="Current plan state and resource consumption across this organization."
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Plan"
            value={currentPlan.name}
            note="Current subscription"
            icon="building"
            tone="blue"
          />

          <StatCard
            label="Status"
            value={formatSubscriptionStatus(
              subscription.status,
            )}
            note={
              subscription.cancel_at_period_end
                ? "Cancellation scheduled"
                : "Subscription state"
            }
            icon="check"
            tone={
              subscription.status ===
                "ACTIVE" ||
              subscription.status ===
                "TRIALING"
                ? "green"
                : "red"
            }
          />

          <StatCard
            label="Billing"
            value={formatBillingInterval(
              subscription.billing_interval,
            )}
            note={`Through ${formatDate(
              subscription.current_period_end,
            )}`}
            icon="settings"
            tone="gold"
          />

          <StatCard
            label="Usage"
            value={totalUsed}
            note={
              nearLimitCount > 0
                ? `${nearLimitCount} metric${
                    nearLimitCount === 1
                      ? ""
                      : "s"
                  } near limit`
                : `${activeFeatures} enabled plan capabilities`
            }
            icon="shield"
            tone={
              nearLimitCount > 0
                ? "gold"
                : "blue"
            }
          />
        </div>
      </section>

      <section>
        <SectionDivider
          title="Current-period usage"
          description={`Usage from ${formatDate(
            usage.period_start,
          )} through ${formatDate(
            usage.period_end,
          )}.`}
        />

        <UsageOverview
          metrics={usage.metrics}
        />
      </section>

      <section>
        <SectionDivider
          title="Current plan"
          description="Capabilities and quotas attached to the organization's active plan."
        />

        <CurrentPlanCard
          plan={currentPlan}
        />
      </section>

      <section>
        <SectionDivider
          title="Available plans"
          description="Compare the plans currently published by the Trace subscription service."
        />

        <PlanComparison
          plans={plans}
          subscription={subscription}
          billingInterval={
            subscription.billing_interval
          }
          canManage={canManage}
          onChangePlan={openChangePlan}
        />
      </section>

      {changePlanOpen ? (
        <ChangePlanDialog
          plans={plans}
          currentPlanId={
            subscription.plan_id
          }
          initialPlan={selectedPlan}
          isSubmitting={
            changePlan.isPending
          }
          onClose={() => {
            if (!changePlan.isPending) {
              setChangePlanOpen(false);
              setSelectedPlan(undefined);
            }
          }}
          onSubmit={handleChangePlan}
        />
      ) : null}

      {cancelOpen ? (
        <CancelSubscriptionDialog
          isSubmitting={
            cancelSubscription.isPending
          }
          onClose={() => {
            if (!cancelSubscription.isPending) {
              setCancelOpen(false);
            }
          }}
          onConfirm={handleCancel}
        />
      ) : null}
    </div>
  );
}
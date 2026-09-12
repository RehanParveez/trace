import { useState } from "react";
import {useCancelSubscription, useChangePlan, useSubscriptionPlans, useSubscriptionSummary, useSubscriptionUsage,
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
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import {formatBillingInterval, formatDate, formatSubscriptionStatus,
} from "../utils/subscription.utils";
import { useTranslation } from "react-i18next";

export function SubscriptionPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const [changePlanOpen, setChangePlanOpen] =
    useState(false);

  const [cancelOpen, setCancelOpen] =
    useState(false);

  const [selectedPlan, setSelectedPlan] =
    useState<Plan | undefined>();

  const subscriptionSummaryQuery =
    useSubscriptionSummary();

  const plansQuery =
    useSubscriptionPlans();

  const usageQuery =
    useSubscriptionUsage();

  const changePlan =
    useChangePlan();

  const cancelSubscription =
    useCancelSubscription();

  const canRead = permissions.includes(
    IDENTITY_PERMISSIONS.SUBSCRIPTION_READ,
  );

  const canManage = permissions.includes(
    IDENTITY_PERMISSIONS.SUBSCRIPTION_MANAGE,
  );

  const canManageBilling =
    permissions.includes(
      IDENTITY_PERMISSIONS
        .SUBSCRIPTION_BILLING_MANAGE,
    );

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title={t("subscription.accessUnavailable.title")}
        description={t("subscription.accessUnavailable.description")}
      />
    );
  }

  if (
    subscriptionSummaryQuery.isLoading ||
    plansQuery.isLoading ||
    usageQuery.isLoading
  ) {
    return <LoadingState />;
  }

    if (
    subscriptionSummaryQuery.isError ||
    plansQuery.isError ||
    usageQuery.isError ||
    !subscriptionSummaryQuery.data ||
    !plansQuery.data ||
    !usageQuery.data
  ) {
    return (
      <ErrorState
        title={t("subscription.loadError.title")}
        description={t("subscription.loadError.description")}
        onRetry={() => {
          void subscriptionSummaryQuery.refetch();
          void plansQuery.refetch();
          void usageQuery.refetch();
        }}
      />
    );
  }

  const { subscription, plan: currentPlan } =
    subscriptionSummaryQuery.data;
  const plans = plansQuery.data;
  const usage = usageQuery.data;
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
    idempotencyKey: string,
  ) {
    changePlan.mutate(
      {
        payload: {
          plan_id: planId,
          billing_interval: billingInterval,
        },
        idempotencyKey,
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
    idempotencyKey: string,
  ) {
    cancelSubscription.mutate(
      {
        payload: {
          cancel_at_period_end: cancelAtPeriodEnd,
        },
        idempotencyKey,
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
        eyebrow={t("subscription.page.eyebrow")}
        title={t("subscription.page.title")}
        description={t("subscription.page.description")}
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
          title={t("subscription.pulse.title")}
          description={t("subscription.pulse.description")}
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label={t("subscription.stat.plan")}
            value={currentPlan.name}
            note={t("subscription.stat.planNote")}
            icon="building"
            tone="blue"
            actionLabel={canManage ? "Change plan" : undefined}
            onAction={canManage ? () => openChangePlan() : undefined}
          />

          <StatCard
            label={t("subscription.stat.status")}
            value={formatSubscriptionStatus(
              subscription.status,
            )}
            note={
              subscription.cancel_at_period_end
                ? t("subscription.stat.statusNoteScheduled")
                : t("subscription.stat.statusNote")
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
            label={t("subscription.stat.billing")}
            value={formatBillingInterval(
              subscription.billing_interval,
            )}
            note={t("subscription.stat.billingNote", {
              date: formatDate(subscription.current_period_end),
            })}
            icon="settings"
            tone="gold"
          />

          <StatCard
            label={t("subscription.stat.usage")}
            value={totalUsed}
            note={
              nearLimitCount > 0
                ? t("subscription.stat.usageNearLimit", {
                    count: nearLimitCount,
                  })
                : t("subscription.stat.usageCapabilities", {
                    count: activeFeatures,
                  })
            }
            icon="shield"
            tone={
              nearLimitCount > 0
                ? "gold"
                : "blue"
            }
            actionLabel="View usage detail"
            onAction={() =>
              document
                .getElementById("usage-overview")
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          />
        </div>
      </section>

      <section id="usage-overview">
        <SectionDivider
          title={t("subscription.usageSection.title")}
          description={t("subscription.usageSection.description", {
            start: formatDate(usage.period_start),
            end: formatDate(usage.period_end),
          })}
        />

        <UsageOverview
          metrics={usage.metrics}
        />
      </section>

      <section>
        <SectionDivider
          title={t("subscription.currentPlanSection.title")}
          description={t("subscription.currentPlanSection.description")}
        />

        <CurrentPlanCard
          plan={currentPlan}
        />
      </section>

      <section>
        <SectionDivider
          title={t("subscription.availablePlansSection.title")}
          description={t("subscription.availablePlansSection.description")}
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
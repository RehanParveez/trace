import { useState } from "react";
import { useAdminSubscriptions } from "../hooks";
import type { SubscriptionStatus } from "../types/subscription.types";
import {Badge, Button, ErrorState, LoadingState, PageHeader, Panel, PanelHeader, SectionDivider,
} from "../../organizations/components/OrganizationUi";
import {formatBillingInterval, formatDate, formatSubscriptionStatus, getSubscriptionStatusTone,
} from "../utils/subscription.utils";
import { useAuthStore } from "../../identity";

const STATUS_FILTERS: { label: string; value: SubscriptionStatus | "ALL" }[] = [
  { label: "All", value: "ALL" },
  { label: "Trialing", value: "TRIALING" },
  { label: "Active", value: "ACTIVE" },
  { label: "Past due", value: "PAST_DUE" },
  { label: "Cancelled", value: "CANCELLED" },
  { label: "Expired", value: "EXPIRED" },
];

const PAGE_SIZE = 20;

export function AdminSubscriptionsPage() {
  const isPlatformAdmin = useAuthStore(
    (state) => state.user?.is_platform_admin ?? false,
  );
  const [statusFilter, setStatusFilter] = useState<SubscriptionStatus | "ALL">("ALL");
  const [page, setPage] = useState(1);

  const subscriptionsQuery = useAdminSubscriptions({
    status: statusFilter === "ALL" ? undefined : statusFilter,
    page,
    page_size: PAGE_SIZE,
  });

  if (!isPlatformAdmin) {
    return (
      <ErrorState
        title="Platform admin access required"
        description="This view is limited to Trace platform administrators."
      />
    );
  }

  if (subscriptionsQuery.isLoading) {
    return <LoadingState />;
  }

  if (subscriptionsQuery.isError || !subscriptionsQuery.data) {
    return (
      <ErrorState
        title="We couldn't load subscriptions"
        description="Cross-tenant subscription data could not be loaded. If the list is unexpectedly empty rather than erroring, check the RLS escape-hatch policy on the `subscriptions` table -- see the backend router's /admin endpoint notes."
        onRetry={() => void subscriptionsQuery.refetch()}
      />
    );
  }

  const { items, total, page: currentPage, page_size: pageSize } = subscriptionsQuery.data;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="PLATFORM ADMIN"
        title="Subscriptions"
        description="Cross-tenant view of every organization's subscription state."
      />

      <section>
        <SectionDivider
          title="Filter"
          description="Filter subscriptions by status across all organizations."
        />

        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((filter) => {
            const selected = filter.value === statusFilter;

            return (
              <button
                key={filter.value}
                type="button"
                onClick={() => {
                  setStatusFilter(filter.value);
                  setPage(1);
                }}
                className={`rounded-[9px] border px-3.5 py-2 text-[12px] font-semibold transition ${
                  selected
                    ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-text-primary)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-muted)]"
                }`}
              >
                {filter.label}
              </button>
            );
          })}
        </div>
      </section>

      <Panel className="overflow-hidden">
        <PanelHeader
          eyebrow={`${total.toLocaleString("en-PK")} TOTAL`}
          title="All organizations"
          description="One row per organization subscription, most recently created first."
        />

        <div className="divide-y divide-[var(--color-border)]">
          {items.length === 0 ? (
            <div className="p-5 sm:p-6 text-[12px] text-[var(--color-text-secondary)]">
              No subscriptions match this filter.
            </div>
          ) : (
            items.map((subscription) => (
              <div
                key={subscription.id}
                className="flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6"
              >
                <div className="min-w-0">

                  <div className="font-mono text-[12px] text-[var(--color-text-muted)]">
                    {subscription.organization_id}
                  </div>

                  <div className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
                    {formatBillingInterval(subscription.billing_interval)} · Provider: {subscription.provider}
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-4">
                  <div className="text-right">
                    <div className="text-[11px] text-[var(--color-text-muted)]">Period ends</div>
                    <div className="font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">
                      {formatDate(subscription.current_period_end)}
                    </div>
                  </div>

                  <Badge tone={getSubscriptionStatusTone(subscription.status)}>
                    {formatSubscriptionStatus(subscription.status)}
                  </Badge>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[var(--color-border)] p-4">
          <span className="text-[12px] text-[var(--color-text-muted)]">
            Page {currentPage} of {totalPages}
          </span>

          <div className="flex gap-2">
            <Button
              variant="ghost"
              disabled={currentPage <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              Previous
            </Button>

            <Button
              variant="ghost"
              disabled={currentPage >= totalPages}
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
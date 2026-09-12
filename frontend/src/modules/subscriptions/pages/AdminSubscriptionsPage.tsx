import { useState } from "react";
import { useAdminSubscriptions } from "../hooks";
import type { SubscriptionStatus } from "../types/subscription.types";
import {Badge, Button, ErrorState, LoadingState, PageHeader, Panel, PanelHeader, SectionDivider,
} from "../../organizations/components/OrganizationUi";
import {formatBillingInterval, formatDate, formatSubscriptionStatus, getSubscriptionStatusTone,
} from "../utils/subscription.utils";
import { useAuthStore } from "../../identity";
import { useTranslation } from "react-i18next";

const PAGE_SIZE = 20;

export function AdminSubscriptionsPage() {
  const { t } = useTranslation();
  const isPlatformAdmin = useAuthStore(
    (state) => state.user?.is_platform_admin ?? false,
  );

  const STATUS_FILTERS: { label: string; value: SubscriptionStatus | "ALL" }[] = [
    { label: t("subscription.admin.filter.all"), value: "ALL" },
    { label: t("subscription.admin.filter.trialing"), value: "TRIALING" },
    { label: t("subscription.admin.filter.active"), value: "ACTIVE" },
    { label: t("subscription.admin.filter.pastDue"), value: "PAST_DUE" },
    { label: t("subscription.admin.filter.cancelled"), value: "CANCELLED" },
    { label: t("subscription.admin.filter.expired"), value: "EXPIRED" },
  ];

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
        title={t("subscription.admin.accessRequired.title")}
        description={t("subscription.admin.accessRequired.description")}
      />
    );
  }

  if (subscriptionsQuery.isLoading) {
    return <LoadingState />;
  }

  if (subscriptionsQuery.isError || !subscriptionsQuery.data) {
    return (
      <ErrorState
        title={t("subscription.admin.loadError.title")}
        description={t("subscription.admin.loadError.description")}
        onRetry={() => void subscriptionsQuery.refetch()}
      />
    );
  }

  const { items, total, page: currentPage, page_size: pageSize } = subscriptionsQuery.data;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={t("subscription.admin.page.eyebrow")}
        title={t("subscription.admin.page.title")}
        description={t("subscription.admin.page.description")}
      />

      <section>
        <SectionDivider
          title={t("subscription.admin.filter.title")}
          description={t("subscription.admin.filter.description")}
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
          eyebrow={t("subscription.admin.list.eyebrow", {
            total: total.toLocaleString("en-PK"),
          })}
          title={t("subscription.admin.list.title")}
          description={t("subscription.admin.list.description")}
        />

        <div className="divide-y divide-[var(--color-border)]">
          {items.length === 0 ? (
            <div className="p-5 sm:p-6 text-[11px] text-[#756957]">
              {t("subscription.admin.list.empty")}
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

                  <div className="mt-1 text-[11px] text-[#6b6152]">
                    {formatBillingInterval(subscription.billing_interval)} ·{" "}
                    {t("subscription.admin.list.provider", {
                      provider: subscription.provider,
                    })}
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-4">
                  <div className="text-right">
                    <div className="text-[10px] text-[#a2957c]">
                      {t("subscription.admin.list.periodEnds")}
                    </div>
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
          <span className="text-[10.5px] text-[#9a8c75]">
            {t("subscription.admin.list.page", {
              current: currentPage,
              total: totalPages,
            })}
          </span>

          <div className="flex gap-2">
            <Button
              variant="ghost"
              disabled={currentPage <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              {t("subscription.admin.list.previous")}
            </Button>

            <Button
              variant="ghost"
              disabled={currentPage >= totalPages}
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            >
              {t("subscription.admin.list.next")}
            </Button>
          </div>
        </div>
      </Panel>
    </div>
  );
}

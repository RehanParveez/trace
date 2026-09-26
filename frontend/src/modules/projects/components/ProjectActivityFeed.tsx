import { useMemo } from "react";
import { Icon, LoadingState, Panel, PanelHeader } from "../../organizations/components/OrganizationUi";
import type { OrganizationIconName } from "../../organizations/types/organization.types";
import { formatRelativeTime } from "../../organizations/utils/organization.utils";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useSitePhotos } from "../../whatsapp";
import { VERIFICATION_PERMISSIONS, useProgressClaims, formatClaimPercentage } from "../../verification";
import { useProcurementRequests } from "../../procurement";
import { useExpenses, formatExpenseAmount } from "../../expenses";
import { CHANGE_ORDER_PERMISSIONS, useChangeOrders, formatChangeOrderMoney } from "../../change_orders";
import { SCHEDULING_PERMISSIONS, useProjectSchedule } from "../../scheduling";
import { PUNCH_LIST_PERMISSIONS, usePunchLists } from "../../punch_lists";

type FeedTone = "green" | "red" | "blue" | "gold" | "slate";

interface ActivityFeedItem {
  key: string;
  timestamp: string;
  icon: OrganizationIconName;
  tone: FeedTone;
  title: string;
  description?: string;
  imageUrl?: string;
}

interface ProjectActivityFeedProps {
  projectId: string;
}

const MAX_VISIBLE_ITEMS = 20;

export function ProjectActivityFeed({ projectId }: ProjectActivityFeedProps) {
  const permissions = usePermissionKeys();

  const canViewPhotos = permissions.includes(IDENTITY_PERMISSIONS.SITE_PHOTO_READ);
  const canViewClaims = permissions.includes(VERIFICATION_PERMISSIONS.PROGRESS_CLAIM_READ);
  const canViewProcurement = permissions.includes(IDENTITY_PERMISSIONS.PROCUREMENT_READ);
  const canViewExpenses = permissions.includes(IDENTITY_PERMISSIONS.EXPENSE_READ);
  const canViewChangeOrders = permissions.includes(CHANGE_ORDER_PERMISSIONS.CHANGE_ORDER_READ);
  const canViewSchedule = permissions.includes(SCHEDULING_PERMISSIONS.SCHEDULE_READ);
  const canViewPunchLists = permissions.includes(PUNCH_LIST_PERMISSIONS.PUNCH_LIST_READ);

  const punchListsQuery = usePunchLists(canViewPunchLists ? projectId : "");
  const scheduleQuery = useProjectSchedule(canViewSchedule ? projectId : "");
  const changeOrdersQuery = useChangeOrders(canViewChangeOrders ? projectId : "");
  const photosQuery = useSitePhotos({ projectId }, { enabled: canViewPhotos });
  const claimsQuery = useProgressClaims(projectId, undefined, { enabled: canViewClaims });
  const procurementQuery = useProcurementRequests({ projectId }, { enabled: canViewProcurement });
  const expensesQuery = useExpenses({ projectId }, { enabled: canViewExpenses });

  const isLoading =
    (canViewPhotos && photosQuery.isLoading) ||
    (canViewClaims && claimsQuery.isLoading) ||
    (canViewProcurement && procurementQuery.isLoading) ||
    (canViewExpenses && expensesQuery.isLoading) ||
    (canViewChangeOrders && changeOrdersQuery.isLoading);

  const hasAnyAccess = canViewPhotos || canViewClaims || canViewProcurement || canViewExpenses || canViewChangeOrders;

  const items = useMemo<ActivityFeedItem[]>(() => {
    const feed: ActivityFeedItem[] = [];

    for (const photo of photosQuery.data ?? []) {
      feed.push({
        key: `photo:${photo.id}`,
        timestamp: photo.created_at,
        icon: "site",
        tone: "blue",
        title: "Site photo added",
        description: photo.location_text ?? undefined,
        imageUrl: photo.photo_url,
      });
    }

    for (const claim of claimsQuery.data ?? []) {
      const claimMeta: Record<string, { title: string; tone: FeedTone }> = {
        DRAFT: { title: "Progress claim drafted", tone: "slate" },
        SUBMITTED: { title: "Progress claim submitted for review", tone: "gold" },
        APPROVED: { title: "Progress claim approved", tone: "green" },
        REJECTED: { title: "Progress claim rejected", tone: "red" },
      };
      const meta = claimMeta[claim.status] ?? { title: "Progress claim updated", tone: "slate" as FeedTone };

      feed.push({
        key: `claim:${claim.id}`,
        timestamp: claim.reviewed_at ?? claim.submitted_at ?? claim.created_at,
        icon: "check",
        tone: meta.tone,
        title: meta.title,
        description: `${formatClaimPercentage(claim.claimed_percentage)} claimed`,
      });
    }

    for (const request of procurementQuery.data?.items ?? []) {
      const procurementMeta: Record<string, { title: string; tone: FeedTone }> = {
        REQUESTED: { title: `Material requested: ${request.material_name}`, tone: "gold" },
        APPROVED: { title: `Procurement approved: ${request.material_name}`, tone: "blue" },
        ORDERED: { title: `Procurement ordered: ${request.material_name}`, tone: "blue" },
        RECEIVED: { title: `Procurement received: ${request.material_name}`, tone: "green" },
        CANCELLED: { title: `Procurement cancelled: ${request.material_name}`, tone: "red" },
      };
      const meta = procurementMeta[request.status] ?? {
        title: `Procurement updated: ${request.material_name}`,
        tone: "slate" as FeedTone,
      };

      feed.push({
        key: `procurement:${request.id}`,
        timestamp: request.updated_at ?? request.created_at,
        icon: "procurement",
        tone: meta.tone,
        title: meta.title,
        description: `${request.quantity} ${request.unit}`,
      });
    }

    for (const expense of expensesQuery.data?.items ?? []) {
      const expenseMeta: Record<string, { title: string; tone: FeedTone }> = {
        PENDING: { title: `Expense recorded: ${expense.category}`, tone: "gold" },
        APPROVED: { title: `Expense approved: ${expense.category}`, tone: "green" },
        REJECTED: { title: `Expense rejected: ${expense.category}`, tone: "red" },
      };
      const meta = expenseMeta[expense.status] ?? {
        title: `Expense updated: ${expense.category}`,
        tone: "slate" as FeedTone,
      };

      feed.push({
        key: `expense:${expense.id}`,
        timestamp: expense.updated_at ?? expense.created_at,
        icon: "expenses",
        tone: meta.tone,
        title: meta.title,
        description: formatExpenseAmount(expense.amount),
      });
    }

    for (const co of changeOrdersQuery.data ?? []) {
      const coMeta: Record<string, { title: string; tone: FeedTone }> = {
        DRAFT: { title: `Change order drafted: ${co.title}`, tone: "gold" },
        APPROVED: { title: `Change order approved: ${co.title}`, tone: "green" },
        REJECTED: { title: `Change order rejected: ${co.title}`, tone: "red" },
        CANCELLED: { title: `Change order cancelled: ${co.title}`, tone: "slate" },
      };

      const meta = coMeta[co.status] ?? {
        title: `Change order updated: ${co.title}`,
        tone: "slate" as FeedTone,
      };

      feed.push({
        key: `change-order:${co.id}`,
        timestamp: co.approved_at ?? co.rejected_at ?? co.created_at,
        icon: "budget",
        tone: meta.tone,
        title: meta.title,
        description: `#${co.change_order_number} · ${formatChangeOrderMoney(co.value_impact, co.currency)}`,
      });
    }

    for (const list of punchListsQuery.data ?? []) {
      if (list.status === "CLOSED" && list.closed_at) {
        feed.push({
          key: `punch-list:${list.id}`,
          timestamp: list.closed_at,
          icon: "check",
          tone: "green",
          title: `Punch list closed: ${list.title}`,
        });
      }
      for (const item of list.items) {
        if (item.status === "RESOLVED" || item.status === "WAIVED") {
          feed.push({
            key: `punch-item:${item.id}`,
            timestamp: item.resolved_at ?? new Date().toISOString(),
            icon: "check",
            tone: item.status === "RESOLVED" ? "green" : "slate",
            title: `Snag item ${item.status === "WAIVED" ? "waived" : "resolved"}: ${item.location}`,
          });
        }
      }
    }

    return feed
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, MAX_VISIBLE_ITEMS);
  }, [photosQuery.data, claimsQuery.data, procurementQuery.data, expensesQuery.data, changeOrdersQuery.data, punchListsQuery.data,]);

  if (!hasAnyAccess) {
    return null;
  }

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="ONE OPERATIONAL RECORD"
        title="Project activity"
        description="Site photos, progress claims, procurement, expenses and change orders for this project, in one timeline."
      />

      {isLoading ? (
        <LoadingState label="Loading project activity…" />
      ) : items.length === 0 ? (
        <div className="px-5 py-8 text-[13px] text-[var(--color-text-secondary)] sm:px-6">
          Nothing recorded for this project yet. Activity will appear here as photos, claims, procurement, expenses and change orders come in.
        </div>
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {items.map((item) => (
            <div key={item.key} className="flex items-start gap-3 px-5 py-3.5 sm:px-6">
              {item.imageUrl ? (
                <img
                  src={item.imageUrl}
                  alt=""
                  className="h-9 w-9 shrink-0 rounded-[8px] border border-[var(--color-border)] object-cover"
                  loading="lazy"
                />
              ) : (
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] ${toneClasses(item.tone)}`}
                >
                  <Icon name={item.icon} size={15} />
                </span>
              )}

              <div className="min-w-0 flex-1">
                <span className="text-[13px] font-medium text-[var(--color-text-primary)]">{item.title}</span>
                {item.description ? (
                  <div className="mt-0.5 text-[12px] text-[var(--color-text-secondary)]">{item.description}</div>
                ) : null}
              </div>

              <span className="shrink-0 whitespace-nowrap text-[11.5px] text-[var(--color-text-muted)]">
                {formatRelativeTime(item.timestamp)}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function toneClasses(tone: FeedTone): string {
  switch (tone) {
    case "green":
      return "bg-[var(--color-success-bg)] text-[var(--color-success)]";
    case "red":
      return "bg-[var(--color-danger-bg)] text-[var(--color-danger)]";
    case "blue":
      return "bg-[var(--color-info-bg)] text-[var(--color-info)]";
    case "gold":
      return "bg-[var(--color-warning-bg)] text-[var(--color-warning)]";
    default:
      return "bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]";
  }
}
import { Link } from "react-router-dom";
import { Icon, Panel, PanelHeader } from "./OrganizationUi";
import type { DashboardAttentionItem } from "../types/organization.types";

interface DashboardAttentionFeedProps {
  items: DashboardAttentionItem[];
  isLoading?: boolean;
}

export function DashboardAttentionFeed({
  items,
  isLoading = false,
}: DashboardAttentionFeedProps) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="NEEDS YOUR ATTENTION"
        title="Attention required"
        description="Open items that are waiting on a decision."
      />

      {isLoading ? (
        <div className="px-5 py-8 text-[13px] text-[var(--color-text-secondary)] sm:px-6">
          Checking for open items…
        </div>
      ) : items.length === 0 ? (
        <div className="flex items-center gap-3 px-5 py-8 sm:px-6">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-success-bg)] text-[var(--color-success)]">
            <Icon name="check" size={16} />
          </div>
          <p className="text-[13px] text-[var(--color-text-secondary)]">
            Nothing needs your attention right now.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {items.map((item) => (
            <Link
              key={item.key}
              to={item.to}
              className="flex items-center justify-between gap-3 px-5 py-4 outline-none transition hover:bg-[var(--color-surface-muted)] focus-visible:bg-[var(--color-surface-muted)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--color-trace-gold)] sm:px-6"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-[var(--color-warning-bg)] text-[var(--color-warning)]">
                  <Icon name={item.icon} size={14} />
                </div>
                <span className="text-[13px] font-medium text-[var(--color-text-primary)]">{item.label}</span>
              </div>
              <Icon name="arrow" size={13} className="shrink-0 text-[var(--color-text-muted)]" />
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}
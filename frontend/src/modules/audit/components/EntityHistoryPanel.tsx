import { EmptyState, ErrorState, LoadingState, Panel, PanelHeader } from "../../organizations/components/OrganizationUi";
import { useEntityAuditLog } from "../hooks";
import type { AuditEntityType } from "../types/audit.types";
import { formatAuditAction, formatAuditTimestamp } from "../utils/audit.utils";
import { useTranslation } from "react-i18next";

interface EntityHistoryPanelProps {
  entityType: AuditEntityType;
  entityId: string;
}

export function EntityHistoryPanel({ entityType, entityId }: EntityHistoryPanelProps) {
  const { t } = useTranslation();
  const historyQuery = useEntityAuditLog(entityType, entityId);

  if (historyQuery.isLoading) return <LoadingState label={t("audit.history.loading")} />;
  if (historyQuery.isError) return <ErrorState title={t("audit.history.loadError")} onRetry={() => void historyQuery.refetch()} />;

  const entries = historyQuery.data ?? [];

  return (
    <Panel>
      <PanelHeader eyebrow={t("audit.history.eyebrow")} title={t("audit.history.title")} />
      {entries.length === 0 ? (
        <EmptyState icon="clock" title={t("audit.history.emptyTitle")} description={t("audit.history.emptyDesc")} />
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {entries.map((entry) => (
            <div key={entry.id} className="flex items-start gap-3 p-4">
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold text-[var(--color-text-primary)]">{entry.summary}</div>
                <div className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">
                  {formatAuditAction(entry.action)} · {entry.actor_name ?? entry.actor_email ?? t("audit.table.system")} · {formatAuditTimestamp(entry.created_at)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
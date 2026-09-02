import { EmptyState, ErrorState, LoadingState, Panel, PanelHeader } from "../../organizations/components/OrganizationUi";
import { useEntityAuditLog } from "../hooks";
import type { AuditEntityType } from "../types/audit.types";
import { formatAuditAction, formatAuditTimestamp } from "../utils/audit.utils";

interface EntityHistoryPanelProps {
  entityType: AuditEntityType;
  entityId: string;
}

export function EntityHistoryPanel({ entityType, entityId }: EntityHistoryPanelProps) {
  const historyQuery = useEntityAuditLog(entityType, entityId);

  if (historyQuery.isLoading) return <LoadingState label="Loading history…" />;
  if (historyQuery.isError) return <ErrorState title="Couldn't load history" onRetry={() => void historyQuery.refetch()} />;

  const entries = historyQuery.data ?? [];

  return (
    <Panel>
      <PanelHeader eyebrow="RECORD HISTORY" title="History" />
      {entries.length === 0 ? (
        <EmptyState icon="clock" title="No history yet" description="Changes to this record will appear here." />
      ) : (
        <div className="divide-y divide-[#e1d5bc]">
          {entries.map((entry) => (
            <div key={entry.id} className="flex items-start gap-3 p-4">
              <div className="min-w-0 flex-1">
                <div className="text-[11.5px] font-semibold text-[#191410]">{entry.summary}</div>
                <div className="mt-1 text-[10px] text-[#a2957c]">
                  {formatAuditAction(entry.action)} · {entry.actor_name ?? entry.actor_email ?? "System"} · {formatAuditTimestamp(entry.created_at)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
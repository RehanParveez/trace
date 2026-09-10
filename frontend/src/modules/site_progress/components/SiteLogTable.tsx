import {Button, EmptyState, Icon, Panel, PanelHeader, TableShell,
} from "../../organizations/components/OrganizationUi";
import type { SiteLogEntry } from "../types/site-progress.types";
import { formatLogDate } from "../utils/site-progress.utils";
import { useDeleteSiteLog } from "../hooks";

interface SiteLogTableProps {
  logs: SiteLogEntry[];
  canCreate: boolean;
  canManage: boolean;
  onCreate: () => void;
}

export function SiteLogTable({ logs, canCreate, canManage, onCreate }: SiteLogTableProps) {
  const deleteLog = useDeleteSiteLog();

  return (
    <Panel>
      <PanelHeader
        eyebrow="SITE DIARY"
        title="Site progress logs"
        description="Daily reports from the field — workforce, weather and blockers."
        action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />New log</Button> : null}
      />

      {logs.length === 0 ? (
        <EmptyState
          icon="site"
          title="No site logs yet"
          description="Site logs will appear here once the field team starts recording daily progress."
          action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>New log</Button> : undefined}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[680px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Workforce</th>
                <th className="px-4 py-3">Weather</th>
                <th className="px-4 py-3">Blockers</th>
                <th className="px-4 py-3">Notes</th>
                {canManage ? <th className="px-4 py-3 text-right">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-3.5 text-[13px] font-semibold text-[var(--color-text-primary)]">{formatLogDate(log.log_date)}</td>
                  <td className="px-4 py-3.5 font-mono text-[12.5px] text-[var(--color-text-secondary)]">{log.workforce_count ?? "—"}</td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{log.weather ?? "—"}</td>
                  <td className="px-4 py-3.5 max-w-[220px] truncate text-[12.5px] text-[var(--color-text-secondary)]">{log.blockers ?? "—"}</td>
                  <td className="px-4 py-3.5 max-w-[260px] truncate text-[12.5px] text-[var(--color-text-secondary)]">{log.notes ?? "—"}</td>
                  {canManage ? (
                    <td className="px-4 py-3.5 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deleteLog.isPending}
                        onClick={() => {
                          if (window.confirm("Delete this site log?")) {
                            deleteLog.mutate(log.id);
                          }
                        }}
                      >
                        Delete
                      </Button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
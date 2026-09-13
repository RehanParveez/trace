import { Badge, EmptyState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import type { AuditLogEntry } from "../types/audit.types";
import { formatAuditAction, formatAuditTimestamp, formatEntityType, getAuditActionTone } from "../utils/audit.utils";
import { useTranslation } from "react-i18next";

interface AuditLogTableProps {
  entries: AuditLogEntry[];
}

export function AuditLogTable({ entries }: AuditLogTableProps) {
  const { t } = useTranslation();
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("audit.table.eyebrow")}
        title={t("audit.table.title")}
        description={t("audit.table.description")}
        action={<span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">{entries.length}</span>}
      />

      {entries.length === 0 ? (
        <EmptyState icon="shield" title={t("audit.table.emptyTitle")} description={t("audit.table.emptyDesc")}/>
      ) : (
        <TableShell>
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("audit.table.colWhen")}</th>
                <th className="px-4 py-3">{t("audit.table.colActor")}</th>
                <th className="px-4 py-3">{t("audit.table.colAction")}</th>
                <th className="px-4 py-3">{t("audit.table.colEntity")}</th>
                <th className="px-4 py-3">{t("audit.table.colSummary")}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-2.5 whitespace-nowrap font-mono text-[12px] text-[var(--color-text-secondary)]">{formatAuditTimestamp(entry.created_at)}</td>
                  <td className="px-4 py-2.5 text-[13px] text-[var(--color-text-primary)]">{entry.actor_name ?? entry.actor_email ?? t("audit.table.system")}</td>
                  <td className="px-4 py-2.5"><Badge tone={getAuditActionTone(entry.action)}>{formatAuditAction(entry.action)}</Badge></td>
                  <td className="px-4 py-2.5 text-[12px] text-[var(--color-text-secondary)]">{formatEntityType(entry.entity_type)}</td>
                  <td className="px-4 py-2.5 text-[13px] text-[var(--color-text-primary)]">{entry.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
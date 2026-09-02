import { Badge, EmptyState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import type { AuditLogEntry } from "../types/audit.types";
import { formatAuditAction, formatAuditTimestamp, formatEntityType, getAuditActionTone } from "../utils/audit.utils";

interface AuditLogTableProps {
  entries: AuditLogEntry[];
}

export function AuditLogTable({ entries }: AuditLogTableProps) {
  return (
    <Panel>
      <PanelHeader
        eyebrow="ACTIVITY RECORD"
        title="Audit log"
        description="An append-only record of who did what across this organization."
        action={<span className="rounded-full bg-[#efe6d3] px-2.5 py-1 font-mono text-[11px] font-semibold text-[#6b6152]">{entries.length}</span>}
      />

      {entries.length === 0 ? (
        <EmptyState icon="shield" title="No activity recorded" description="Actions across the organization will appear here as they happen." />
      ) : (
        <TableShell>
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-[#f5efe3]">
              <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                <th className="px-4 py-3">When</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Entity</th>
                <th className="px-4 py-3">Summary</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-t border-[#e1d5bc]">
                  <td className="px-4 py-3.5 whitespace-nowrap font-mono text-[10.5px] text-[#6b6152]">{formatAuditTimestamp(entry.created_at)}</td>
                  <td className="px-4 py-3.5 text-[11.5px] text-[#191410]">{entry.actor_name ?? entry.actor_email ?? "System"}</td>
                  <td className="px-4 py-3.5"><Badge tone={getAuditActionTone(entry.action)}>{formatAuditAction(entry.action)}</Badge></td>
                  <td className="px-4 py-3.5 text-[10.5px] text-[#6b6152]">{formatEntityType(entry.entity_type)}</td>
                  <td className="px-4 py-3.5 text-[11.5px] text-[#332a21]">{entry.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
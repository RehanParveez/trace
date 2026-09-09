import { useState } from "react";
import { Badge, EmptyState, Modal, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import type { AIRequestEntry } from "../types/ai-requests.types";
import { formatAIPurpose, formatAITimestamp, formatLatency, getAIStatusTone } from "../utils/ai-requests.utils";

interface AIRequestTableProps {
  entries: AIRequestEntry[];
}

export function AIRequestTable({ entries }: AIRequestTableProps) {
  const [viewing, setViewing] = useState<AIRequestEntry | null>(null);

  return (
    <>
      <Panel>
        <PanelHeader
          eyebrow="AI ORCHESTRATOR"
          title="AI requests"
          description="Every AI call made on this organization's behalf, whether it succeeded or not."
          action={<span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">{entries.length}</span>}
        />

        {entries.length === 0 ? (
          <EmptyState icon="settings" title="No AI requests yet" description="AI calls made during drawing parsing or WhatsApp caption processing will appear here." />
        ) : (
          <TableShell>
            <table className="w-full min-w-[700px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                  <th className="px-4 py-3">When</th>
                  <th className="px-4 py-3">Purpose</th>
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Latency</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id} onClick={() => setViewing(entry)} className="cursor-pointer border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                    <td className="px-4 py-3.5 whitespace-nowrap font-mono text-[12px] text-[var(--color-text-secondary)]">{formatAITimestamp(entry.created_at)}</td>
                    <td className="px-4 py-3.5 text-[13px] text-[var(--color-text-primary)]">{formatAIPurpose(entry.purpose)}</td>
                    <td className="px-4 py-3.5 font-mono text-[12px] text-[var(--color-text-secondary)]">{entry.model}</td>
                    <td className="px-4 py-3.5">
                      {entry.response ? <Badge tone={getAIStatusTone(entry.response.status)}>{entry.response.status}</Badge> : <Badge tone="slate">Pending</Badge>}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-[11px] text-[#191410]">{formatLatency(entry.response?.latency_ms ?? null)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      {viewing ? (
        <Modal title="AI request detail" description={formatAIPurpose(viewing.purpose)} onClose={() => setViewing(null)} wide>
          <div className="space-y-4">
            {viewing.response?.error_message ? (
              <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2.5 text-[12.5px] text-[var(--color-danger)]">{viewing.response.error_message}</div>
            ) : null}
            {viewing.response?.parsed_output ? (
              <div>
                <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">Parsed output</div>
                <pre className="mt-1.5 max-h-64 overflow-auto rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[12px] text-[var(--color-text-primary)]">
                  {JSON.stringify(viewing.response.parsed_output, null, 2)}
                </pre>
              </div>
            ) : null}
          </div>
        </Modal>
      ) : null}
    </>
  );
}
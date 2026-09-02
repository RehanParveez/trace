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
          action={<span className="rounded-full bg-[#efe6d3] px-2.5 py-1 font-mono text-[11px] font-semibold text-[#6b6152]">{entries.length}</span>}
        />

        {entries.length === 0 ? (
          <EmptyState icon="settings" title="No AI requests yet" description="AI calls made during drawing parsing or WhatsApp caption processing will appear here." />
        ) : (
          <TableShell>
            <table className="w-full min-w-[700px] text-left">
              <thead className="bg-[#f5efe3]">
                <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                  <th className="px-4 py-3">When</th>
                  <th className="px-4 py-3">Purpose</th>
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Latency</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id} onClick={() => setViewing(entry)} className="cursor-pointer border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]">
                    <td className="px-4 py-3.5 whitespace-nowrap font-mono text-[10.5px] text-[#6b6152]">{formatAITimestamp(entry.created_at)}</td>
                    <td className="px-4 py-3.5 text-[11.5px] text-[#191410]">{formatAIPurpose(entry.purpose)}</td>
                    <td className="px-4 py-3.5 font-mono text-[10.5px] text-[#6b6152]">{entry.model}</td>
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
              <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2.5 text-[11px] text-[#c24a3a]">{viewing.response.error_message}</div>
            ) : null}
            {viewing.response?.parsed_output ? (
              <div>
                <div className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Parsed output</div>
                <pre className="mt-1.5 max-h-64 overflow-auto rounded-[8px] border border-[#e1d5bc] bg-[#f5efe3] p-3 text-[10.5px] text-[#332a21]">
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
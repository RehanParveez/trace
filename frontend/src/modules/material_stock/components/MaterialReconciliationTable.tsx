import { Badge, EmptyState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import type { MaterialStockLine } from "../types/material-stock.types";

export function MaterialReconciliationTable({ lines, currency }: { lines: MaterialStockLine[]; currency: string }) {
  return (
    <Panel>
      <PanelHeader eyebrow="SITE RECONCILIATION" title="Material stock" description="Received minus issued minus wastage, per material for this project." />
      {lines.length === 0 ? (
        <EmptyState icon="materials" title="No material data yet" description="This fills in automatically once materials are received via Procurement and issue/wastage entries are recorded." />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Material</th><th className="px-4 py-3 text-right">Received</th>
                <th className="px-4 py-3 text-right">Issued</th><th className="px-4 py-3 text-right">Wastage</th>
                <th className="px-4 py-3 text-right">Balance</th><th className="px-4 py-3 text-right">Wastage %</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => {
                const wastagePct = line.wastage_percentage;
                const tone = wastagePct === null ? "slate" : wastagePct > 5 ? "red" : wastagePct > 2 ? "gold" : "green";
                return (
                  <tr key={line.material_name} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{line.material_name}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{Number(line.total_received).toFixed(2)} {line.unit}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{Number(line.total_issued).toFixed(2)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">
                      {Number(line.total_wastage).toFixed(2)}
                      {line.estimated_wastage_cost !== null ? <span className="ml-1 text-[11px] text-[var(--color-text-muted)]">(~{currency} {Number(line.estimated_wastage_cost).toLocaleString()})</span> : null}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{Number(line.balance).toFixed(2)}</td>
                    <td className="px-4 py-3.5 text-right"><Badge tone={tone as any}>{wastagePct === null ? "—" : `${wastagePct.toFixed(1)}%`}</Badge></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
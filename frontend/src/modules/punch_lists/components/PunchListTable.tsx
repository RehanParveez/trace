import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, StatCard, TableShell } from "../../organizations/components/OrganizationUi";
import type { PunchListDetail, ProjectPunchListSummary } from "../types/punch-list.types";
import { formatPunchListDate, getPunchListStatusTone } from "../utils/punch-list.utils";

export function PunchListTable({ punchLists, summary, canCreate, onCreate, onView }: {
  punchLists: PunchListDetail[]; summary?: ProjectPunchListSummary; canCreate: boolean;
  onCreate: () => void; onView: (id: string) => void;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label="Open items" value={summary?.total_open_items ?? "…"} note="Across all inspection rounds" icon="alert" tone={summary && summary.total_open_items > 0 ? "gold" : "green"} />
        <StatCard label="Project clear for final release" value={summary?.is_project_clear ? "Yes" : "Not yet"} note="Every punch list must be closed" icon="check" tone={summary?.is_project_clear ? "green" : "gold"} />
      </div>

      <Panel>
        <PanelHeader eyebrow="HANDOVER & DEFECTS" title="Punch lists" description="Formal snag inspections — required before final retention release." action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />New punch list</Button> : null} />
        {punchLists.length === 0 ? (
          <EmptyState icon="check" title="No punch lists yet" description="Start one at Practical Completion, and another at the end of the Defects Liability Period." action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>New punch list</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Title</th><th className="px-4 py-3">Inspection date</th><th className="px-4 py-3">Items</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
              <tbody>
                {punchLists.map((pl) => {
                  const open = pl.items.filter((i) => i.status === "OPEN" || i.status === "IN_PROGRESS").length;
                  return (
                    <tr key={pl.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                      <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{pl.title}</td>
                      <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatPunchListDate(pl.inspection_date)}</td>
                      <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{pl.items.length} total, {open} open</td>
                      <td className="px-4 py-3.5"><Badge tone={getPunchListStatusTone(pl.status)}>{pl.status}</Badge></td>
                      <td className="px-4 py-3.5 text-right"><Button variant="ghost" size="sm" onClick={() => onView(pl.id)}>Open</Button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>
    </div>
  );
}
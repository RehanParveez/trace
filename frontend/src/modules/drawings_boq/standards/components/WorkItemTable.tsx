import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useUpdateWorkItem } from "../hooks";
import type { WorkItem } from "../types/standards.types";

export function WorkItemTable({ workItems, canManage, onCreate }: { workItems: WorkItem[]; canManage: boolean; onCreate: () => void }) {
  const updateWorkItem = useUpdateWorkItem();
  const { showToast } = useToast();

  return (
    <Panel>
      <PanelHeader eyebrow="CATALOG" title="Work items" description="The coded items that mappings and recipes emit. System items are read-only." action={canManage ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />New work item</Button> : null} />
      {workItems.length === 0 ? (
        <EmptyState icon="budget" title="No work items yet" description="Run the standards seed, or create your own." action={canManage ? <Button variant="primary" size="sm" onClick={onCreate}>New work item</Button> : undefined} />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">Code</th><th className="px-4 py-3">Description</th><th className="px-4 py-3">Unit</th><th className="px-4 py-3">Trade</th><th className="px-4 py-3">Material class</th><th className="px-4 py-3">Source</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
            <tbody>
              {workItems.map((w) => (
                <tr key={w.id} className="border-t border-[var(--color-border)]">
                  <td className="px-4 py-3.5 font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">{w.code}</td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{w.description}</td>
                  <td className="px-4 py-3.5"><Badge tone="blue">{w.unit}</Badge></td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{w.trade ?? "—"}</td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{typeof w.extra?.material_class === "string" ? w.extra.material_class : "—"}</td>
                  <td className="px-4 py-3.5"><Badge tone={w.is_system ? "slate" : "green"}>{w.is_system ? "System" : "Custom"}</Badge></td>
                  <td className="px-4 py-3.5 text-right">
                    {canManage && !w.is_system && w.organization_id !== null ? (
                      <Button variant="ghost" size="sm" onClick={() => updateWorkItem.mutate({ id: w.id, payload: { is_active: false } }, {
                        onSuccess: () => showToast({ tone: "success", title: "Work item deactivated" }),
                        onError: (e) => showToast({ tone: "error", title: "Couldn't update this work item", description: getApiErrorMessage(e, "Please try again.") }),
                      })}>Deactivate</Button>
                    ) : <span className="text-[11px] text-[var(--color-text-muted)]">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}

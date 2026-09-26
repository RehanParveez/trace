import { useState } from "react";
import { Badge, Button, EmptyState, Panel, PanelHeader, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { usePunchList, useUpdatePunchListItem, useClosePunchList } from "../hooks";
import { PunchListItemForm } from "./PunchListItemForm";
import { PunchListPhotoPicker } from "./PunchListPhotoPicker";
import { formatPunchListDate, formatPunchListItemStatus, getPunchListItemStatusTone, getPunchListStatusTone } from "../utils/punch-list.utils";
import type { PunchListItemStatus } from "../types/punch-list.types";

export function PunchListDetailPanel({ projectId, punchListId, canManage }: {
  projectId: string; punchListId: string; canManage: boolean;
}) {
  const punchListQuery = usePunchList(punchListId);
  const updateItem = useUpdatePunchListItem(projectId, punchListId);
  const closeList = useClosePunchList(projectId);
  const { showToast } = useToast();
  const [itemFormOpen, setItemFormOpen] = useState(false);

  const punchList = punchListQuery.data;
  if (!punchList) return null;

  const openItems = punchList.items.filter((i) => i.status === "OPEN" || i.status === "IN_PROGRESS").length;

  return (
    <Panel>
      <PanelHeader
        eyebrow={formatPunchListDate(punchList.inspection_date)}
        title={punchList.title}
        description={`${punchList.items.length} item(s), ${openItems} open`}
        action={
          canManage ? (
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setItemFormOpen(true)} disabled={punchList.status === "CLOSED"}>Add item</Button>
              {punchList.status === "OPEN" ? (
                <Button
                  variant="primary" size="sm" disabled={closeList.isPending || openItems > 0}
                  title={openItems > 0 ? "Resolve or waive every item first" : undefined}
                  onClick={() => closeList.mutate(punchList.id, { onSuccess: () => showToast({ tone: "success", title: "Punch list closed" }) })}
                >
                  Close list
                </Button>
              ) : <Badge tone="green">Closed</Badge>}
            </div>
          ) : <Badge tone={getPunchListStatusTone(punchList.status)}>{punchList.status}</Badge>
        }
      />

      {punchList.items.length === 0 ? (
        <EmptyState icon="check" title="No items yet" description="Add each defect found during this inspection round." action={canManage ? <Button variant="primary" size="sm" onClick={() => setItemFormOpen(true)}>Add item</Button> : undefined} />
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {punchList.items.map((item) => (
            <div key={item.id} className="space-y-3 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{item.location}</div>
                  <div className="mt-0.5 text-[12.5px] text-[var(--color-text-secondary)]">{item.description}</div>
                  {item.due_date ? <div className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">Due {formatPunchListDate(item.due_date)}</div> : null}
                </div>
                {canManage ? (
                  <select
                    className="rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12px] outline-none"
                    value={item.status}
                    onChange={(e) => updateItem.mutate({ itemId: item.id, payload: { status: e.target.value as PunchListItemStatus } }, {
                      onError: (err) => showToast({ tone: "error", title: "Couldn't update status", description: getApiErrorMessage(err, "Please try again.") }),
                    })}
                  >
                    <option value="OPEN">Open</option>
                    <option value="IN_PROGRESS">In progress</option>
                    <option value="RESOLVED">Resolved</option>
                    <option value="WAIVED">Waived</option>
                  </select>
                ) : (
                  <Badge tone={getPunchListItemStatusTone(item.status)}>{formatPunchListItemStatus(item.status)}</Badge>
                )}
              </div>

              <PunchListPhotoPicker projectId={projectId} punchListId={punchListId} item={item} canManage={canManage} />
            </div>
          ))}
        </div>
      )}

      {itemFormOpen ? <PunchListItemForm projectId={projectId} punchListId={punchListId} onClose={() => setItemFormOpen(false)} /> : null}
    </Panel>
  );
}
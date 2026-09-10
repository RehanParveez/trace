import {
  Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell,
} from "../../organizations/components/OrganizationUi";
import type { ProcurementRequest } from "../types/procurement.types";
import {formatNextProcurementActionLabel, formatProcurementAmount, formatProcurementDate, formatProcurementStatus, getProcurementStatusTone, PROCUREMENT_NEXT_STATUS,
} from "../utils/procurement.utils";
import { useUpdateProcurementStatus } from "../hooks";

interface ProcurementTableProps {
  requests: ProcurementRequest[];
  canCreate: boolean;
  canManage: boolean;
  onCreate: () => void;
}

export function ProcurementTable({ requests, canCreate, canManage, onCreate }: ProcurementTableProps) {
  const updateStatus = useUpdateProcurementStatus();

  return (
    <Panel>
      <PanelHeader
        eyebrow="MATERIAL PROCUREMENT"
        title="Procurement requests"
        description="Request → approval → purchase → receipt, tracked in one place."
        action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />New request</Button> : null}
      />

      {requests.length === 0 ? (
        <EmptyState
          icon="procurement"
          title="No procurement requests yet"
          description="Material requests raised for this project will appear here."
          action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>New request</Button> : undefined}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Material</th>
                <th className="px-4 py-3 text-right">Quantity</th>
                <th className="px-4 py-3 text-right">Est. cost</th>
                <th className="px-4 py-3">Needed by</th>
                <th className="px-4 py-3">Status</th>
                {canManage ? <th className="px-4 py-3 text-right">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => {
                const nextStatus = PROCUREMENT_NEXT_STATUS[request.status];
                const nextLabel = formatNextProcurementActionLabel(request.status);

                return (
                  <tr key={request.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                    <td className="px-4 py-3.5">
                      <span className="block text-[13.5px] font-semibold text-[var(--color-text-primary)]">{request.material_name}</span>
                      {request.notes ? <span className="mt-0.5 block max-w-[280px] truncate text-[12px] text-[var(--color-text-secondary)]">{request.notes}</span> : null}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-primary)]">{request.quantity} {request.unit}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-primary)]">{formatProcurementAmount(request.estimated_amount)}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatProcurementDate(request.needed_by_date)}</td>
                    <td className="px-4 py-3.5"><Badge tone={getProcurementStatusTone(request.status)}>{formatProcurementStatus(request.status)}</Badge></td>
                    {canManage ? (
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex justify-end gap-2">
                          {nextStatus && nextLabel ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              disabled={updateStatus.isPending}
                              onClick={() => updateStatus.mutate({ requestId: request.id, payload: { status: nextStatus } })}
                            >
                              {nextLabel}
                            </Button>
                          ) : null}
                          {request.status !== "CANCELLED" && request.status !== "RECEIVED" ? (
                            <Button
                              variant="danger"
                              size="sm"
                              disabled={updateStatus.isPending}
                              onClick={() => updateStatus.mutate({ requestId: request.id, payload: { status: "CANCELLED" } })}
                            >
                              Cancel
                            </Button>
                          ) : null}
                        </div>
                      </td>
                    ) : null}
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
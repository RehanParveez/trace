import {Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import type { ProcurementRequest } from "../types/procurement.types";
import {formatNextProcurementActionLabel, formatProcurementAmount, formatProcurementDate, formatProcurementStatus, getProcurementStatusTone, PROCUREMENT_NEXT_STATUS,
} from "../utils/procurement.utils";
import { useUpdateProcurementStatus } from "../hooks";
import { useTranslation } from "react-i18next";

interface ProcurementTableProps {
  requests: ProcurementRequest[];
  canCreate: boolean;
  canManage: boolean;
  onCreate: () => void;
}

export function ProcurementTable({ requests, canCreate, canManage, onCreate }: ProcurementTableProps) {
  const { t } = useTranslation();
  const updateStatus = useUpdateProcurementStatus();
  const { showToast } = useToast();

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("procurement.table.eyebrow")}
        title={t("procurement.table.title")}
        description={t("procurement.table.description")}
        action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />{t("procurement.table.new")}</Button> : null}
      />

      {requests.length === 0 ? (
        <EmptyState
          icon="procurement"
          title={t("procurement.table.emptyTitle")}
          description={t("procurement.table.emptyDesc")}
          action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>{t("procurement.table.new")}</Button> : undefined}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("procurement.table.colMaterial")}</th>
                <th className="px-4 py-3 text-right">{t("procurement.table.colQuantity")}</th>
                <th className="px-4 py-3 text-right">{t("procurement.table.colEstCost")}</th>
                <th className="px-4 py-3">{t("procurement.table.colNeededBy")}</th>
                <th className="px-4 py-3">{t("procurement.table.colStatus")}</th>
                {canManage ? <th className="px-4 py-3 text-right">{t("procurement.table.colActions")}</th> : null}
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
                              onClick={() =>
                                updateStatus.mutate(
                                  { requestId: request.id, payload: { status: nextStatus } },
                                  {
                                    onSuccess: () =>
                                      showToast({
                                        tone: "success",
                                        title: t("procurement.table.statusUpdated", {
                                          name: request.material_name,
                                          status: formatProcurementStatus(nextStatus).toLowerCase(),
                                        }),
                                      }),
                                    onError: (error) =>
                                      showToast({
                                        tone: "error",
                                        title: t("procurement.table.updateError"),
                                        description: getApiErrorMessage(
                                          error,
                                          t("procurement.table.updateErrorDesc"),
                                        ),
                                      }),
                                  },
                                )
                              }
                            >
                              {nextLabel}
                            </Button>
                          ) : null}
                          {request.status !== "CANCELLED" && request.status !== "RECEIVED" ? (
                            <Button
                              variant="danger"
                              size="sm"
                              disabled={updateStatus.isPending}
                              onClick={() =>
                                updateStatus.mutate(
                                  { requestId: request.id, payload: { status: "CANCELLED" } },
                                  {
                                    onSuccess: () =>
                                      showToast({
                                        tone: "success",
                                        title: t("procurement.table.cancelled", { name: request.material_name }),
                                      }),
                                    onError: (error) =>
                                      showToast({
                                        tone: "error",
                                        title: t("procurement.table.cancelError"),
                                        description: getApiErrorMessage(error, t("procurement.table.updateErrorDesc")),
                                      }),
                                  },
                                )
                              }
                            >
                              {t("common.cancel")}
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
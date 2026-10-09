import { useState } from "react";
import axios from "axios";
import {Badge, Button, EmptyState, ErrorState, Icon, LoadingState, Panel, PanelHeader, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import {useApproveBOQItem, useBOQItems, useConfirmBOQItemRate, useDeleteBOQItem, useUpdateBOQItem, useWaiveBOQItemReview,
} from "../hooks";
import type { BOQItem } from "../types/drawings-boq.types";
import { computeLineTotal, formatBOQItemStatus, formatBOQItemType, formatCurrency, formatQuantity,
} from "../utils/drawings-boq.utils";
import { BOQItemTraceDialog } from "./BOQItemTraceDialog";
import { BOQItemAdjustmentsDialog } from "./BOQItemAdjustmentsDialog";
import { OverrideFormDialog } from "../pricing/components/OverrideFormDialog";
import { RateExplainDialog } from "../pricing/components/RateExplainDialog";
import { RateSourceBadge } from "../pricing/components/RateSourceBadge";
import { formatFactor } from "../pricing/utils/pricing.utils";
import { useTranslation } from "react-i18next";

interface BOQItemTableProps {
  boqVersionId: string;
  isEngine?: boolean;
  canUpdate: boolean;
  canOverrideRate?: boolean;
  projectId?: string;
  canApprove: boolean;
  canAdjust?: boolean;
}

export function BOQItemTable({
  boqVersionId,
  isEngine = false,
  canUpdate,
  canApprove,
  canAdjust = false,
  canOverrideRate = false,
  projectId,
}: BOQItemTableProps) {
  const { t } =
    useTranslation();

  const itemsQuery =
    useBOQItems(
      boqVersionId,
    );

  const updateItem =
    useUpdateBOQItem(
      boqVersionId,
    );

  const approveItem =
    useApproveBOQItem(
      boqVersionId,
    );

  const confirmRate =
    useConfirmBOQItemRate(
      boqVersionId,
    );

  const waiveReview =
    useWaiveBOQItemReview(
      boqVersionId,
    );

  const deleteItem =
    useDeleteBOQItem(
      boqVersionId,
    );

  const onActionError = (error: unknown) =>
    setNotice(getApiErrorMessage(error, t("boq.items.actionError", "This action could not be completed.")));

  const { showToast } =
    useToast();

  const [editingId, setEditingId] =
    useState<string | null>(
      null,
    );

  const [traceItem, setTraceItem] =
    useState<BOQItem | null>(
      null,
    );

  const [adjustmentItem, setAdjustmentItem] =
    useState<BOQItem | null>(
      null,
    );

  const [notice, setNotice] =
    useState<string | null>(
      null,
    );

  const [explainItem, setExplainItem] =
    useState<BOQItem | null>(
      null,
    );

  const [overrideItem, setOverrideItem] =
    useState<BOQItem | null>(
      null,
    );

  const items =
    itemsQuery.data ?? [];

  function handleConflict() {
    setNotice(
      t("boq.items.conflict"),
    );

    void itemsQuery.refetch();
    setEditingId(null);
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t(
          "boq.items.eyebrow",
        )}
        title={t(
          "boq.items.title",
        )}
        description={t(
          "boq.items.description",
        )}
        action={
          <span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">
            {items.length}
          </span>
        }
      />

      {notice ? (
        <div className="border-b border-[var(--color-info)]/25 bg-[var(--color-info-bg)] px-5 py-3 text-[12px] text-[var(--color-info)]">
          {notice}
        </div>
      ) : null}

      {itemsQuery.isLoading ? (
        <LoadingState label={t("boq.items.loading")} />
      ) : itemsQuery.isError ? (
        <ErrorState
          title={t(
            "boq.items.loadError",
          )}
          onRetry={() =>
            void itemsQuery.refetch()
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon="building"
          title={t(
            "boq.items.emptyTitle",
          )}
          description={t(
            "boq.items.emptyDesc",
          )}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[1250px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">
                  {t(
                    "boq.items.colMaterial",
                  )}
                </th>

                <th className="px-4 py-3">
                  {t("boq.items.colType")}
                </th>

                <th className="px-4 py-3">
                  {t("boq.items.colWorkItem")}
                </th>

                <th className="px-4 py-3">
                  {t("boq.items.colUnit")}
                </th>

                <th className="px-4 py-3 text-right">
                  {t("boq.items.colQuantity")}
                </th>

                <th className="px-4 py-3 text-right">
                  {t("boq.items.colRate")}
                </th>

                <th className="px-4 py-3 text-right">
                  {t("boq.items.colTotal")}
                </th>

                <th className="px-4 py-3">
                  {t("boq.items.colReview")}
                </th>

                <th className="px-4 py-3">
                  {t("boq.items.colStatus")}
                </th>

                <th className="px-4 py-3 text-right">
                  {t("boq.items.colActions")}
                </th>
              </tr>
            </thead>

            <tbody>
              {items.map((item) =>
                editingId ===
                item.id ? (
                  <BOQItemEditRow
                    key={item.id}
                    item={item}
                    isSaving={
                      updateItem.isPending
                    }
                    onCancel={() =>
                      setEditingId(
                        null,
                      )
                    }
                    onSave={(
                      payload,
                    ) =>
                      updateItem.mutate(
                        {
                          itemId:
                            item.id,
                          payload: {
                            ...payload,
                            version:
                              item.version,
                          },
                        },
                        {
                          onSuccess:
                            () => {
                              setEditingId(
                                null,
                              );

                              setNotice(
                                null,
                              );

                              showToast(
                                {
                                  tone:
                                    "success",
                                  title:
                                    t(
                                      "boq.items.savedToast",
                                    ),
                                },
                              );
                            },
                          onError:
                            (
                              error,
                            ) => {
                              if (
                                axios.isAxiosError(
                                  error,
                                ) &&
                                error
                                  .response
                                  ?.status ===
                                  409
                              ) {
                                handleConflict();
                                return;
                              }

                              setNotice(
                                getApiErrorMessage(
                                  error,
                                  t(
                                    "boq.items.saveError",
                                  ),
                                ),
                              );
                            },
                        },
                      )
                    }
                  />
                ) : (
                  <tr
                    key={item.id}
                    className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]"
                  >
                    <td className="px-4 py-3.5">
                      <span className="block text-[14px] font-semibold text-[var(--color-text-primary)]">
                        {item.material_name}
                      </span>

                      {item.category ? (
                        <span className="mt-0.5 block text-[12px] text-[var(--color-text-secondary)]">
                          {item.category}
                        </span>
                      ) : null}
                    </td>

                    <td className="px-4 py-3.5 text-[12px] text-[var(--color-text-secondary)]">
                      {formatBOQItemType(
                        item.item_type,
                      )}
                    </td>

                    <td className="px-4 py-3.5 font-mono text-[11px] text-[var(--color-text-secondary)]">
                      {item.work_item_code ??
                        "—"}
                    </td>

                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">
                      {item.unit}
                    </td>

                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-primary)]">
                      {formatQuantity(
                        item.quantity,
                      )}
                    </td>

                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-primary)]">
                      {formatCurrency(
                        item.unit_rate,
                      )}
                      <div className="mt-1 flex flex-col items-end gap-0.5">
                        <RateSourceBadge
                          source={item.rate_source ?? null}
                          hasRate={item.unit_rate !== null}
                        />

                        {item.base_rate !== null &&
                        item.base_rate !== undefined &&
                        item.escalation_factor !== null &&
                        item.escalation_factor !== undefined ? (
                          <span className="text-[10.5px] font-normal text-[var(--color-text-muted)]">
                           {formatCurrency(item.base_rate)}{" "}
                            {formatFactor(item.escalation_factor)}
                          </span>
                        ) : null}
                      </div>
                    </td>

                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">
                      {formatCurrency(
                        computeLineTotal(
                          item.quantity,
                          item.unit_rate,
                        ),
                      )}
                    </td>

                    <td className="px-4 py-3.5">
                      {item.review_status ? (
                        <Badge
                          tone={
                            item.review_status ===
                            "OK"
                              ? "green"
                              : item.review_status ===
                                  "WAIVED"
                                ? "slate"
                                : "gold"
                          }
                        >
                          {
                            item.review_status
                          }
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </td>

                    <td className="px-4 py-3.5">
                      <Badge
                        tone={
                          item.status ===
                          "APPROVED"
                            ? "green"
                            : "slate"
                        }
                      >
                        {formatBOQItemStatus(
                          item.status,
                        )}
                      </Badge>
                    </td>

                    <td className="px-4 py-3.5">
                      <div className="flex flex-wrap justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setTraceItem(
                              item,
                            )
                          }
                        >
                          {t("boq.items.trace")}
                        </Button>

                        {item.source_kind !== "ESTIMATE" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setExplainItem(
                                item,
                              )
                            }
                          >
                            {t("boq.items.explainRate", "Rate source")}
                          </Button>
                        ) : null}

                        {canAdjust && item.source_kind === "MODEL" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setAdjustmentItem(
                                item,
                              )
                            }
                          >
                            {t("boq.items.adjust")}
                          </Button>
                        ) : null}

                        {canUpdate &&
                        item.status ===
                          "DRAFT" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setEditingId(
                                item.id,
                              )
                            }
                          >
                            <Icon
                              name="edit"
                              size={12}
                            />
                            {t(
                              "common.edit",
                            )}
                          </Button>
                        ) : null}

                        {canUpdate &&
                        item.status ===
                          "DRAFT" &&
                        item.unit_rate !==
                          null &&
                        item.rate_source ===
                          "AI_SUGGESTED" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={
                              confirmRate.isPending
                            }
                            onClick={() =>
                              confirmRate.mutate(
                                item.id,
                                { onError: onActionError },
                              )
                            }
                          >
                            {t("boq.items.confirmRate")}
                          </Button>
                        ) : null}

                        {canUpdate &&
                        item.review_status ===
                          "REVIEW_REQUIRED" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={
                              waiveReview.isPending
                            }
                            onClick={() => {
                              const reason =
                                window.prompt(
                                  t("boq.items.waivePrompt"),
                                );

                              if (
                                !reason?.trim()
                              ) {
                                return;
                              }

                              waiveReview.mutate(
                                {
                                  itemId:
                                    item.id,
                                  reason:
                                    reason.trim(),
                                },
                                { onError: onActionError },
                              );
                            }}
                          >
                            {t("boq.items.waive")}
                          </Button>
                        ) : null}

                        {canUpdate &&
                        item.status ===
                          "DRAFT" &&
                        item.source_kind !==
                          "MODEL" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={
                              deleteItem.isPending
                            }
                            onClick={() => {
                              if (!window.confirm(t("boq.items.deleteConfirm", "Delete this draft line?"))) return;
                              deleteItem.mutate(item.id, {
                                onSuccess: () => showToast({ tone: "success", title: t("boq.items.deletedToast", "Line deleted") }),
                                onError: onActionError,
                              });
                            }}
                          >
                            {t("boq.items.delete", "Delete")}
                          </Button>
                        ) : null}

                        {canApprove &&
                        !isEngine &&
                        item.status ===
                          "DRAFT" ? (
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={
                              approveItem.isPending
                            }
                            onClick={() =>
                              approveItem.mutate(
                                item.id,
                                {
                                  onSuccess:
                                    () =>
                                      showToast(
                                        {
                                          tone:
                                            "success",
                                          title:
                                            t(
                                              "boq.items.approvedToast",
                                              {
                                                name:
                                                  item.material_name,
                                              },
                                            ),
                                        },
                                      ),
                                  onError:
                                    (
                                      error,
                                    ) =>
                                      setNotice(
                                        getApiErrorMessage(
                                          error,
                                          t(
                                            "boq.items.approveError",
                                          ),
                                        ),
                                      ),
                                },
                              )
                            }
                          >
                            {t(
                              "boq.items.approve",
                            )}
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </TableShell>
      )}

      {traceItem ? (
        <BOQItemTraceDialog
          itemId={traceItem.id}
          itemName={
            traceItem.material_name
          }
          onClose={() =>
            setTraceItem(null)
          }
        />
      ) : null}

      {explainItem ? (
        <RateExplainDialog
          itemId={explainItem.id}
          itemName={explainItem.material_name}
          onOverride={
            canOverrideRate && projectId
              ? () => {
                  setOverrideItem(explainItem);
                  setExplainItem(null);
                }
              : undefined
          }
          onClose={() =>
            setExplainItem(null)
          }
        />
      ) : null}

      {overrideItem && projectId ? (
        <OverrideFormDialog
          projectId={projectId}
          defaults={{
            work_item_code: overrideItem.work_item_code,
            unit: overrideItem.unit,
            rate: overrideItem.unit_rate,
          }}
          onClose={() =>
            setOverrideItem(null)

          }
        />
      ) : null}

      {adjustmentItem ? (
        <BOQItemAdjustmentsDialog
          itemId={
            adjustmentItem.id
          }
          versionId={
            boqVersionId
          }
          itemName={
            adjustmentItem.material_name
          }
          unit={adjustmentItem.unit}
          netQuantity={adjustmentItem.net_quantity}
          quantity={adjustmentItem.quantity}
          canAdjust={
            canAdjust
          }
          onClose={() =>
            setAdjustmentItem(
              null,
            )
          }
        />
      ) : null}
    </Panel>
  );
}

interface BOQItemEditRowProps {
  item: BOQItem;
  isSaving: boolean;
  onCancel: () => void;
    onSave: (payload: {
    material_name: string;
    category: string | null;
    unit: string;
    quantity?: number;
    adjustment_reason?: string;
    unit_rate: number | null;
  }) => void;
}

function BOQItemEditRow({
  item,
  isSaving,
  onCancel,
  onSave,
}: BOQItemEditRowProps) {
  const { t } =
    useTranslation();

  const [materialName, setMaterialName] =
    useState(
      item.material_name,
    );

  const [category, setCategory] =
    useState(
      item.category ?? "",
    );

  const [unit, setUnit] =
    useState(item.unit);

  const [quantity, setQuantity] =
    useState(
      String(item.quantity),
    );

  const [unitRate, setUnitRate] =
    useState(
      item.unit_rate !== null
        ? String(item.unit_rate)
        : "",
    );

  const cls =
    "w-full rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12.5px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]";

  return (
    <tr className="border-t border-[var(--color-border)] bg-[var(--color-warning-bg)]">
      <td className="px-4 py-3">
        <input
          className={cls}
          value={materialName}
          onChange={(event) =>
            setMaterialName(
              event.target.value,
            )
          }
        />

        <input
          className={`${cls} mt-1.5`}
          placeholder={t(
            "boq.items.categoryPlaceholder",
          )}
          value={category}
          onChange={(event) =>
            setCategory(
              event.target.value,
            )
          }
        />
      </td>

      <td className="px-4 py-3 text-[12px] text-[var(--color-text-muted)]">
        {formatBOQItemType(
          item.item_type,
        )}
      </td>

      <td className="px-4 py-3 font-mono text-[11px]">
        {item.work_item_code ??
          "—"}
      </td>

      <td className="px-4 py-3">
        <input
          className={cls}
          value={unit}
          onChange={(event) =>
            setUnit(
              event.target.value,
            )
          }
        />
      </td>

      <td className="px-4 py-3">
        <input
          className={`${cls} text-right`}
          type="number"
          step="any"
          value={quantity}
          onChange={(event) =>
            setQuantity(
              event.target.value,
            )
          }
        />
      </td>

      <td className="px-4 py-3">
        <input
          className={`${cls} text-right`}
          type="number"
          step="any"
          placeholder="—"
          value={unitRate}
          onChange={(event) =>
            setUnitRate(
              event.target.value,
            )
          }
        />
      </td>

      <td className="px-4 py-3 text-right font-mono text-[12.5px] text-[var(--color-text-muted)]">
        {formatCurrency(
          computeLineTotal(
            quantity,
            unitRate === ""
              ? null
              : unitRate,
          ),
        )}
      </td>

      <td className="px-4 py-3" />

      <td className="px-4 py-3" />

      <td className="px-4 py-3">
        <div className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            disabled={isSaving}
          >
            {t("common.cancel")}
          </Button>

          <Button
            variant="primary"
            size="sm"
            disabled={
              isSaving ||
              !materialName.trim() ||
              !unit.trim() ||
              quantity === ""
            }
            onClick={() =>
              onSave({
                material_name:
                  materialName.trim(),
                category:
                  category.trim() ||
                  null,
                unit:
                  unit.trim(),
                ...(Number(quantity) !== Number(item.quantity)
                  ? {
                      quantity: Number(quantity),
                      adjustment_reason:
                        item.source_kind === "MODEL"
                          ? window.prompt(t("boq.items.adjustReasonPrompt", "Reason for changing the calculated quantity"))?.trim() || undefined
                          : undefined,
                    }
                  : {}),
                unit_rate:
                  unitRate === ""
                    ? null
                    : Number(
                        unitRate,
                      ),
              })
            }
          >
            {isSaving
              ? t(
                  "common.saving",
                )
              : t(
                  "common.save",
                )}
          </Button>
        </div>
      </td>
    </tr>
  );
}
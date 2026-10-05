import { useState } from "react";
import {Button, ErrorState, LoadingState, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import {useBOQItemAdjustments, useCreateBOQItemAdjustment, useRevokeBOQAdjustment,
} from "../hooks";
import type {AdjustmentKind,
} from "../types/drawings-boq.types";
import {formatQuantity,
} from "../utils/drawings-boq.utils";
import { useTranslation } from "react-i18next";

interface BOQItemAdjustmentsDialogProps {
  itemId: string;
  versionId: string;
  itemName: string;
  canAdjust: boolean;
  onClose: () => void;
}

export function BOQItemAdjustmentsDialog({
  itemId, versionId, itemName, canAdjust,
  onClose,
}: BOQItemAdjustmentsDialogProps) {
  const { t } = useTranslation();

  const query = useBOQItemAdjustments(itemId);
  const create =
    useCreateBOQItemAdjustment(itemId, versionId,
    );

  const revoke =
    useRevokeBOQAdjustment(itemId, versionId,
    );

  const { showToast } = useToast();

  const [kind, setKind] = useState<AdjustmentKind>(
      "DELTA",
    );

  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [revokeReason, setRevokeReason] = useState("");

  function submit() {const numericValue = Number(value);

    if (
      Number.isNaN(numericValue) ||
      !reason.trim()
    ) {
      return;
    }

    create.mutate(
      {
        kind,
        value: numericValue,
        reason: reason.trim(),
      },
      {
        onSuccess: () => {
          setValue("");
          setReason("");

          showToast({
            tone: "success",
            title:
              t("boq.itemAdjustments.adjustmentCreated"),
          });
        },
      },
    );
  }

  return (
    <Modal
      title={t("boq.itemAdjustments.title", { itemName })}
      description={t("boq.itemAdjustments.description")}
      onClose={onClose}
      wide
    >
      {query.isLoading ? (
        <LoadingState label={t("boq.itemAdjustments.loading")} />
      ) : query.isError ? (
        <ErrorState
          title={t("boq.itemAdjustments.loadError")}
          onRetry={() =>
            void query.refetch()
          }
        />
      ) : (
        <div className="space-y-5">
          <div className="space-y-2">
            {(
              query.data ?? []
            ).map((adjustment) => (
              <div
                key={adjustment.id}
                className="rounded-[8px] border border-[var(--color-border)] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex gap-2">
                    <span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 text-[10px] font-semibold text-[var(--color-text-secondary)]">
                      {adjustment.kind === "DELTA"
                        ? t("boq.itemAdjustments.kindDelta")
                        : t("boq.itemAdjustments.kindReplace")}
                    </span>

                    <span className="font-mono text-[12px] font-semibold text-[var(--color-text-primary)]">
                      {formatQuantity(
                        adjustment.value,
                      )}
                    </span>
                  </div>

                  {adjustment.revoked_at ? (
                    <span className="text-[10px] text-[var(--color-text-muted)]">
                      {t("boq.itemAdjustments.revoked")}
                    </span>
                  ) : canAdjust ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={
                        revoke.isPending
                      }
                      onClick={() => {
                        const fallback =
                          window.prompt(
                            t("boq.itemAdjustments.revokePrompt"),
                          );

                        const finalReason =
                          fallback?.trim() ||
                          revokeReason.trim();

                        if (
                          !finalReason
                        ) {
                          return;
                        }

                        revoke.mutate({
                          adjustmentId:
                            adjustment.id,
                          reason:
                            finalReason,
                        });
                      }}
                    >
                      {t("boq.itemAdjustments.revoke")}
                    </Button>
                  ) : null}
                </div>

                <div className="mt-2 text-[12px] text-[var(--color-text-secondary)]">
                  {adjustment.reason}
                </div>

                {adjustment.revoke_reason ? (
                  <div className="mt-2 text-[11px] text-[var(--color-text-muted)]">
                    {t("boq.itemAdjustments.revokeReasonLabel")}{" "}
                    {adjustment.revoke_reason}
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          {canAdjust ? (
            <div className="border-t border-[var(--color-border)] pt-5">
              <div className="mb-3 text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                {t("boq.itemAdjustments.addAdjustment")}
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <label className="block">
                  <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                    {t("boq.itemAdjustments.kind")}
                  </span>

                  <select
                    value={kind}
                    onChange={(event) =>
                      setKind(
                        event.target
                          .value as AdjustmentKind,
                      )
                    }
                    className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
                  >
                    <option value="DELTA">
                      {t("boq.itemAdjustments.kindDelta")}
                    </option>
                    <option value="REPLACE">
                      {t("boq.itemAdjustments.kindReplace")}
                    </option>
                  </select>
                </label>

                <label className="block">
                  <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                    {t("boq.itemAdjustments.value")}
                  </span>

                  <input
                    type="number"
                    step="any"
                    value={value}
                    onChange={(event) =>
                      setValue(
                        event.target.value,
                      )
                    }
                    className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
                  />
                </label>

                <label className="block">
                  <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                    {t("boq.itemAdjustments.reason")}
                  </span>

                  <input
                    value={reason}
                    onChange={(event) =>
                      setReason(
                        event.target.value,
                      )
                    }
                    className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
                  />
                </label>
              </div>

              <div className="mt-3 flex justify-end">
                <Button
                  variant="primary"
                  disabled={
                    create.isPending ||
                    value === "" ||
                    !reason.trim()
                  }
                  onClick={submit}
                >
                  {create.isPending
                    ? t("boq.itemAdjustments.saving")
                    : t("boq.itemAdjustments.addAdjustment")}
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </Modal>
  );
}
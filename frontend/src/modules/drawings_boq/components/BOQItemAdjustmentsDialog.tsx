import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import {Badge, Button, ErrorState, Field, inputClass, LoadingState, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import {useBOQItemAdjustments, useCreateBOQItemAdjustment, useRevokeBOQAdjustment,
} from "../hooks";
import type { AdjustmentKind } from "../types/drawings-boq.types";
import { formatQuantity } from "../utils/drawings-boq.utils";
import { useTranslation } from "react-i18next";
import { ReasonDialog } from "./ReasonDialog";

interface BOQItemAdjustmentsDialogProps {
  itemId: string;
  versionId: string;
  itemName: string;
  unit?: string;
  netQuantity?: number | string | null;
  quantity?: number | string;
  canAdjust: boolean;
  editable?: boolean;
  onClose: () => void;
}
export function BOQItemAdjustmentsDialog({
  itemId,
  versionId,
  itemName,
  unit = "",
  netQuantity,
  quantity,
  canAdjust,
  editable = true,
  onClose,
}: BOQItemAdjustmentsDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();

  const query = useBOQItemAdjustments(itemId);
  const create = useCreateBOQItemAdjustment(itemId, versionId);
  const revoke = useRevokeBOQAdjustment(itemId, versionId);

  const [kind, setKind] = useState<AdjustmentKind>("DELTA");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<{
    id: string;
    kind: AdjustmentKind;
    value: number | string;
  } | null>(null);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  const rows = query.data ?? [];
  const active = useMemo(
    () => rows.filter((a) => !a.revoked_at),
    [rows],
  );
  const hasActiveReplace = active.some((a) => a.kind === "REPLACE");

  const net = Number(netQuantity ?? quantity ?? 0);
  const current = useMemo(() => {
    let q = net;
    for (const a of active) {
      const v = Number(a.value);
      if (a.kind === "REPLACE") q = v;
      else q += v;
    }
    return q;
  }, [net, active]);

  const numeric = value === "" ? null : Number(value);
  const previewValid =
    numeric !== null &&
    !Number.isNaN(numeric) &&
    !(kind === "REPLACE" && numeric < 0) &&
    !(kind === "REPLACE" && hasActiveReplace);

  const preview = previewValid
    ? kind === "REPLACE"
      ? numeric
      : current + (numeric as number)
    : null;

  const canSubmit =
    previewValid && reason.trim().length > 0 && !create.isPending;
  const mutable = canAdjust && editable;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit || numeric === null) return;

    setError(null);
    create.mutate(
      {
        kind,
        value: numeric,
        reason: reason.trim(),
      },
      {
        onSuccess: () => {
          setValue("");
          setReason("");
          showToast({
            tone: "success",
            title: t("boq.itemAdjustments.adjustmentCreated"),
          });
        },
        onError: () => {
          setError(
            t("boq.itemAdjustments.addError", "Couldn't add this adjustment."),
          );
        },
      },
    );
  }

  function confirmRevoke(text: string) {
    if (!revoking) return;
    setRevokeError(null);

    revoke.mutate(
      {
        adjustmentId: revoking.id,
        reason: text,
      },
      {
        onSuccess: () => {
          setRevoking(null);
          showToast({
            tone: "success",
            title: t("boq.itemAdjustments.revoked", "Adjustment revoked"),
          });
        },
        onError: () => {
          setRevokeError(
            t("boq.itemAdjustments.revokeError", "Couldn't revoke this adjustment."),
          );
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
          onRetry={() => void query.refetch()}
        />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-3 gap-3 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
            <div>
              <div className="font-mono text-[16px] font-semibold">
                {formatQuantity(net)}
              </div>
              <div className="text-[11px] text-[var(--color-text-muted)]">
                {t("boq.itemAdjustments.calculated", "Calculated")} {unit && `(${unit})`}
              </div>
            </div>
            <div>
              <div className="font-mono text-[16px] font-semibold">
                {formatQuantity(current - net)}
              </div>
              <div className="text-[11px] text-[var(--color-text-muted)]">
                {t("boq.itemAdjustments.netAdjustments", "Net adjustments")}
              </div>
            </div>
            <div>
              <div className="font-mono text-[16px] font-semibold">
                {formatQuantity(current)}
              </div>
              <div className="text-[11px] text-[var(--color-text-muted)]">
                {t("boq.itemAdjustments.contractQuantity", "Contract quantity")}
              </div>
            </div>
          </div>

          {rows.length === 0 ? (
            <p className="text-[12.5px] text-[var(--color-text-secondary)]">
              {t("boq.itemAdjustments.none", "No adjustments yet.")}
            </p>
          ) : (
            <ul className="divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
              {rows.map((adjustment) => (
                <li
                  key={adjustment.id}
                  className={`flex flex-wrap items-start justify-between gap-3 px-4 py-3 ${
                    adjustment.revoked_at ? "opacity-60" : ""
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge tone={adjustment.kind === "REPLACE" ? "blue" : "slate"}>
                        {adjustment.kind === "DELTA"
                          ? t("boq.itemAdjustments.kindDelta")
                          : t("boq.itemAdjustments.kindReplace")}
                      </Badge>
                      <span
                        className={`font-mono text-[13px] font-semibold ${
                          adjustment.revoked_at ? "line-through" : ""
                        }`}
                      >
                        {adjustment.kind === "DELTA" && Number(adjustment.value) > 0
                          ? "+"
                          : ""}
                        {formatQuantity(adjustment.value)} {unit}
                      </span>
                      {adjustment.revoked_at ? (
                        <Badge tone="red">
                          {t("boq.itemAdjustments.revoked")}
                        </Badge>
                      ) : null}
                    </div>
                    <p className="text-[12px] text-[var(--color-text-secondary)]">
                      {adjustment.reason}
                    </p>
                    {adjustment.revoke_reason ? (
                      <p className="text-[11.5px] italic text-[var(--color-text-muted)]">
                        {t("boq.itemAdjustments.revokeReasonLabel")}:{" "}
                        {adjustment.revoke_reason}
                      </p>
                    ) : null}
                  </div>

                  {mutable && !adjustment.revoked_at ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setRevokeError(null);
                        setRevoking({
                          id: adjustment.id,
                          kind: adjustment.kind,
                          value: adjustment.value,
                        });
                      }}
                    >
                      {t("boq.itemAdjustments.revoke")}
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}

          {mutable ? (
            <form
              onSubmit={submit}
              className="space-y-3 border-t border-[var(--color-border)] pt-4"
            >
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("boq.itemAdjustments.kind")}>
                  <select
                    className={inputClass}
                    value={kind}
                    onChange={(e) =>
                      setKind(e.target.value as AdjustmentKind)
                    }
                  >
                    <option value="DELTA">
                      {t("boq.itemAdjustments.kindDelta")}
                    </option>
                    <option value="REPLACE" disabled={hasActiveReplace}>
                      {t("boq.itemAdjustments.kindReplace")}
                    </option>
                  </select>
                </Field>

                <Field
                  label={
                    kind === "DELTA"
                      ? t("boq.itemAdjustments.deltaValue", {
                          unit,
                          defaultValue: `Amount (${unit}, negative to subtract)`,
                        })
                      : t("boq.itemAdjustments.replaceValue", {
                          unit,
                          defaultValue: `New quantity (${unit})`,
                        })
                  }
                >
                  <input
                    className={inputClass}
                    type="number"
                    step="any"
                    min={kind === "REPLACE" ? 0 : undefined}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                  />
                </Field>
              </div>

              {hasActiveReplace ? (
                <p className="text-[11.5px] text-[var(--color-text-muted)]">
                  {t(
                    "boq.itemAdjustments.oneReplace",
                    "Only one replacement can be active. Revoke it to add another.",
                  )}
                </p>
              ) : null}

              <Field label={t("boq.itemAdjustments.reason")}>
                <textarea
                  className={`${inputClass} min-h-[72px]`}
                  maxLength={1000}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Field>

              {preview !== null ? (
                <p className="text-[12.5px] text-[var(--color-text-secondary)]">
                  {t("boq.itemAdjustments.preview", "Contract quantity becomes")}{" "}
                  <span className="font-mono font-semibold text-[var(--color-text-primary)]">
                    {formatQuantity(preview)} {unit}
                  </span>
                  {preview < 0 ? (
                    <span className="ml-2 text-[var(--color-warning)]">
                      {t("boq.itemAdjustments.negative", "This is below zero.")}
                    </span>
                  ) : null}
                </p>
              ) : null}

              {error ? (
                <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
                  {error}
                </div>
              ) : null}

              <div className="flex justify-end">
                <Button type="submit" variant="primary" disabled={!canSubmit}>
                  {create.isPending
                    ? t("boq.itemAdjustments.saving")
                    : t("boq.itemAdjustments.addAdjustment")}
                </Button>
              </div>
            </form>
          ) : (
            <p className="border-t border-[var(--color-border)] pt-4 text-[12px] text-[var(--color-text-muted)]">
              {!editable
                ? t(
                    "boq.itemAdjustments.locked",
                    "This version is locked. Reopen it to change quantities.",
                  )
                : t(
                    "boq.itemAdjustments.noPermission",
                    "You don't have permission to adjust quantities.",
                  )}
            </p>
          )}
        </div>
      )}

      {revoking ? (
        <ReasonDialog
          title={t("boq.itemAdjustments.revokeTitle", "Revoke adjustment")}
          description={`${revoking.kind} ${formatQuantity(revoking.value)} ${unit}`}
          label={t("boq.itemAdjustments.revokeLabel", "Reason for revoking")}
          required
          confirmLabel={
            revoke.isPending
              ? t("common.saving", "Saving…")
              : t("boq.itemAdjustments.revoke")
          }
          pending={revoke.isPending}
          error={revokeError}
          onConfirm={confirmRevoke}
          onClose={() => setRevoking(null)}
        />
      ) : null}
    </Modal>
  );
}
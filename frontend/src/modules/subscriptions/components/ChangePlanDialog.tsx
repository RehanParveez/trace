import { useEffect, useMemo, useState } from "react";
import type { BillingInterval, Plan,
} from "../types/subscription.types";
import {Badge, Button, Field, Icon, Modal,
} from "../../organizations/components/OrganizationUi";
import { formatPrice } from "../utils/subscription.utils";

interface ChangePlanDialogProps {
  plans: Plan[];
  currentPlanId: string;
  initialPlan?: Plan;
  isSubmitting?: boolean;
  onSubmit: (
    planId: string,
    billingInterval: BillingInterval,
    idempotencyKey: string,
  ) => void;
  onClose: () => void;
}

export function ChangePlanDialog({
  plans,
  currentPlanId,
  initialPlan,
  isSubmitting = false,
  onSubmit,
  onClose,
}: ChangePlanDialogProps) {
  const [planId, setPlanId] = useState(
    initialPlan?.id ??
      plans.find(
        (plan) => plan.id !== currentPlanId,
      )?.id ??
      "",
  );

  const [billingInterval, setBillingInterval] =
    useState<BillingInterval>("MONTHLY");
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  useEffect(() => {
    setPlanId(
      initialPlan?.id ??
        plans.find(
          (plan) => plan.id !== currentPlanId,
        )?.id ??
        "",
    );
  }, [initialPlan, currentPlanId, plans]);

  const selectedPlan = plans.find(
    (plan) => plan.id === planId,
  );

  return (
    <Modal
      title="Change subscription plan"
      description="Choose the plan and billing interval to apply to this organization."
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();

          if (!planId) {
            return;
          }

          onSubmit(
            planId,
            billingInterval,
            idempotencyKey,
          );
        }}
      >
        <div className="space-y-5">
          <Field label="Plan">
            <div className="space-y-2.5">
              {plans.map((plan) => {
                const selected =
                  plan.id === planId;

                return (
                  <label
                    key={plan.id}
                    className={`flex cursor-pointer items-center gap-3.5 rounded-[var(--radius-md)] border p-3.5 transition ${
                      selected
                        ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] shadow-[0_4px_14px_rgba(80,60,20,0.05)]"
                        : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-muted)]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="plan"
                      value={plan.id}
                      checked={selected}
                      onChange={() =>
                        setPlanId(plan.id)
                      }
                      className="sr-only"
                    />

                    <div
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] ${
                        selected
                          ? "bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                          : "bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]"
                      }`}
                    >
                      <Icon
                        name="building"
                        size={14}
                      />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">
                          {plan.name}
                        </span>

                        {plan.id ===
                        currentPlanId ? (
                          <Badge tone="green">
                            Current
                          </Badge>
                        ) : null}
                      </div>

                      <div className="mt-1 text-[12px] leading-4 text-[var(--color-text-secondary)]">
                        {plan.description}
                      </div>
                    </div>

                    <div className="shrink-0 text-right">
                      <div className="font-mono text-[12px] font-semibold text-[var(--color-text-primary)]">
                        {formatPrice(
                          billingInterval ===
                            "YEARLY"
                            ? plan.price_yearly
                            : plan.price_monthly,
                          plan.currency,
                        )}
                      </div>

                      <div className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">
                        {billingInterval ===
                        "YEARLY"
                          ? "per year"
                          : "per month"}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          </Field>

          <Field label="Billing interval">
            <div className="grid grid-cols-2 gap-2.5">
              {(
                [
                  "MONTHLY",
                  "YEARLY",
                ] as BillingInterval[]
              ).map((interval) => {
                const selected =
                  billingInterval === interval;

                return (
                  <button
                    key={interval}
                    type="button"
                    onClick={() =>
                      setBillingInterval(
                        interval,
                      )
                    }
                    className={`rounded-[9px] border px-3.5 py-3 text-left transition ${
                      selected
                        ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]"
                        : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-muted)]"
                    }`}
                  >
                    <div
                      className={`text-[13px] font-semibold ${
                        selected
                          ? "text-[var(--color-text-primary)]"
                          : "text-[var(--color-text-primary)]"
                      }`}
                    >
                      {interval === "YEARLY"
                        ? "Yearly"
                        : "Monthly"}
                    </div>

                    <div className="mt-1 text-[11px] text-[var(--color-text-secondary)]">
                      {interval === "YEARLY"
                        ? "Annual billing"
                        : "Monthly billing"}
                    </div>
                  </button>
                );
              })}
            </div>
          </Field>

          {selectedPlan ? (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] p-3.5">
              <div className="flex gap-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-[var(--color-surface)] text-[var(--color-info)]">
                  <Icon
                    name="settings"
                    size={13}
                  />
                </div>

                <div className="text-[12px] leading-5 text-[var(--color-info)]">
                  Changing to{" "}
                  <strong className="font-semibold">
                    {selectedPlan.name}
                  </strong>{" "}
                  will update the organization's
                  subscription plan.
                </div>
              </div>
            </div>
          ) : null}

          <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="primary"
              disabled={
                isSubmitting ||
                !planId ||
                planId === currentPlanId
              }
            >
              {isSubmitting
                ? "Saving…"
                : "Save plan"}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
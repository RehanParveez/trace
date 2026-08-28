import { useEffect, useState } from "react";
import type {BillingInterval, Plan,
} from "../types/subscription.types";
import {Badge, Button, Field, Icon, Modal,
} from "../../organizations/components/OrganizationUi";
import {formatPrice,
} from "../utils/subscription.utils";

interface ChangePlanDialogProps {
  plans: Plan[];
  currentPlanId: string;
  initialPlan?: Plan;
  isSubmitting?: boolean;
  onSubmit: (
    planId: string,
    billingInterval: BillingInterval,
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
          );
        }}
      >
        <div className="space-y-4">
          <Field label="Plan">
            <div className="space-y-2">
              {plans.map((plan) => {
                const selected =
                  plan.id === planId;

                return (
                  <label
                    key={plan.id}
                    className={`flex cursor-pointer items-center gap-3 rounded-[9px] border p-3 transition ${
                      selected
                        ? "border-[#c6a449] bg-[#fff8e8]"
                        : "border-[#e1d5bc] bg-white hover:bg-[#f5efe3]"
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

                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-[#efe6d3] text-[#6b6152]">
                      <Icon
                        name="building"
                        size={14}
                      />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[12px] font-semibold text-[#191410]">
                          {plan.name}
                        </span>

                        {plan.id ===
                        currentPlanId ? (
                          <Badge tone="green">
                            Current
                          </Badge>
                        ) : null}
                      </div>

                      <div className="mt-0.5 text-[10.5px] text-[#6b6152]">
                        {plan.description}
                      </div>
                    </div>

                    <div className="shrink-0 font-mono text-[10.5px] font-semibold text-[#332a21]">
                      {formatPrice(
                        billingInterval ===
                          "YEARLY"
                          ? plan.price_yearly
                          : plan.price_monthly,
                        plan.currency,
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          </Field>

          <Field label="Billing interval">
            <div className="grid grid-cols-2 gap-2">
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
                    className={`rounded-[8px] border px-3 py-2.5 text-left transition ${
                      selected
                        ? "border-[#c6a449] bg-[#fff8e8]"
                        : "border-[#e1d5bc] bg-white hover:bg-[#f5efe3]"
                    }`}
                  >
                    <div className="text-[11.5px] font-semibold text-[#332a21]">
                      {interval === "YEARLY"
                        ? "Yearly"
                        : "Monthly"}
                    </div>

                    <div className="mt-0.5 text-[10px] text-[#6b6152]">
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
            <div className="rounded-[9px] border border-[#cfe0f2] bg-[#e7f0fa] p-3">
              <div className="flex gap-2.5">
                <Icon
                  name="settings"
                  size={14}
                  className="mt-0.5 shrink-0 text-[#2c5c8f]"
                />

                <div className="text-[11px] leading-5 text-[#2c5c8f]">
                  Changing to{" "}
                  <strong>
                    {selectedPlan.name}
                  </strong>{" "}
                  will update the organization's
                  subscription plan.
                </div>
              </div>
            </div>
          ) : null}

          <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
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
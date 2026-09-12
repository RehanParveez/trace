import type { Plan } from "../types/subscription.types";
import {Badge, Icon, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import { formatPrice, formatQuota,
} from "../utils/subscription.utils";
import { useTranslation } from "react-i18next";

interface CurrentPlanCardProps {
  plan: Plan;
}

const quotaOrder = [
  "projects",
  "storage_bytes",
  "site_photos",
  "drawings",
  "ai_requests",
];

export function CurrentPlanCard({
  plan,
}: CurrentPlanCardProps) {
  const { t } = useTranslation();

  const quotas = quotaOrder.filter(
    (metric) =>
      Object.prototype.hasOwnProperty.call(
        plan.quotas,
        metric,
      ),
  );

  const features = Object.entries(
    plan.features ?? {},
  );

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow={t("subscription.planCard.eyebrow")}
        title={plan.name}
        description={
          plan.description ??
          t("subscription.planCard.fallbackDescription")
        }
        action={
          <Badge tone="blue">
            {formatPrice(plan.price_monthly, plan.currency)}
            {" "}
            {t("subscription.planCard.perMonth")}
          </Badge>
        }
      />

      <div className="grid gap-0 divide-y divide-[var(--color-border)] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <div className="p-5 sm:p-6">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            {t("subscription.planCard.quotas")}
          </div>

          <div className="mt-4 space-y-2.5">
            {quotas.length === 0 ? (
              <div className="rounded-[9px] border border-[#e1d5bc] bg-white px-3.5 py-3 text-[11px] text-[#6b6152]">
                {t("subscription.planCard.noQuotas")}
              </div>
            ) : (
              quotas.map((metric) => (
                <div
                  key={metric}
                  className="flex items-center justify-between gap-4 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-3"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-[var(--color-warning-bg)] text-[var(--color-warning)]">
                      <Icon
                        name="building"
                        size={12}
                      />
                    </div>

                    <span className="text-[13px] font-semibold text-[var(--color-text-primary)]">
                      {metric
                        .replaceAll("_", " ")
                        .replace(
                          /\b\w/g,
                          (letter) =>
                            letter.toUpperCase(),
                        )}
                    </span>
                  </div>

                  <span className="shrink-0 font-mono text-[12px] font-semibold text-[var(--color-text-secondary)]">
                    {formatQuota(
                      metric,
                      plan.quotas[metric],
                    )}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-5 sm:p-6">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            {t("subscription.planCard.capabilities")}
          </div>

          <div className="mt-4 space-y-2.5">
            {features.length === 0 ? (
              <div className="rounded-[9px] border border-[#e1d5bc] bg-white px-3.5 py-3 text-[11px] text-[#6b6152]">
                {t("subscription.planCard.noFeatures")}
              </div>
            ) : (
              features.map(([feature, enabled]) => (
                <div
                  key={feature}
                  className="flex items-center gap-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-3"
                >
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] ${
                      enabled
                        ? "bg-[var(--color-success-bg)] text-[var(--color-success)]"
                        : "bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]"
                    }`}
                  >
                    <Icon
                      name={
                        enabled
                          ? "check"
                          : "lock"
                      }
                      size={12}
                    />
                  </div>

                  <span className="text-[13px] font-semibold text-[var(--color-text-primary)]">
                    {feature
                      .replaceAll("_", " ")
                      .replace(
                        /\b\w/g,
                        (letter) =>
                          letter.toUpperCase(),
                      )}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}
import type { WeeklyBucket } from "../types/cash-flow.types";
import { formatCashFlowDate, formatCashFlowMoney } from "../utils/cash-flow.utils";
import { useTranslation } from "react-i18next";

export function CashFlowChart({ buckets, currency }: { buckets: WeeklyBucket[]; currency: string }) {
  const { t } = useTranslation();
  const maxAbs = Math.max(...buckets.map((b) => Math.max(Math.abs(Number(b.total_inflow)), Math.abs(Number(b.total_outflow)))), 1);

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex min-w-max items-end gap-3" style={{ height: 180 }}>
        {buckets.map((bucket) => {
          const inflowHeight = (Number(bucket.total_inflow) / maxAbs) * 70;
          const outflowHeight = (Number(bucket.total_outflow) / maxAbs) * 70;
          const isNegativeCumulative = Number(bucket.cumulative_net) < 0;
          return (
            <div key={bucket.week_start} className="flex w-16 flex-col items-center gap-1">
              <div className="flex h-[140px] w-full flex-col justify-end gap-0.5">
                <div className="rounded-t-[3px] bg-[var(--color-success)]" style={{ height: inflowHeight }} title={t("cashFlow.chart.inflowTitle", { amount: formatCashFlowMoney(bucket.total_inflow, currency) })} />
                <div className="rounded-b-[3px] bg-[var(--color-danger)]" style={{ height: outflowHeight }} title={t("cashFlow.chart.outflowTitle", { amount: formatCashFlowMoney(bucket.total_outflow, currency) })} />
              </div>
              <span className={`text-[9px] font-semibold ${isNegativeCumulative ? "text-[var(--color-danger)]" : "text-[var(--color-text-muted)]"}`}>
                {formatCashFlowDate(bucket.week_start)}
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex gap-4 border-t border-[var(--color-border)] pt-3 text-[11px]">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-[2px] bg-[var(--color-success)]" />{t("cashFlow.chart.inflow")}</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-[2px] bg-[var(--color-danger)]" />{t("cashFlow.chart.outflow")}</span>
      </div>
    </div>
  );
}
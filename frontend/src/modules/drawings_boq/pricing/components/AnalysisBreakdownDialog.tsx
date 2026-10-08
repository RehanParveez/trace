import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, LoadingState, Modal, TableShell, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { formatCurrency, formatQuantity } from "../../utils/drawings-boq.utils";
import { useAnalysisBreakdown, useApplyAnalysis, useComputeAnalysis } from "../hooks";
import type { RateAnalysis } from "../types/pricing.types";
import { COMPONENT_TYPE_LABEL, formatDate } from "../utils/pricing.utils";
import { FormError } from "./FormError";

interface AnalysisBreakdownDialogProps {
  bookId: string;
  analysis: RateAnalysis;
  editable: boolean;
  onClose: () => void;
}

export function AnalysisBreakdownDialog({ bookId, analysis, editable, onClose }: AnalysisBreakdownDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const breakdown = useAnalysisBreakdown(analysis.id);
  const compute = useComputeAnalysis(bookId);
  const apply = useApplyAnalysis(bookId);
  const [error, setError] = useState<string | null>(null);

  function runCompute() {
    setError(null);
    compute.mutate(analysis.id, {
      onSuccess: (saved) => {
        showToast({
          tone: "success",
          title: t("pricing.breakdown.computedToast", "Rate saved on the analysis"),
          description: formatCurrency(saved.computed_rate),
        });
      },
      onError: (e) => setError(getApiErrorMessage(e, t("pricing.breakdown.computeError", "Couldn't compute this analysis."))),
    });
  }

  function runApply() {
    setError(null);
    apply.mutate(analysis.id, {
      onSuccess: (item) => {
        showToast({
          tone: "success",
          title: t("pricing.breakdown.appliedToast", "Rate applied to the book"),
          description: `${item.work_item_code} · ${formatCurrency(item.rate)} / ${item.unit}`,
        });
        onClose();
      },
      onError: (e) => setError(getApiErrorMessage(e, t("pricing.breakdown.applyError", "Couldn't apply this analysis."))),
    });
  }

  const data = breakdown.data;

  return (
    <Modal
      title={t("pricing.breakdown.title", "Breakdown: {{code}}", { code: analysis.code })}
      description={analysis.description}
      onClose={onClose}
      wide
    >
      <div className="space-y-4">
        {breakdown.isLoading ? (
          <LoadingState label={t("pricing.breakdown.loading", "Working out the rate…")} />
        ) : breakdown.isError || !data ? (
          <FormError message={getApiErrorMessage(breakdown.error, t("pricing.breakdown.loadError", "This analysis can't be priced yet."))} />
        ) : (
          <>
            <TableShell>
              <table className="w-full min-w-[560px] text-left">
                <thead className="bg-[var(--color-surface)]">
                  <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                    <th className="px-3 py-2">{t("pricing.breakdown.colPart", "Component")}</th>
                    <th className="px-3 py-2 text-right">{t("pricing.breakdown.colCoef", "Coefficient")}</th>
                    <th className="px-3 py-2">{t("pricing.breakdown.colUnit", "Unit")}</th>
                    <th className="px-3 py-2 text-right">{t("pricing.breakdown.colRate", "Rate")}</th>
                    <th className="px-3 py-2 text-right">{t("pricing.breakdown.colAmount", "Amount")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lines.map((line) => (
                    <tr key={line.sequence} className="border-t border-[var(--color-border)]">
                      <td className="px-3 py-2.5 text-[12.5px]">
                        {line.description}{" "}
                        <Badge tone="slate">{t(`pricing.componentType.${line.component_type}`, COMPONENT_TYPE_LABEL[line.component_type] ?? line.component_type)}</Badge>
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{formatQuantity(line.coefficient)}</td>
                      <td className="px-3 py-2.5 font-mono text-[12.5px]">{line.unit}</td>
                      <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{formatCurrency(line.unit_rate)}</td>
                      <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{formatCurrency(line.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>

            <dl className="ml-auto grid max-w-sm grid-cols-2 gap-x-6 gap-y-1.5 text-[13px]">
              {Object.entries(data.cost_by_type).map(([type, amount]) => (
                <div key={type} className="col-span-2 flex justify-between text-[12.5px] text-[var(--color-text-secondary)]">
                  <dt>{t(`pricing.componentType.${type}`, COMPONENT_TYPE_LABEL[type as keyof typeof COMPONENT_TYPE_LABEL] ?? type)}</dt>
                  <dd className="font-mono">{formatCurrency(amount)}</dd>
                </div>
              ))}
              <dt className="font-semibold">{t("pricing.breakdown.cost", "Cost")}</dt>
              <dd className="text-right font-mono">{formatCurrency(data.cost)}</dd>
              <dt className="text-[var(--color-text-secondary)]">{t("pricing.breakdown.overhead", "Overhead ({{pct}}%)", { pct: Number(analysis.overhead_pct) })}</dt>
              <dd className="text-right font-mono">{formatCurrency(data.overhead)}</dd>
              <dt className="text-[var(--color-text-secondary)]">{t("pricing.breakdown.profit", "Profit ({{pct}}%)", { pct: Number(analysis.profit_pct) })}</dt>
              <dd className="text-right font-mono">{formatCurrency(data.profit)}</dd>
              <dt className="font-semibold">{t("pricing.breakdown.total", "Total for {{basis}} {{unit}}", { basis: formatQuantity(data.basis_quantity), unit: data.unit })}</dt>
              <dd className="text-right font-mono font-semibold">{formatCurrency(data.total)}</dd>
              <dt className="border-t border-[var(--color-border)] pt-2 font-bold">{t("pricing.breakdown.rate", "Rate per {{unit}}", { unit: data.unit })}</dt>
              <dd className="border-t border-[var(--color-border)] pt-2 text-right font-mono font-bold">{formatCurrency(data.rate)}</dd>
            </dl>

            <p className="text-[12px] text-[var(--color-text-muted)]">
              {analysis.computed_at
                ? t("pricing.breakdown.savedAt", "Saved rate on the analysis: {{rate}} ({{date}}).", {
                    rate: formatCurrency(analysis.computed_rate), date: formatDate(analysis.computed_at),
                  })
                : t("pricing.breakdown.notSaved", "This rate has not been saved on the analysis yet.")}
            </p>
          </>
        )}

        <FormError message={error} />

        <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={compute.isPending || apply.isPending}>{t("common.close", "Close")}</Button>
          {editable ? (
            <>
              <Button variant="secondary" onClick={runCompute} disabled={!data || compute.isPending || apply.isPending}>
                {compute.isPending ? t("common.saving", "Saving…") : t("pricing.breakdown.compute", "Save computed rate")}
              </Button>
              <Button variant="primary" onClick={runApply} disabled={!data || compute.isPending || apply.isPending}>
                {apply.isPending ? t("common.saving", "Saving…") : t("pricing.breakdown.apply", "Apply to the book's rates")}
              </Button>
            </>
          ) : null}
        </div>
      </div>
    </Modal>
  );
}

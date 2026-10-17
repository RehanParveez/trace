import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { StageReport } from "../types/drawings-boq.types";
import { gradeTone, rangeView } from "../utils/quantityRange";
import { formatPrecise, stageDescriptor } from "../utils/drawings-boq.utils";
import { useGradeLabel } from "../utils/gradeLabel";
import { RangeTotalsStrip } from "./RangeViews";

const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";

export function StageReportView({ report }: { report: StageReport }) {
  const { t } = useTranslation();
  const gradeLabel = useGradeLabel();
  if (report.stages.length === 0) {
    return (
      <div className="px-5 py-4 text-[12px] text-[var(--color-text-secondary)]" data-testid="stage-report-empty">
        {t("boq.stageReport.empty", "There are no quantities to report by stage yet.")}
      </div>
    );
  }
  return (
    <div data-testid="stage-report">
      {report.stages.map((st) => {
        const d = st.stage === "NOT_SPLIT" ? null : stageDescriptor(st.stage);
        const label = d ? t(d.key, { defaultValue: d.fallback, n: d.n }) : t("boq.stageReport.notSplit", "Not split by stage");
        return (
          <section key={st.stage} className="border-b border-[var(--color-border)] px-5 py-4" data-testid={`stage-${st.stage}`}>
            <h3 className="text-[13px] font-bold text-[var(--color-text-primary)]">{label}</h3>
            {st.trades.map((tr) => (
              <div key={tr.trade} className="mt-3" data-testid={`stage-${st.stage}-trade-${tr.trade}`}>
                <div className={HEAD}>{tr.trade}</div>
                <div className="mt-1 overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
                  <table className="w-full text-[12px]">
                    <thead>
                      <tr className="bg-[var(--color-surface-muted)] text-left">
                        <th className={`${HEAD} px-3 py-2`}>{t("boq.stageReport.colItem", "Item")}</th>
                        <th className={`${HEAD} px-3 py-2`}>{t("boq.stageReport.colUnit", "Unit")}</th>
                        <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.stageReport.colQuantity", "Quantity")}</th>
                        <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.stageReport.colRange", "Range")}</th>
                        <th className={`${HEAD} px-3 py-2`}>{t("boq.stageReport.colBasis", "Weakest input")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tr.items.map((it) => {
                        const v = rangeView(it.quantity_range);
                        return (
                          <tr key={it.item_id} className="border-t border-[var(--color-border)]" data-testid={`stage-item-${it.item_id}`}>
                            <td className="px-3 py-1.5">
                              {it.name}
                              {it.derived ? (
                                <span className="ml-2 rounded-full bg-[var(--color-surface-muted)] px-2 py-0.5 text-[10px] text-[var(--color-text-secondary)]">
                                  {t("boq.stageReport.derived", "derived")}
                                </span>
                              ) : null}
                            </td>
                            <td className="px-3 py-1.5">{it.unit}</td>
                            <td className="px-3 py-1.5 text-right font-mono">{formatPrecise(it.quantity, 3)}</td>
                            <td className="px-3 py-1.5 text-right font-mono">
                              {v ? (v.exact ? t("boq.range.exact", "no spread") : `${formatPrecise(v.low, 3)} – ${formatPrecise(v.high, 3)}`) : "—"}
                            </td>
                            <td className="px-3 py-1.5">
                              {v?.weakest ? <Badge tone={gradeTone(v.weakest)}>{gradeLabel(v.weakest)}</Badge> : <span className="text-[var(--color-text-muted)]">{t("boq.range.none", "not graded")}</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            <div className="mt-3 -mx-5">
              <RangeTotalsStrip totals={st.totals} title={t("boq.stageReport.stageTotals", { defaultValue: "Total for {{stage}}", stage: label })} />
            </div>
          </section>
        );
      })}
      <div className="py-1" data-testid="stage-report-bill">
        <RangeTotalsStrip totals={report.totals} title={t("boq.stageReport.billTotals", "Whole bill")} />
      </div>
    </div>
  );
}

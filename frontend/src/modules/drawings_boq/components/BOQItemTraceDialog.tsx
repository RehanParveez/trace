import { useTranslation } from "react-i18next";
import { Badge, ErrorState, LoadingState, Modal } from "../../organizations/components/OrganizationUi";
import { useBOQItemTrace } from "../hooks";
import {activeAdjustments, DEDUCTION_RULE_LABEL, formatJsonValue, formatPrecise, isLowConfidence, warningInfo,
} from "../utils/drawings-boq.utils";
import { TraceSteps } from "./TraceSteps";
import { shapeDims } from "../../drawings_boq/rebar/utils/rebar.utils";

interface BOQItemTraceDialogProps {
  itemId: string;
  itemName: string;
  onClose: () => void;
}

const label = "text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function BOQItemTraceDialog({ itemId, itemName, onClose }: BOQItemTraceDialogProps) {
  const { t } = useTranslation();
  const query = useBOQItemTrace(itemId);
  const data = query.data;

  return (
    <Modal
      title={t("boq.itemTrace.title", { name: itemName })}
      description={t("boq.itemTrace.description")}
      onClose={onClose}
      wide
    >
      {query.isLoading ? (
        <LoadingState label={t("boq.itemTrace.loading")} />
      ) : query.isError || !data ? (
        <ErrorState title={t("boq.itemTrace.loadError")} onRetry={() => void query.refetch()} />
      ) : (
        <div className="max-h-[70vh] space-y-5 overflow-auto">
          <div className="grid grid-cols-2 gap-3 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 sm:grid-cols-4">
            {[
              [t("boq.itemTrace.calculated", "Calculated"), formatPrecise(data.item.net_quantity, 6)],
              [t("boq.itemTrace.adjustments", "Adjustments"), formatPrecise(data.item.adjustment_total, 6)],
              [t("boq.itemTrace.contract", "Contract quantity"), formatPrecise(data.item.quantity, 6)],
              [t("boq.itemTrace.confidence", "Confidence"), data.item.confidence != null ? `${Math.round(Number(data.item.confidence) * 100)}%` : "—"],
            ].map(([k, v]) => (
              <div key={k}>
                <div className="font-mono text-[15px] font-semibold">{v} {k === t("boq.itemTrace.confidence", "Confidence") ? "" : data.item.unit}</div>
                <div className="text-[11px] text-[var(--color-text-muted)]">{k}</div>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            <div className={label}>{t("boq.itemTrace.ledger", "Measurement ledger")} ({data.ledger.length})</div>
            {data.ledger.length === 0 ? (
              <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("boq.itemTrace.noLedger", "No ledger rows. This item was entered manually.")}</p>
            ) : (

              data.ledger.map((l) => (
                <div key={l.id} className="space-y-2 rounded-[8px] border border-[var(--color-border)] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[12.5px] font-semibold">{l.work_item_code}</span>
                    <span className="font-mono text-[11.5px] text-[var(--color-text-secondary)]">{l.formula_code}</span>
                    <Badge tone="slate">{l.source_kind}</Badge>
                    <span className={`font-mono text-[12px] ${isLowConfidence(l.confidence) ? "text-[var(--color-warning)]" : ""}`}>
                      {Math.round(Number(l.confidence) * 100)}%
                    </span>
                    <span className="ml-auto font-mono text-[13px] font-semibold">
                      {formatPrecise(l.quantity_net, 6)} {l.unit}
                    </span>
                  </div>

                  {l.trace?.label ? <div className="text-[12px] text-[var(--color-text-secondary)]">{l.trace.label}</div> : null}
                  <TraceSteps steps={l.trace?.steps ?? []} />
                  {l.warnings.length > 0 ? (
                    <div className="space-y-1 border-t border-[var(--color-border)] pt-2">
                      {l.warnings.map((w) => {
                        const info = warningInfo(w);
                        return (
                          <div key={w} className="flex flex-wrap items-baseline gap-2 text-[11.5px]">
                            <Badge tone={info.severity === "error" ? "red" : info.severity === "warning" ? "gold" : "slate"}>{w}</Badge>
                            <span className="text-[var(--color-text-secondary)]">{info.message}</span>
                            {info.fix ? <span className="text-[var(--color-text-muted)]">{info.fix}</span> : null}
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>

          {(data.bar_marks ?? []).length > 0 ? (
            <div className="space-y-2">
              <div className={label}>{t("boq.itemTrace.barMarks", "Bar marks")} ({data.bar_marks?.length})</div>
              <div className="overflow-auto rounded-[8px] border border-[var(--color-border)]">
                <table className="w-full min-w-[640px] text-left text-[12px]">
                  <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase text-[var(--color-text-muted)]"><tr>
                    <th className="px-3 py-2">{t("rebar.colMark", "Bar mark")}</th>
                    <th className="px-3 py-2">{t("rebar.colShape", "Shape")}</th>
                    <th className="px-3 py-2 text-right">{t("rebar.colDia", "Dia mm")}</th>
                    <th className="px-3 py-2 text-right">{t("rebar.colCount", "Nos")}</th>
                    <th className="px-3 py-2 text-right">{t("rebar.colCut", "Cut mm")}</th>
                    <th className="px-3 py-2 text-right">kg</th>
                    <th className="px-3 py-2">{t("rebar.colSource", "Source")}</th>
                  </tr></thead>
                  <tbody>
                    {(data.bar_marks ?? []).map((m) => (
                      <tr key={m.id ?? `${m.solid_id}-${m.mark}`} className="border-t border-[var(--color-border)]">
                        <td className="px-3 py-2 font-mono font-semibold">{m.mark}</td>
                        <td className="px-3 py-2">{m.shape_code}<div className="font-mono text-[11px] text-[var(--color-text-muted)]">{shapeDims(m.shape_params)}</div></td>
                        <td className="px-3 py-2 text-right font-mono">{formatPrecise(m.dia_mm, 3)}</td>
                        <td className="px-3 py-2 text-right font-mono">{m.count}</td>
                        <td className="px-3 py-2 text-right font-mono">{formatPrecise(m.cut_len_mm, 1)}</td>
                        <td className="px-3 py-2 text-right font-mono font-semibold">{formatPrecise(m.total_kg, 3)}</td>
                        <td className="px-3 py-2"><Badge tone={m.provenance === "RULE_ESTIMATE" ? "gold" : "slate"}>{m.provenance}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {data.deductions.length > 0 ? (
            <div className="space-y-2">
              <div className={label}>{t("boq.itemTrace.deductions", "Deductions")} ({data.deductions.length})</div>
              <ul className="divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
                {data.deductions.map((d) => (
                  <li key={d.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-3 py-2.5 text-[12px]">
                    <Badge tone="slate">{d.deduction_type}</Badge>
                    <span className="font-semibold">{DEDUCTION_RULE_LABEL[d.rule_code] ?? d.rule_code}</span>
                    <span className="font-mono">−{formatPrecise(d.quantity, 6)} {d.unit}</span>
                    {d.explanation ? <span className="text-[var(--color-text-secondary)]">{d.explanation}</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {activeAdjustments(data.adjustments).length > 0 ? (
            <div className="space-y-2">
              <div className={label}>{t("boq.itemTrace.activeAdjustments", "Active adjustments")}</div>
              <ul className="divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
                {activeAdjustments(data.adjustments).map((a) => (
                  <li key={a.id} className="flex flex-wrap items-baseline gap-3 px-3 py-2.5 text-[12px]">
                    <Badge tone={a.kind === "REPLACE" ? "blue" : "slate"}>{a.kind}</Badge>
                    <span className="font-mono font-semibold">{formatPrecise(a.value, 6)} {data.item.unit}</span>
                    <span className="text-[var(--color-text-secondary)]">{a.reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <details>
            <summary className="cursor-pointer text-[11.5px] text-[var(--color-text-muted)]">{t("boq.itemTrace.raw", "Raw trace")}</summary>
            <pre className="mt-2 overflow-auto rounded-[8px] bg-[var(--color-surface-muted)] p-4 text-[11px] leading-5 text-[var(--color-text-secondary)]">
              {formatJsonValue(data)}
            </pre>
          </details>
        </div>
      )}
    </Modal>
  );
}
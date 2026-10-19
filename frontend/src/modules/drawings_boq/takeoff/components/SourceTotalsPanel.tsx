import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../organizations/components/OrganizationUi";
import type { SourceTotals } from "../utils/sourceTotals";
import { hasReconciliation, itemsToShow, quantityText, sourceShares, sourceText } from "../utils/sourceTotals";

interface Props {
  data: SourceTotals | undefined;
  loading: boolean;
  error: boolean;
}

export function SourceTotalsPanel({ data, loading, error }: Props) {

  const { t } = useTranslation();
  const [onlyMixed, setOnlyMixed] = useState(false);
  if (loading || error || !data || !data.run) return null;
  const items = itemsToShow(data, onlyMixed);
  const rec = data.reconciliation;
  return (
    <section className="space-y-2 border-b border-[var(--color-border)] p-4" data-testid="source-totals" data-mixed={data.mixed_items}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-[13px] font-semibold">{t("boq.takeoff.sources.title", "Where the quantities come from")}</h3>
        <Badge tone="slate">{t("boq.takeoff.sources.items", "{{n}} items", { n: data.items.length })}</Badge>
        {data.mixed_items > 0 ? <Badge tone="gold">{t("boq.takeoff.sources.mixed", "{{n}} from more than one source", { n: data.mixed_items })}</Badge> : null}
        {data.mixed_items > 0 ? (
          <label className="ms-auto flex items-center gap-1 text-[12px]">
            <input type="checkbox" checked={onlyMixed} onChange={(e) => setOnlyMixed(e.target.checked)} data-testid="source-totals-mixed-only" />
            {t("boq.takeoff.sources.onlyMixed", "Only those")}
          </label>
        ) : null}
      </div>
      {hasReconciliation(rec) ? (
        <div className="flex flex-wrap gap-2 text-[12px]" data-testid="source-reconciliation">
          {rec.replaced ? <Badge tone="gold">{t("boq.takeoff.sources.replaced", "{{n}} replaced the model", { n: rec.replaced })}</Badge> : null}
          {rec.verified ? <Badge tone="blue">{t("boq.takeoff.sources.verified", "{{n}} only verified it", { n: rec.verified })}</Badge> : null}
          {rec.variances ? <Badge tone="red">{t("boq.takeoff.sources.variances", "{{n}} differ from the model", { n: rec.variances })}</Badge> : null}
          {rec.not_counted ? <Badge tone="red">{t("boq.takeoff.sources.notCounted", "{{n}} not counted", { n: rec.not_counted })}</Badge> : null}
          {rec.tolerance_pct ? <Badge tone="slate">{t("boq.takeoff.results.tolerance", "tolerance")} {rec.tolerance_pct}%</Badge> : null}
        </div>
      ) : null}
      <ul className="list-none space-y-1 pl-0">
        {items.map((i) => (
          <li key={`${i.work_item_code}-${i.unit}`} className="rounded-[8px] border border-[var(--color-border)] p-2 text-[12.5px]" data-testid="source-total-row" data-mixed={i.mixed}>
            <div className="flex items-baseline gap-2">
              <span className="min-w-0 flex-1 truncate font-semibold" title={i.name ?? i.work_item_code}>{i.name ?? i.work_item_code}</span>
              <span className="font-mono">{quantityText(i.total)} {i.unit}</span>
            </div>
            {i.mixed ? (
              <div className="mt-0.5 flex flex-wrap gap-x-3 text-[11.5px] text-[var(--color-text-secondary)]">
                {sourceShares(i).map((s) => (
                  <span key={s.source} data-testid="source-share">{sourceText(s.source)}: <span className="font-mono">{quantityText(s.quantity)}</span> ({s.pct}%)</span>
                ))}
              </div>
            ) : (
              <div className="text-[11.5px] text-[var(--color-text-secondary)]">{i.sources[0] ? sourceText(i.sources[0].source) : ""}</div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { QuantityRange, RangeTotal } from "../types/drawings-boq.types";
import { gradeTone, rangeView } from "../utils/quantityRange";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { useGradeLabel } from "../utils/gradeLabel";

const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";

export function RangeCell({ range }: { range: QuantityRange | null | undefined }) {
  const { t } = useTranslation();
  const gradeLabel = useGradeLabel();
  const v = rangeView(range);
  if (!v || !range) {
    return (
      <span className="text-[11px] text-[var(--color-text-muted)]" data-testid="range-none">
        {t("boq.range.none", "not graded")}
      </span>
    );
  }
  return (
    <div className="flex flex-col items-end gap-0.5" data-testid="range-cell">
      {v.exact ? (
        <span className="font-mono text-[12px] text-[var(--color-text-secondary)]" data-testid="range-exact">
          {t("boq.range.exact", "no spread")}
        </span>
      ) : (
        <span className="font-mono text-[12px] text-[var(--color-text-primary)]" data-testid="range-span">
          {formatPrecise(v.low, 3)} – {formatPrecise(v.high, 3)}
        </span>
      )}
      {v.weakest ? <Badge tone={gradeTone(v.weakest)}>{gradeLabel(v.weakest)}</Badge> : null}
      {!v.complete ? (
        <span className="max-w-[170px] text-right text-[10.5px] text-[var(--color-warning)]" data-testid="range-incomplete">
          {v.unboundedRows > 0
            ? t("boq.range.unbounded", { defaultValue: "{{count}} row(s) with no range: a minimum", count: v.unboundedRows })
            : t("boq.range.leavesOut", { defaultValue: "{{count}} row(s) leave something out", count: v.leavesOutRows })}
        </span>
      ) : null}
    </div>
  );
}

export function RangeTotalsStrip({ totals, title }: { totals: RangeTotal[]; title?: string }) {
  const { t } = useTranslation();
  if (totals.length === 0) return null;
  return (
    <div className="border-b border-[var(--color-border)] px-5 py-3" data-testid="range-totals">
      <div className={HEAD}>{title ?? t("boq.range.totalsTitle", "Totals by unit, with their range")}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {totals.map((x) => (
          <div key={x.unit} className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2" data-testid={`range-total-${x.unit}`}>
            <div className="font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">
              {formatPrecise(x.likely, 3)} {x.unit}
            </div>
            <div className="font-mono text-[11px] text-[var(--color-text-secondary)]">
              {x.low === x.likely && x.high === x.likely ? t("boq.range.exact", "no spread") : `${formatPrecise(x.low, 3)} – ${formatPrecise(x.high, 3)}`}
            </div>
            {x.unbounded > 0 ? (
              <div className="text-[10.5px] text-[var(--color-warning)]" data-testid={`range-total-unbounded-${x.unit}`}>
                {t("boq.range.itemsUnbounded", { defaultValue: "{{count}} item(s) not fully bounded", count: x.unbounded })}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

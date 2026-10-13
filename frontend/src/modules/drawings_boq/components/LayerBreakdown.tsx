import { useTranslation } from "react-i18next";
import type { LedgerTrace } from "../types/drawings-boq.types";
import { layerSplitView } from "../utils/derived";

export function LayerBreakdown({ trace }: { trace?: LedgerTrace | null }) {
  const { t } = useTranslation();
  const view = layerSplitView(trace);
  if (!view) return null;
  const hasExcluded = Number(view.excludedM3) > 0;
  return (
    <div className="space-y-2 rounded-[8px] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {t("boq.layers.title", "Layers of this element")}
      </div>
      <table className="w-full text-left text-[12px]">
        <thead className="text-[10.5px] uppercase text-[var(--color-text-muted)]">
          <tr>
            <th className="py-1 pr-3">{t("boq.layers.colMaterial", "Material")}</th>
            <th className="py-1 pr-3">{t("boq.layers.colFamily", "Kind")}</th>
            <th className="py-1 text-right">{t("boq.layers.colThickness", "Thickness (mm)")}</th>
          </tr>
        </thead>
        <tbody>
          {view.layers.map((l, i) => (
            <tr key={`${l.material}-${i}`} className="border-t border-[var(--color-border)]">
              <td className="py-1 pr-3">{l.material}</td>
              <td className="py-1 pr-3 font-mono text-[11px]">{l.family}</td>
              <td className="py-1 text-right font-mono">{l.thicknessMm}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-[12px] text-[var(--color-text-secondary)]">
        {t("boq.layers.summary", {
          defaultValue: "Billed {{family}}: {{billed}} mm of {{total}} mm ({{percent}}%) of {{m3}} m³",
          family: view.family,
          billed: view.billedThicknessMm,
          total: view.totalThicknessMm,
          percent: view.sharePercent,
          m3: view.ofM3,
        })}
      </div>
      {hasExcluded ? (
        <div className="text-[12px] text-[var(--color-text-secondary)]">
          {t("boq.layers.excluded", {
            defaultValue: "{{m3}} m³ of this element was left out (finish or unpriced layers).",
            m3: view.excludedM3,
          })}
        </div>
      ) : null}
      {view.declaredThicknessMm ? (
        <div className="text-[12px] text-[var(--color-text-muted)]">
          {t("boq.layers.declared", {
            defaultValue: "The element's own width in the model is {{declared}} mm.",
            declared: view.declaredThicknessMm,
          })}
        </div>
      ) : null}
    </div>
  );
}

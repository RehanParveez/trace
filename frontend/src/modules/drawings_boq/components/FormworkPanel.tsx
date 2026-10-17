import { useTranslation } from "react-i18next";
import type { FormworkStatsView } from "../utils/derived";
import { formatPrecise } from "../utils/drawings-boq.utils";

const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";
const NOTE = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]";

function Cell({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3" data-testid={testId}>
      <div className={HEAD}>{label}</div>
      <div className="mt-1.5 font-mono text-[15px] font-semibold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

export function FormworkPanel({ view }: { view: FormworkStatsView }) {
  const { t } = useTranslation();
  if (!view.ran) {
    return (
      <div className={NOTE} data-testid="formwork-not-run">
        {t(`boq.calculationRun.formworkReason.${view.reason ?? "NOTHING_TO_SHUTTER"}`, "Formwork was not worked out for the concrete read from the drawing.")}
        {view.footingsLeftOut > 0
          ? ` ${t("boq.calculationRun.formworkFootingsOff", {
              defaultValue: "{{count}} footings were left without formwork. Footing sides are not shuttered unless the site assumptions say so.",
              count: view.footingsLeftOut,
            })}`
          : ""}
      </div>
    );
  }
  const showGross = view.categories.some((c) => c.grossM2 != null);
  return (
    <div className="space-y-3" data-testid="formwork-panel">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {t("boq.calculationRun.statsFormwork", "Formwork (concrete read from the drawing)")}
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <Cell testId="formwork-net" label={t("boq.calculationRun.statFormworkTotal", "Formwork (m²)")} value={formatPrecise(view.areaM2, 3)} />
        {view.comparison ? (
          <Cell testId="formwork-gross" label={t("boq.formwork.gross", "Each member on its own (m²)")} value={formatPrecise(view.comparison.grossM2, 3)} />
        ) : null}
        {view.takenOffM2 ? (
          <Cell testId="formwork-taken-off" label={t("boq.formwork.takenOff", "Taken off where members meet (m²)")} value={formatPrecise(view.takenOffM2, 3)} />
        ) : null}
      </div>
      <div className="overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
        <table className="w-full text-[12px]" data-testid="formwork-table">
          <thead>
            <tr className="bg-[var(--color-surface-muted)] text-left">
              <th className={`${HEAD} px-3 py-2`}>{t("boq.formwork.colCategory", "Member")}</th>
              <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.formwork.colMarks", "Marks")}</th>
              {showGross ? <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.formwork.colGross", "Each on its own (m²)")}</th> : null}
              <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.formwork.colNet", "Net (m²)")}</th>
            </tr>
          </thead>
          <tbody>
            {view.categories.map((c) => (
              <tr key={c.category} data-testid={`formwork-row-${c.category}`} className="border-t border-[var(--color-border)]">
                <td className="px-3 py-1.5">{t(`boq.derived.category.${c.category}`, c.category)}</td>
                <td className="px-3 py-1.5 text-right font-mono">{c.marks}</td>
                {showGross ? <td className="px-3 py-1.5 text-right font-mono">{c.grossM2 != null ? formatPrecise(c.grossM2, 3) : "—"}</td> : null}
                <td className="px-3 py-1.5 text-right font-mono font-semibold">{formatPrecise(c.m2, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {view.assumed.length > 0 ? (
        <div className="flex flex-wrap gap-1.5" data-testid="formwork-assumed">
          {view.assumed.map((name) => (
            <span key={name} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 text-[11px] text-[var(--color-warning)]">
              {t(`boq.derived.param.${name}`, name)}
            </span>
          ))}
        </div>
      ) : null}
      {view.footingsLeftOut > 0 ? (
        <div className={NOTE} data-testid="formwork-footings-off">
          {t("boq.calculationRun.formworkFootingsOff", {
            defaultValue: "{{count}} footings were left without formwork. Footing sides are not shuttered unless the site assumptions say so.",
            count: view.footingsLeftOut,
          })}
        </div>
      ) : null}
      {view.tanksLeftOut > 0 ? (
        <div className={`${NOTE} text-[var(--color-warning)]`} data-testid="formwork-tanks-off">
          {t("boq.formwork.tanksLeftOut", {
            defaultValue: "{{count}} tanks were left without formwork: their height and wall thickness were not kept when they were accepted. Accept them again with those sizes.",
            count: view.tanksLeftOut,
          })}
        </div>
      ) : null}
      {view.contactNotDeducted ? (
        <div className={NOTE} data-testid="formwork-contact">
          {t("boq.calculationRun.formworkContact", "Each member is shuttered on its own. No face where members meet was taken off in this run.")}
        </div>
      ) : null}
      {view.beamsUnmatched > 0 ? (
        <div className={NOTE} data-testid="formwork-beams-unmatched">
          {t("boq.formwork.beamsUnmatched", {
            defaultValue: "{{count}} beams stand on a floor with no counted slab, or are plinth beams or tie bands, so their sides were not reduced.",
            count: view.beamsUnmatched,
          })}
        </div>
      ) : null}
      {view.comparison ? (
        <details className={NOTE} data-testid="formwork-comparison">
          <summary className="cursor-pointer font-semibold">{t("boq.formwork.comparisonTitle", "For comparison only. These figures are not in the bill.")}</summary>
          <ul className="mt-2 space-y-1">
            <li data-testid="formwork-cmp-soffit">
              {t("boq.formwork.cmpSoffit", { defaultValue: "Slab soffit alone, with no edges and no beams: {{m2}} m²", m2: formatPrecise(view.comparison.slabSoffitOnlyM2, 3) })}
            </li>
            <li data-testid="formwork-cmp-beam">
              {t("boq.formwork.cmpBeam", {
                defaultValue: "Beams at 0.75 ft of formwork for each running foot: {{shortcut}} m² (worked out from the drawing: {{net}} m²)",
                shortcut: formatPrecise(view.comparison.beamPerRftM2, 3),
                net: formatPrecise(view.comparison.beamNetM2, 3),
              })}
            </li>
          </ul>
        </details>
      ) : null}
    </div>
  );
}

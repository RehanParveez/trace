import { useTranslation } from "react-i18next";
import type { SteelEstimateView } from "../utils/steelEstimate";

function kgText(value: string | number): string {
  const n = Number(value);
  return n >= 1000 ? `${(n / 1000).toFixed(2)} t` : `${n.toFixed(1)} kg`;
}

const SKIPPED_LABEL: Record<string, string> = {
  NOT_COUNTED: "not counted in this run",
  NO_USUAL_FIGURE: "stairs, tanks, RCC walls and parapets have no usual figure",
  NO_SIZE: "the size is not whole yet (depth or width missing)",
};

export function SteelEstimateNotes({ view }: { view: SteelEstimateView }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-1 rounded-[8px] border border-[var(--color-warning)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]" data-testid="steel-estimate">
      <p className="font-semibold text-[var(--color-text-primary)]">
        {t("boq.steelEstimate.title", {
          defaultValue: "{{n}} members print no bars. Their steel is an estimate: {{kg}} (between {{low}} and {{high}}).",
          n: view.members,
          kg: kgText(view.kg),
          low: kgText(view.low),
          high: kgText(view.high),
        })}
      </p>
      <p data-testid="steel-estimate-total">
        {t("boq.steelEstimate.total", {
          defaultValue: "With the {{measured}} of printed bars the total is {{total}} (between {{low}} and {{high}}). {{share}} percent of it is estimated.",
          measured: kgText(view.measuredKg),
          total: kgText(view.totalKg),
          low: kgText(view.totalLow),
          high: kgText(view.totalHigh),
          share: Number(view.sharePct).toFixed(0),
        })}
      </p>
      <ul className="list-disc pl-5">
        {view.families.map((f) => (
          <li key={f.family}>
            {t(`boq.derived.category.${f.family}`, f.family.charAt(0) + f.family.slice(1).toLowerCase())}, {f.members}: {kgText(f.kg)} ({kgText(f.low)} to {kgText(f.high)})
          </li>
        ))}
      </ul>
      {view.slabRule ? (
        <p>
          {t("boq.steelEstimate.slabRule", { defaultValue: "Slabs use {{rule}} kg per square metre, the quantity surveyor's rule ({{src}}).", rule: view.slabRule, src: view.slabRuleSource ?? "proposed" })}
        </p>
      ) : null}
      {view.skipped.map((s) => (
        <p key={s.code} data-testid={`steel-estimate-skipped-${s.code}`}>
          {t("boq.steelEstimate.skipped", { defaultValue: "{{n}} left out: {{why}}.", n: s.count, why: t(`boq.steelEstimate.skip.${s.code}`, SKIPPED_LABEL[s.code] ?? s.code) })}
        </p>
      ))}
    </div>
  );
}

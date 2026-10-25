import { useTranslation } from "react-i18next";
import { Badge } from "../../../organizations/components/OrganizationUi";
import type { BillCompleteness } from "../types/billCompleteness.types";
import { useBillCompleteness } from "../hooks/useBillCompleteness";
import { funnelLine, severityTone, stepTone, verdictText, verdictTone } from "../utils/billCompleteness";

export function BillCompletenessCard({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const q = useBillCompleteness(runId);
  const d: BillCompleteness | undefined = q.data;
  if (!d) return null;
  const line = funnelLine(d);
  return (
    <section className="space-y-2 rounded-[8px] border border-[var(--color-border)] p-3 text-[12px]" data-testid="bill-completeness" data-verdict={d.verdict}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.completeness.title", "Is the bill complete?")}</h3>
        <Badge tone={verdictTone(d.verdict)}>{t(`boq.completeness.verdict.${d.verdict}`, verdictText(d.verdict))}</Badge>
        <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{t("boq.completeness.rows", "{{n}} ledger rows", { n: d.ledger_rows })}</span>
      </div>
      {line ? <p className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="bill-completeness-funnel">{line}</p> : null}
      <ul className="space-y-1.5">
        {d.findings.map((f) => (
          <li key={f.code} className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid={`completeness-${f.code}`} data-severity={f.severity}>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={severityTone(f.severity)}>{f.severity.toLowerCase()}</Badge>
              <span className="font-semibold">{f.title}</span>
            </div>
            <p className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]">{f.detail}</p>
            {f.fix ? <p className="mt-1 text-[11.5px]"><span className="font-semibold">{t("boq.completeness.fix", "What to do")}: </span>{f.fix}</p> : null}
          </li>
        ))}
      </ul>
      {d.derived_steps.length ? (
        <div data-testid="bill-completeness-steps">
          <p className="mb-1 font-semibold">{t("boq.completeness.steps", "What each derived step did")}</p>
          <ul className="space-y-0.5">
            {d.derived_steps.map((s) => (
              <li key={s.step} className="flex flex-wrap items-center gap-2" data-testid={`completeness-step-${s.step}`} data-ran={s.ran}>
                <Badge tone={stepTone(s)}>{s.ran ? t("boq.completeness.stepRows", "{{n}} rows", { n: s.rows }) : t("boq.completeness.stepNotRun", "not run")}</Badge>
                <span>{s.label}</span>
                {s.reason_text ? <span className="text-[11px] text-[var(--color-text-muted)]">{s.reason_text}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="flex flex-wrap gap-1.5" data-testid="bill-completeness-families">
        {d.families.map((f) => (
          <Badge key={f.family} tone={f.present ? "green" : "slate"}>{f.label}: {f.present ? f.rows : t("boq.completeness.none", "none")}</Badge>
        ))}
      </div>
      <p className="text-[11px] text-[var(--color-text-muted)]">{d.note}</p>
    </section>
  );
}

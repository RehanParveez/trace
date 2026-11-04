import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { classTone, sortedClassCounts } from "../utils/bbsAudit";
import { basisSentence, kgPlain, pctLabel, signedKg } from "../utils/bbsReport";
import type { ReportSummary } from "../types/bbsReport.types";

const card = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3";
const label = "text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function AuditSummary({ summary }: { summary: ReportSummary }) {
  const { t } = useTranslation();
  const left = Object.entries(summary.excluded_kg).filter(([, v]) => Number(v) !== 0);
  const estimate = basisSentence(summary.effect_by_basis);
  const st = summary.counts_by_status;
  return (
    <div className="space-y-3" data-testid="bbs-audit-summary">
      {!summary.has_run ? (
        <p className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
          {t("bbs.report.notRun", "No audit has been run on this version. Run the cross-check to compare the schedule with the drawings.")}
        </p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className={card}>
          <div className={label}>{t("bbs.report.bbsTotal", "Schedule total")}</div>
          <div className="mt-1 font-mono text-[18px] font-semibold text-[var(--color-text-primary)]">{kgPlain(summary.bbs_total_kg)} kg</div>
        </div>
        <div className={card}>
          <div className={label}>{t("bbs.report.expected", "Expected total")}</div>
          <div className="mt-1 font-mono text-[18px] font-semibold text-[var(--color-text-primary)]">{kgPlain(summary.expected_total_kg)} kg</div>
        </div>
        <div className={card}>
          <div className={label}>{t("bbs.report.difference", "Difference")}</div>
          <div className="mt-1 font-mono text-[18px] font-semibold text-[var(--color-text-primary)]">{signedKg(summary.diff_kg)} kg</div>
          <div className="font-mono text-[12px] text-[var(--color-text-muted)]">{pctLabel(summary.diff_pct)}</div>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {sortedClassCounts(summary.counts_by_class).map(([c, count]) => (
          <Badge key={c} tone={classTone(c)}>{c} {count}{summary.effect_by_class[c] !== undefined ? ` · ${signedKg(summary.effect_by_class[c])} kg` : ""}</Badge>
        ))}
      </div>
      <p className="text-[12px] text-[var(--color-text-secondary)]">
        {t("bbs.report.statuses", "Open {{o}} · accepted {{a}} · rejected {{r}} · signed {{s}}", { o: st.OPEN ?? 0, a: st.ACCEPTED ?? 0, r: st.REJECTED ?? 0, s: st.SIGNED ?? 0 })}
      </p>
      <p className="text-[11.5px] text-[var(--color-text-muted)]">{summary.note}</p>
      {estimate ? <p className="text-[11.5px] font-semibold text-[var(--color-warning)]">{estimate}</p> : null}
      {left.length > 0 ? (
        <p className="text-[11.5px] text-[var(--color-text-muted)]">
          {t("bbs.report.left", "Left out of the expected total: {{list}}", { list: left.map(([k, v]) => `${k.toLowerCase()} ${signedKg(v)} kg`).join(", ") })}
        </p>
      ) : null}
    </div>
  );
}

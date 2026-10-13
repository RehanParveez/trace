import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { RunStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import {
  bandTone, confidenceView, coverageView, geometrySourceLabel,
  type CoverageGapKey, type TrustBand,
} from "../utils/trust";

const heading = "mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

const BAND_BAR: Record<TrustBand, string> = {
  HIGH: "bg-[var(--color-success)]",
  MEDIUM: "bg-[var(--color-warning)]",
  LOW: "bg-[var(--color-danger)]",
};

function pct(share: number | null): string {
  return share === null ? "—" : `${Math.round(share * 100)}%`;
}

export function RunTrust({ stats }: { stats?: RunStats }) {
  const { t } = useTranslation();
  const coverage = coverageView(stats?.coverage);
  const confidence = confidenceView(stats?.confidence);

  if (!coverage && !confidence) {
    return null;
  }

  const gapLabel: Record<CoverageGapKey, string> = {
    rejected: t("boq.trust.gapRejected", "Failed validation"),
    skipped_by_role: t("boq.trust.gapSkipped", "No quantity role"),
    unmapped: t("boq.trust.gapUnmapped", "No work item for its type"),
    other_unmeasured: t("boq.trust.gapOther", "Zero or merged into another element"),
  };
  const bandLabel: Record<TrustBand, string> = {
    HIGH: t("boq.trust.bandHigh", "High (90% and over)"),
    MEDIUM: t("boq.trust.bandMedium", "Medium (70 to 90%)"),
    LOW: t("boq.trust.bandLow", "Low (under 70%)"),
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {coverage ? (
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <div className={heading}>{t("boq.trust.coverageTitle", "What was measured")}</div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[18px] font-semibold text-[var(--color-text-primary)]">{coverage.percent}%</span>
            <span className="text-[12px] text-[var(--color-text-secondary)]">
              {t("boq.trust.coverageOf", "{{measured}} of {{total}} model elements gave a quantity", {
                measured: coverage.measured, total: coverage.total,
              })}
            </span>
          </div>
          <div
            className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--color-border)]"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={coverage.percent}
          >
            <div className="h-full bg-[var(--color-success)]" style={{ width: `${coverage.percent}%` }} />
          </div>
          {coverage.gaps.length > 0 ? (
            <div className="mt-3 space-y-1">
              <div className="text-[11px] text-[var(--color-text-muted)]">
                {t("boq.trust.coverageGaps", "Not measured")}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {coverage.gaps.map((gap) => (
                  <span
                    key={gap.key}
                    className="rounded-full bg-[var(--color-surface)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]"
                  >
                    {gapLabel[gap.key]}: {gap.count}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {confidence ? (
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <div className={heading}>{t("boq.trust.confidenceTitle", "How far the numbers can be trusted")}</div>
          {confidence.totalVolumeM3 > 0 ? (
            <>
              <div className="flex h-2 overflow-hidden rounded-full bg-[var(--color-border)]">
                {confidence.bands.map((b) =>
                  b.volumeShare ? (
                    <div key={b.band} className={BAND_BAR[b.band]} style={{ width: `${b.volumeShare * 100}%` }} />
                  ) : null,
                )}
              </div>
              <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">
                {t("boq.trust.byVolume", "Share of the {{total}} m³ of measured volume", {
                  total: formatPrecise(confidence.totalVolumeM3, 2),
                })}
              </div>
            </>
          ) : null}
          <ul className="mt-2 space-y-1 text-[12px]">
            {confidence.bands.map((b) => (
              <li key={b.band} className="flex flex-wrap items-center gap-2">
                <Badge tone={bandTone(b.band)}>{bandLabel[b.band]}</Badge>
                <span className="font-mono text-[11.5px] text-[var(--color-text-secondary)]">
                  {t("boq.trust.rows", "{{count}} rows", { count: b.rows })}
                  {confidence.totalVolumeM3 > 0 ? ` · ${formatPrecise(b.volumeM3, 2)} m³ · ${pct(b.volumeShare)}` : ""}
                </span>
              </li>
            ))}
          </ul>
          {confidence.sources.length > 0 ? (
            <div className="mt-3 space-y-1">
              <div className="text-[11px] text-[var(--color-text-muted)]">{t("boq.trust.sources", "Where the volume comes from")}</div>
              <ul className="space-y-0.5 text-[11.5px] text-[var(--color-text-secondary)]">
                {confidence.sources.map((s) => (
                  <li key={s.key} className="flex flex-wrap gap-x-2">
                    <span>{geometrySourceLabel(s.key, (key, fallback) => t(key, fallback))}</span>
                    <span className="font-mono text-[var(--color-text-muted)]">
                      {formatPrecise(s.volumeM3, 2)} m³ · {pct(s.share)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

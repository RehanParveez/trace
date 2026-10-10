import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { RunStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";

function Stat({ label, value, tone }: { label: string; value: ReactNode; tone?: "red" | "gold" }) {
  const color =
    tone === "red" ? "text-[var(--color-danger)]"
    : tone === "gold" ? "text-[var(--color-warning)]"
    : "text-[var(--color-text-primary)]";
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{label}</div>
      <div className={`mt-1.5 font-mono text-[15px] font-semibold ${color}`}>{value}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{title}</div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{children}</div>
    </div>
  );
}

function Counts({ title, data }: { title: string; data?: Record<string, number> }) {
  const entries = Object.entries(data ?? {});
  if (entries.length === 0) return null;
  return (
    <div>
      <div className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{title}</div>
      <div className="flex flex-wrap gap-1.5">
        {entries.map(([k, v]) => (
          <span key={k} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]">
            {k}: {v}
          </span>
        ))}
      </div>
    </div>
  );
}

export function RunStatsSummary({ stats }: { stats?: RunStats }) {
  const { t } = useTranslation();
  if (!stats || Object.keys(stats).length === 0) return null;

  const a = stats.allocation;
  const o = a?.openings;
  const r = stats.rebar;
  const failures = Number(a?.conservation_failures ?? 0);
  const estimatedKg = Number(r?.tier3_kg ?? 0);
  const rejected = Number(stats.rejected_total ?? 0);

  return (
    <div className="space-y-4">
      {stats.boq_error ? (
        <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
          {t("boq.calculationRun.boqBuildFailed", "BOQ build failed after the run")}: {stats.boq_error}
        </div>
      ) : null}

      <Section title={t("boq.calculationRun.statsInput", "Input")}>
        <Stat label={t("boq.calculationRun.statElements", "Elements")} value={stats.elements_in ?? 0} />
        <Stat label={t("boq.calculationRun.statRejected", "Rejected")} value={rejected} tone={rejected > 0 ? "red" : undefined} />
        <Stat label={t("boq.calculationRun.statSpaces", "Spaces")} value={stats.spaces ?? 0} />
      </Section>

      {a && a.participating !== undefined ? (
        <Section title={t("boq.calculationRun.statsAllocation", "Overlap allocation")}>
          <Stat label={t("boq.calculationRun.statConvention", "Convention")} value={a.convention ?? "—"} />
          <Stat label={t("boq.calculationRun.statParticipating", "Solids allocated")} value={a.participating ?? 0} />
          <Stat label={t("boq.calculationRun.statOverlaps", "Overlaps")} value={a.overlaps ?? 0} />
          <Stat
            label={t("boq.calculationRun.statApprox", "Approximate (bbox)")}
            value={a.approximate_solids ?? 0}
            tone={Number(a.approximate_solids ?? 0) > 0 ? "gold" : undefined}
          />
          <Stat label={t("boq.calculationRun.statComponents", "Components checked")} value={a.components_checked ?? 0} />
          <Stat
            label={t("boq.calculationRun.statConservation", "Conservation failures")}
            value={failures}
            tone={failures > 0 ? "red" : undefined}
          />
        </Section>
      ) : null}

      {stats.wall_material && stats.wall_material.walls > 0 ? (
        <Section title={t("boq.calculationRun.statsWalls", "Wall material")}>
          <Stat label={t("boq.calculationRun.statWalls", "Walls")} value={stats.wall_material.walls} />
          <Stat label={t("boq.calculationRun.statWallsConcrete", "Concrete (billed as RCC)")} value={stats.wall_material.billed_as_concrete} />
          <Stat label={t("boq.calculationRun.statWallsMasonry", "Masonry")} value={stats.wall_material.masonry} />
          <Stat
            label={t("boq.calculationRun.statWallsUnknown", "Material not in model (billed as masonry)")}
            value={stats.wall_material.material_unknown}
            tone={stats.wall_material.material_unknown > 0 ? "gold" : undefined}
          />
        </Section>
      ) : null}

      {o ? (
        <Section title={t("boq.calculationRun.statsOpenings", "Openings")}>
          <Stat label={t("boq.calculationRun.statHosted", "Hosted")} value={o.hosted} />
          <Stat label={t("boq.calculationRun.statDeducted", "Deducted")} value={o.deducted} />
          <Stat label={t("boq.calculationRun.statIgnored", "Below threshold")} value={o.ignored} />
          <Stat label={t("boq.calculationRun.statSizeMissing", "Size missing")} value={o.size_missing} tone={o.size_missing > 0 ? "gold" : undefined} />
          <Stat label={t("boq.calculationRun.statUnhosted", "No host wall")} value={o.unhosted} tone={o.unhosted > 0 ? "gold" : undefined} />
          <Stat label={t("boq.calculationRun.statQtoWalls", "Qto walls skipped")} value={o.qto_walls_skipped} tone={o.qto_walls_skipped > 0 ? "gold" : undefined} />
        </Section>
      ) : null}

      {r && r.schedule_marks !== undefined ? (
        <Section title={t("boq.calculationRun.statsRebar", "Reinforcement")}>
          <Stat label={t("boq.calculationRun.statScheduleMarks", "Schedule marks")} value={r.schedule_marks ?? 0} />
          <Stat label={t("boq.calculationRun.statMatched", "Matched / unmatched")} value={`${r.matched ?? 0} / ${r.unmatched ?? 0}`} />
          <Stat label={t("boq.calculationRun.statFromSchedule", "From schedule (kg)")} value={formatPrecise(r.tier2_kg, 2)} />
          <Stat
            label={t("boq.calculationRun.statEstimated", "Estimated (kg)")}
            value={formatPrecise(r.tier3_kg, 2)}
            tone={estimatedKg > 0 ? "gold" : undefined}
          />
          <Stat label={t("boq.calculationRun.statTotalKg", "Total (kg)")} value={formatPrecise(r.total_kg, 2)} />
          <Stat label={t("boq.calculationRun.statEstimateMarks", "Estimated marks")} value={r.estimated_marks ?? 0} />
          <Stat label={t("boq.calculationRun.statSuppressed", "Estimates suppressed")} value={r.estimate_suppressed ?? 0} />
          <Stat label={t("boq.calculationRun.statFamilies", "Covered families")} value={(r.covered_families ?? []).join(", ") || "—"} />
        </Section>
      ) : null}

      <Counts title={t("boq.calculationRun.statsSkippedRoles", "Skipped (no quantity role)")} data={stats.skipped_by_role} />
      <Counts title={t("boq.calculationRun.statsUnmapped", "Unmapped IFC types (no work item)")} data={stats.unmapped_by_type} />
      <Counts title={t("boq.calculationRun.statsFinishSkipped", "Finishes skipped")} data={stats.finishes_skipped} />
      <Counts title={t("boq.calculationRun.statsRebarSkipped", "Bar rows skipped")} data={stats.rebar_skipped} />

      {stats.rejected_sample && stats.rejected_sample.length > 0 ? (
        <div>
          <div className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
            {t("boq.calculationRun.statsRejected", "Rejected elements")} ({rejected}
            {rejected > stats.rejected_sample.length ? `, showing ${stats.rejected_sample.length}` : ""})
          </div>
          <ul className="space-y-0.5 text-[11.5px] text-[var(--color-text-secondary)]">
            {stats.rejected_sample.slice(0, 20).map((x) => (
              <li key={x.element_id}>
                <span className="font-mono">{x.ifc_type}</span> · {x.code}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
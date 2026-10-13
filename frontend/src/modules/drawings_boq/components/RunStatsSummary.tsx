import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { RunStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { SteelRebarRange } from "./SteelRebarRange";
import { RunTrust } from "./RunTrust";
import { useStageLabel } from "./StageBadge";

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
  const stageLabel = useStageLabel();
  if (!stats || Object.keys(stats).length === 0) return null;

  const a = stats.allocation;
  const o = a?.openings;
  const r = stats.rebar;
  const failures = Number(a?.conservation_failures ?? 0);
  const estimatedKg = Number(r?.tier3_kg ?? 0);
  const rejected = Number(stats.rejected_total ?? 0);

  const sp = stats.spec;
  const st = stats.stages;
  const ly = stats.layers;
  const dv = stats.derived;
  const genericMaterial = Number(stats.material?.generic_elements ?? 0);

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

      <RunTrust stats={stats} />

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

            {sp?.enabled ? (
        <Section title={t("boq.calculationRun.statsSpec", "Specification")}>
          <Stat label={t("boq.calculationRun.statSpecRows", "Rows with a specification")} value={sp.rows_with_spec ?? 0} />
          <Stat label={t("boq.calculationRun.statSpecMasonry", "Masonry rows")} value={sp.masonry_rows ?? 0} />
          <Stat label={t("boq.calculationRun.statSpecConcrete", "Concrete rows")} value={sp.concrete_rows ?? 0} />
          <Stat label={t("boq.calculationRun.statSpecKeys", "Distinct specifications")} value={sp.distinct_spec_keys ?? 0} />
          <Stat label={t("boq.calculationRun.statSpecMix", "Mix not stated")} value={sp.mix_missing ?? 0} tone={Number(sp.mix_missing ?? 0) > 0 ? "gold" : undefined} />
          <Stat label={t("boq.calculationRun.statSpecMortar", "Mortar not stated")} value={sp.mortar_missing ?? 0} tone={Number(sp.mortar_missing ?? 0) > 0 ? "gold" : undefined} />
          <Stat label={t("boq.calculationRun.statSpecThickness", "Thickness not stated")} value={sp.thickness_missing ?? 0} tone={Number(sp.thickness_missing ?? 0) > 0 ? "gold" : undefined} />
        </Section>
      ) : null}

      {st?.enabled ? (
        st.resolved ? (
          <div className="space-y-3">
            <Section title={t("boq.calculationRun.statsStages", "Work stages")}>
              <Stat label={t("boq.calculationRun.statStageSplit", "Rows cut at a level")} value={st.rows_split ?? 0} />
              <Stat label={t("boq.calculationRun.statStageTagged", "Rows placed whole")} value={st.rows_tagged ?? 0} />
              <Stat label={t("boq.calculationRun.statStageNotSplit", "Could not be cut")} value={st.rows_not_split ?? 0} tone={Number(st.rows_not_split ?? 0) > 0 ? "gold" : undefined} />
              <Stat label={t("boq.calculationRun.statStageUnresolved", "Height unknown")} value={st.rows_unresolved ?? 0} tone={Number(st.rows_unresolved ?? 0) > 0 ? "red" : undefined} />
            </Section>
            <div>
              <div className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                {t("boq.calculationRun.statsDatums", "Reference levels (mm)")}
              </div>
              <ul className="space-y-0.5 text-[11.5px] text-[var(--color-text-secondary)]">
                {(st.datums ?? []).map((d) => (
                  <li key={d.name}>
                    <span className="inline-block w-20 font-mono font-semibold">{d.name}</span>
                    <span className="inline-block w-20 font-mono">{formatPrecise(d.z_mm, 0)}</span>
                    <span className={d.source === "default" ? "text-[var(--color-warning)]" : ""}>
                      {d.source === "model" ? t("boq.calculationRun.datumModel", "from the model")
                        : d.source === "param" ? t("boq.calculationRun.datumParam", "set on the convention")
                        : t("boq.calculationRun.datumDefault", "assumed")}
                    </span>
                    <span className="ml-2 text-[var(--color-text-muted)]">{d.note}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(st.rows_by_stage ?? {}).map(([k, v]) => (
                <span key={k} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]">
                  {stageLabel(k)}: {v}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]">
            {t("boq.calculationRun.stagesNotDerived", "Quantities were not split by stage of work")}: {st.reason ?? "—"}
          </div>
        )
      ) : null}

            {ly?.enabled ? (
        <Section title={t("boq.calculationRun.statsLayers", "Wall layers")}>
          <Stat label={t("boq.calculationRun.statLayerSplit", "Rows split by layer")} value={ly.rows_split ?? 0} />
          <Stat label={t("boq.calculationRun.statLayerMerged", "Layers of one material")} value={ly.rows_merged ?? 0} />
          <Stat label={t("boq.calculationRun.statLayerNotSplit", "Left whole")} value={ly.rows_not_split ?? 0} tone={Number(ly.rows_not_split ?? 0) > 0 ? "gold" : undefined} />
          <Stat label={t("boq.calculationRun.statLayerMismatch", "Thickness differs from layers")} value={ly.rows_mismatch ?? 0} tone={Number(ly.rows_mismatch ?? 0) > 0 ? "gold" : undefined} />
          <Stat label={t("boq.calculationRun.statLayerFinish", "Finish layers left out (m³)")} value={formatPrecise(ly.finish_excluded_m3 ?? 0, 3)} />
          <Stat label={t("boq.calculationRun.statLayerUnpriced", "Unpriced layers left out (m³)")} value={formatPrecise(ly.unpriced_m3 ?? 0, 3)} tone={Number(ly.unpriced_m3 ?? 0) > 0 ? "gold" : undefined} />
        </Section>
      ) : null}

      {dv?.enabled ? (
        dv.ran ? (
          <div className="space-y-3">
            <Section title={t("boq.calculationRun.statsDerived", "Derived works (below ground)")}>
              <Stat label={t("boq.calculationRun.statDerivedFoundations", "Footings")} value={dv.foundations ?? 0} />
              <Stat label={t("boq.calculationRun.statDerivedExcavation", "Excavation (m³)")} value={formatPrecise(dv.excavation_m3 ?? 0, 3)} />
              <Stat label={t("boq.calculationRun.statDerivedPcc", "PCC bed (m³)")} value={formatPrecise(dv.pcc_m3 ?? 0, 3)} />
              <Stat label={t("boq.calculationRun.statDerivedBackfill", "Backfill (m³)")} value={formatPrecise(dv.backfill_m3 ?? 0, 3)} />
              <Stat label={t("boq.calculationRun.statDerivedBuried", "Structure in the trench (m³)")} value={formatPrecise(dv.buried_m3 ?? 0, 3)} />
              <Stat label={t("boq.calculationRun.statDerivedBox", "Footings taken as rectangles")} value={dv.box_footprints ?? 0} tone={Number(dv.box_footprints ?? 0) > 0 ? "gold" : undefined} />
            </Section>
            {(dv.assumed?.length ?? 0) > 0 || dv.ngl_assumed ? (
              <div>
                <div className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                  {t("boq.calculationRun.derivedAssumedLabel", "Assumed (not given)")}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {[...(dv.assumed ?? []), ...(dv.ngl_assumed ? ["ngl"] : [])].map((name) => (
                    <span key={name} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 text-[11px] text-[var(--color-warning)]">
                      {t(`boq.derived.param.${name}`, name)}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">
            {dv.reason === "ALL_ITEMS_IN_MODEL"
              ? t("boq.calculationRun.derivedModelHas", "The model already draws excavation or PCC, so none was derived.")
              : `${t("boq.calculationRun.derivedNotRun", "Excavation, PCC and backfill were not worked out")}: ${dv.reason ?? "—"}`}
          </div>
        )
      ) : null}

      {genericMaterial > 0 ? (
        <Section title={t("boq.calculationRun.statsMaterial", "Material")}>
          <Stat label={t("boq.calculationRun.statMaterialGeneric", "Elements with a generic material")} value={genericMaterial} tone="gold" />
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

      <SteelRebarRange steel={stats.steel} rebar={r} />

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
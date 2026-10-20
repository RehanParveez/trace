import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { RunStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { derivedWaitingView, formworkStatsView, steelStatsView } from "../utils/derived";
import { FormworkPanel } from "./FormworkPanel";
import { DerivedExtras } from "./DerivedExtras";
import { ModelWorksPanel } from "./ModelWorksPanel";
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
  const waiting = derivedWaitingView(dv?.claims);
  const fw = formworkStatsView(dv);
  const sv = steelStatsView(dv);
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
              {Number(dv.wall_foundations ?? 0) > 0 ? (
                <Stat label={t("boq.calculationRun.statDerivedWallFoundations", "Masonry foundation walls")} value={dv.wall_foundations ?? 0} />
              ) : null}
              {Number(dv.ballast_m3 ?? 0) > 0 ? (
                <Stat label={t("boq.calculationRun.statDerivedBallast", "Brick ballast (m³)")} value={formatPrecise(dv.ballast_m3 ?? 0, 3)} />
              ) : null}
              {Number(dv.shoring_m2 ?? 0) > 0 ? (
                <Stat label={t("boq.calculationRun.statDerivedShoring", "Shoring (m²)")} value={formatPrecise(dv.shoring_m2 ?? 0, 3)} />
              ) : null}
              <Stat label={t("boq.calculationRun.statDerivedBuried", "Structure in the trench (m³)")} value={formatPrecise(dv.buried_m3 ?? 0, 3)} />
              <Stat label={t("boq.calculationRun.statDerivedBox", "Footings taken as rectangles")} value={dv.box_footprints ?? 0} tone={Number(dv.box_footprints ?? 0) > 0 ? "gold" : undefined} />
              {Number(dv.mark_positions ?? 0) > 0 ? (
                <Stat label={t("boq.calculationRun.statDerivedMarks", "Footings placed at their drawing mark")} value={dv.mark_positions ?? 0} tone="gold" />
              ) : null}
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
        ) : waiting ? (
          <div className="rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]">
            {t("boq.calculationRun.derivedNeedsLevel", {
              defaultValue:
                "{{count}} footings counted from the drawing{{tags}} are waiting for the depth of the footing bottom below natural ground. Give it in the site assumptions and calculate again.",
              count: waiting.waiting,
              tags: waiting.tags.length > 0 ? ` (${waiting.tags.join(", ")})` : "",
            })}
          </div>
        ) : (
          <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">
            {dv.reason === "ALL_ITEMS_IN_MODEL"
              ? t("boq.calculationRun.derivedModelHas", "The model already draws excavation or PCC, so none was derived.")
              : `${t("boq.calculationRun.derivedNotRun", "Excavation, PCC and backfill were not worked out")}: ${dv.reason ?? "—"}`}
          </div>
        )
       ) : null}

      {dv?.enabled ? <DerivedExtras stats={dv} /> : null}
      <ModelWorksPanel derived={dv} ranges={stats.ranges} />
      {fw ? <FormworkPanel view={fw} /> : null}
      
      {sv ? (
        sv.ran ? (
          <div className="space-y-3">
            <Section title={t("boq.calculationRun.statsSteel", "Steel (bars printed on the drawing)")}>
              <Stat label={t("boq.calculationRun.statSteelTotal", "Steel (kg)")} value={formatPrecise(sv.kg, 3)} />
              {Number(sv.wastagePct) === 0 ? (
                <Stat label={t("boq.calculationRun.statSteelWith5", "With 5 percent added (kg)")} value={formatPrecise(sv.withFivePctKg, 3)} />
              ) : (
                <Stat label={t("boq.calculationRun.statSteelBare", "Bare weight before {{pct}} percent wastage (kg)", { pct: sv.wastagePct })} value={formatPrecise(sv.bareKg, 3)} />
              )}
              {sv.categories.map((c) => (
                <Stat
                  key={c.category}
                  label={t("boq.calculationRun.statSteelCategory", {
                    defaultValue: "{{category}}, {{marks}} marks (kg)",
                    category: t(`boq.derived.category.${c.category}`, c.category),
                    marks: c.marks,
                  })}
                  value={formatPrecise(c.kg, 3)}
                />
              ))}
            </Section>
            {sv.diameters.length > 0 ? (
              <Section title={t("boq.calculationRun.statsSteelDia", "Steel by bar diameter")}>
                {sv.diameters.map((d) => (
                  <Stat key={d.diaMm} label={t("boq.calculationRun.statSteelDia", { defaultValue: "{{dia}} mm, {{len}} m (kg)", dia: Number(d.diaMm).toFixed(1), len: formatPrecise(d.lengthM, 1) })} value={formatPrecise(d.kg, 3)} />
                ))}
              </Section>
            ) : null}
            {sv.intensity.length > 0 ? (
              <Section title={t("boq.calculationRun.statsSteelIntensity", "Steel per m3 of concrete")}>
                {sv.intensity.map((r) => (
                  <Stat
                    key={r.family}
                    label={t("boq.calculationRun.statSteelIntensity", { defaultValue: "{{family}} (usual {{low}} to {{high}})", family: t(`boq.derived.family.${r.family}`, r.family), low: r.low, high: r.high })}
                    value={formatPrecise(r.kgPerM3, 1)}
                    tone={r.status === "IN_RANGE" ? undefined : "gold"}
                  />
                ))}
              </Section>
            ) : null}
            {sv.assumed.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {sv.assumed.map((name) => (
                  <span key={name} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 text-[11px] text-[var(--color-warning)]">
                    {t(`boq.derived.param.${name}`, name)}
                  </span>
                ))}
              </div>
            ) : null}
            {sv.noBars > 0 ? (
              <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">
                {t("boq.calculationRun.steelNoBars", {
                  defaultValue: "{{count}} members had no bars printed or typed, so no steel was taken for them.",
                  count: sv.noBars,
                })}
              </div>
            ) : null}
            {sv.lapAndWastageNotAdded ? (
              <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">
                {t("boq.calculationRun.steelLap", "Steel is the weight of the bars, rings and mesh as printed, cut by the cover, hook, lap and anchorage of the site assumptions. Chairs, binding wire and wastage are not added.")}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">
            {t(`boq.calculationRun.steelReason.${sv.reason ?? "NOTHING_TO_REINFORCE"}`, "Steel was not worked out from the bars printed on the drawing.")}
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

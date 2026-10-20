import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { DerivedStats, RangeStampStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { rangeStampView, reasonWords, wallFinishView, wallWorksView } from "../utils/modelWorks";

const TITLE = "text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const NOTE = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]";
const WARN = "rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]";

function Cell({ label, value, testId }: { label: string; value: ReactNode; testId: string }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3" data-testid={testId}>
      <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{label}</div>
      <div className="mt-1.5 font-mono text-[15px] font-semibold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

export function ModelWorksPanel({ derived, ranges }: { derived: DerivedStats | null | undefined; ranges?: RangeStampStats | null }) {
  const { t } = useTranslation();
  const works = wallWorksView(derived);
  const finish = wallFinishView(derived);
  const stamp = rangeStampView(ranges);
  if (!works && !finish && !stamp) return null;
  return (
    <div className="space-y-3" data-testid="model-works">
      {works ? (
        works.ran ? (
          <div className="space-y-2" data-testid="wall-works">
            <div className={TITLE}>{t("boq.modelWorks.worksTitle", "Under the walls of the model")}</div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <Cell testId="wall-works-steps" label={t("boq.modelWorks.steps", "Brick steps (m³)")} value={formatPrecise(works.brickStepsM3, 3)} />
              <Cell testId="wall-works-termite" label={t("boq.modelWorks.termite", "Termite, trench bottom (m²)")} value={formatPrecise(works.termiteM2, 3)} />
              <Cell testId="wall-works-membrane" label={t("boq.modelWorks.membrane", "Membrane (m²)")} value={formatPrecise(works.membraneM2, 3)} />
              <Cell testId="wall-works-walls" label={t("boq.modelWorks.walls", "Walls, run (m)")} value={`${works.walls} · ${formatPrecise(works.lengthM, 2)}`} />
            </div>
            <div className={NOTE} data-testid="wall-works-basis">
              {t(
                "boq.modelWorks.worksBasis",
                "The steps are not in the model. Their heights and how much narrower each is than the one below come from the QS's workbook, not from your drawings, so every row is marked assumed.",
              )}
              {works.classes.length > 0
                ? ` ${works.classes.map((c) => `${c.cls === "THIN" ? t("boq.modelWorks.thin", "Thin walls") : t("boq.modelWorks.thick", "Walls of 6 in and over")}: ${c.walls} (${c.lengthM} m)`).join("; ")}.`
                : ""}
              {works.stepOffsetMm !== null ? ` ${t("boq.modelWorks.offset", { defaultValue: "Each step is {{mm}} mm narrower.", mm: works.stepOffsetMm })}` : ""}
            </div>
            {works.belowDpc > 0 ? (
              <div className={NOTE} data-testid="wall-works-below">
                {t("boq.modelWorks.below", { defaultValue: "{{count}} wall(s) already go below the damp-proof course; their steps are taken to be in the model and none was added.", count: works.belowDpc })}
              </div>
            ) : null}
            {works.skipped.length > 0 ? (
              <div className={NOTE} data-testid="wall-works-skipped">
                {t("boq.modelWorks.skipped", "Left as they are:")} {works.skipped.map((s) => `${s.item} (${s.why})`).join(", ")}
              </div>
            ) : null}
            {works.levelAssumed ? (
              <div className={WARN} data-testid="wall-works-level">
                {t("boq.modelWorks.levelAssumed", "The damp-proof course was taken at the floor level. Give its level in the datums if it is lower.")}
              </div>
            ) : null}
          </div>
        ) : (
          <div className={NOTE} data-testid="wall-works-not-run">
            {t("boq.modelWorks.worksNotRun", "Brick steps, termite and membrane under the walls were not worked out.")} {reasonWords(works.reason)}
          </div>
        )
      ) : null}

      {finish ? (
        finish.ran ? (
          <div className="space-y-2" data-testid="wall-finishes">
            <div className={TITLE}>{t("boq.modelWorks.finishTitle", "Plaster and paint from the walls")}</div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <Cell testId="wall-finish-inside" label={t("boq.modelWorks.plasterInside", "Plaster, inside (m²)")} value={formatPrecise(finish.plasterInsideM2, 3)} />
              <Cell testId="wall-finish-outside" label={t("boq.modelWorks.plasterOutside", "Plaster, outside (m²)")} value={formatPrecise(finish.plasterOutsideM2, 3)} />
              <Cell testId="wall-finish-openings" label={t("boq.modelWorks.openingsOff", "Openings taken off (m²)")} value={formatPrecise(finish.openingsDeductedM2, 3)} />
              <Cell testId="wall-finish-walls" label={t("boq.modelWorks.finishWalls", "Walls")} value={finish.walls} />
            </div>
            <div className={NOTE} data-testid="wall-finish-basis">
              {t(
                "boq.modelWorks.finishBasis",
                "The model has no rooms, so the finishes are taken from the walls, from the damp-proof course up to the top of each wall, both faces of an inner wall and the inside and outside of an outer wall. Doors and windows are taken off. Paint is the area of the plaster. Ceilings and floors are not taken.",
              )}
            </div>
            {finish.sidesFromGeometry > 0 ? (
              <div className={WARN} data-testid="wall-finish-sides">
                {t("boq.modelWorks.sides", { defaultValue: "{{count}} wall(s) do not say whether they are outer walls. They were placed by the outline of the walls; check them.", count: finish.sidesFromGeometry })}
              </div>
            ) : null}
            {finish.openings === 0 ? (
              <div className={WARN} data-testid="wall-finish-no-openings">
                {t("boq.modelWorks.noOpenings", "The model has no door or window with a position, so nothing was taken off the walls.")}
              </div>
            ) : null}
            {finish.skipped.length > 0 ? (
              <div className={NOTE} data-testid="wall-finish-skipped">
                {t("boq.modelWorks.skipped", "Left as they are:")} {finish.skipped.join(", ")}
              </div>
            ) : null}
          </div>
        ) : (
          <div className={NOTE} data-testid="wall-finishes-not-run">
            {t("boq.modelWorks.finishNotRun", "Plaster and paint were not taken from the walls.")} {reasonWords(finish.reason)}
          </div>
        )
      ) : null}

      {stamp ? (
        <div className="space-y-2" data-testid="range-stamp">
          <div className={TITLE}>{t("boq.modelWorks.rangeTitle", "Range on every row")}</div>
          <div className={NOTE}>
            {t("boq.modelWorks.rangeText", {
              defaultValue: "{{stamped}} of {{rows}} rows were given a range by the engine (rows from the model, the works worked out from it and hand measurements). The others carry the range read from their drawing.",
              stamped: stamp.stamped,
              rows: stamp.rows,
            })}
            {stamp.grades.length > 0 ? ` ${stamp.grades.map((g) => `${t(`boq.range.grade.${g.grade}`, g.grade.toLowerCase())}: ${g.count}`).join(", ")}.` : ""}
            {stamp.unbounded > 0 ? ` ${t("boq.modelWorks.rangeOpen", { defaultValue: "{{count}} row(s) have no bound.", count: stamp.unbounded })}` : ""}
          </div>
        </div>
      ) : null}
    </div>
  );
}

import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { DerivedStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { areaReasonWords, openingAreaView, roofTreatmentView } from "../utils/areaWorks";

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

export function AreaWorksPanel({ derived }: { derived: DerivedStats | null | undefined }) {
  const { t } = useTranslation();
  const openings = openingAreaView(derived);
  const roof = roofTreatmentView(derived);
  if (!openings && !roof) return null;
  return (
    <div className="space-y-3" data-testid="area-works">
      {openings ? (
        openings.ran ? (
          <div className="space-y-2" data-testid="opening-area">
            <div className={TITLE}>{t("boq.areaWorks.openingsTitle", "Area of the doors and windows")}</div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <Cell testId="opening-area-doors" label={t("boq.areaWorks.doors", "Doors")} value={openings.doors} />
              <Cell testId="opening-area-door-m2" label={t("boq.areaWorks.doorArea", "Door area (m²)")} value={formatPrecise(openings.doorAreaM2, 3)} />
              <Cell testId="opening-area-windows" label={t("boq.areaWorks.windows", "Windows")} value={openings.windows} />
              <Cell testId="opening-area-window-m2" label={t("boq.areaWorks.windowArea", "Window area (m²)")} value={formatPrecise(openings.windowAreaM2, 3)} />
            </div>
            <div className={NOTE} data-testid="opening-area-basis">
              {t(
                "boq.areaWorks.openingsBasis",
                "Width is the long side of the box the door or window stands in, height is its height. The box is the frame, so these areas are a little more than the clear openings; every row is marked assumed.",
              )}
            </div>
            {openings.noSize > 0 ? (
              <div className={WARN} data-testid="opening-area-no-size">
                {t("boq.areaWorks.noSize", { defaultValue: "{{count}} opening(s) have no size in the model and were left out.", count: openings.noSize })}
              </div>
            ) : null}
            {openings.skipped.length > 0 ? (
              <div className={NOTE}>
                {t("boq.modelWorks.skipped", "Left as they are:")} {openings.skipped.join(", ")}
              </div>
            ) : null}
          </div>
        ) : (
          <div className={NOTE} data-testid="opening-area-not-run">
            {t("boq.areaWorks.openingsNotRun", "The area of the doors and windows was not worked out.")} {areaReasonWords(openings.reason)}
          </div>
        )
      ) : null}

      {roof ? (
        roof.ran ? (
          <div className="space-y-2" data-testid="roof-treatment">
            <div className={TITLE}>{t("boq.areaWorks.roofTitle", "Roof treatment")}</div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <Cell testId="roof-slabs" label={t("boq.areaWorks.roofSlabs", "Roof slabs")} value={roof.roofSlabs} />
              <Cell testId="roof-area" label={t("boq.areaWorks.roofArea", "Treated area (m²)")} value={formatPrecise(roof.areaM2, 3)} />
            </div>
            <div className={NOTE} data-testid="roof-basis">
              {t("boq.areaWorks.roofBasis", "The plan area of each roof slab the model measured, taken flat. The slope, the upstand and any hole in the slab are not taken; the row is marked assumed.")}
            </div>
            {roof.noPlan > 0 ? (
              <div className={WARN}>{t("boq.areaWorks.noPlan", { defaultValue: "{{count}} roof slab(s) have no plan and were left out.", count: roof.noPlan })}</div>
            ) : null}
          </div>
        ) : (
          <div className={NOTE} data-testid="roof-not-run">
            {t("boq.areaWorks.roofNotRun", "The roof treatment was not worked out.")} {areaReasonWords(roof.reason)}
          </div>
        )
      ) : null}
    </div>
  );
}

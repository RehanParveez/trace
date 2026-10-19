import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { DerivedStats } from "../types/drawings-boq.types";
import { earthBalanceView, earthFillView, floorWorksView } from "../utils/derivedExtras";
import { formatPrecise } from "../utils/drawings-boq.utils";

const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";
const NOTE = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]";

function Cell({ label, value, testId }: { label: string; value: ReactNode; testId: string }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3" data-testid={testId}>
      <div className={HEAD}>{label}</div>
      <div className="mt-1.5 font-mono text-[15px] font-semibold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

export function DerivedExtras({ stats }: { stats: DerivedStats | null | undefined }) {
  const { t } = useTranslation();
  const balance = earthBalanceView(stats);
  const fill = earthFillView(stats);
  const floor = floorWorksView(stats);
  if (!balance && !fill && !floor) return null;
  return (
    <div className="space-y-3" data-testid="derived-extras">
      {balance ? (
        <div className="space-y-2" data-testid="earth-balance">
          <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.derived.balanceTitle", "Earth balance of the dig")}</div>
          <div className="grid gap-2 sm:grid-cols-3">
            <Cell testId="balance-excavation" label={t("boq.derived.balanceExcavation", "Excavation (m³)")} value={formatPrecise(balance.excavationM3, 3)} />
            <Cell testId="balance-backfill" label={t("boq.derived.balanceBackfill", "Backfill (m³)")} value={formatPrecise(balance.backfillM3, 3)} />
            <Cell testId="balance-carted" label={t("boq.derived.balanceCarted", "Surplus to cart away (m³)")} value={formatPrecise(balance.cartedM3, 3)} />
          </div>
        </div>
      ) : null}
      {fill ? (
        <div className="space-y-2" data-testid="earth-fill">
          <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.derived.fillTitle", "Earth filling under the floors")}</div>
          <div className="grid gap-2 sm:grid-cols-3">
            <Cell testId="fill-measured" label={t("boq.derived.fillMeasured", "Filling measured (m³)")} value={formatPrecise(fill.fillM3, 3)} />
            <Cell testId="fill-need" label={t("boq.derived.fillNeed", "Loose earth needed with compaction (m³)")} value={formatPrecise(fill.needLooseM3, 3)} />
            <Cell testId="fill-surplus" label={t("boq.derived.fillSurplus", "Surplus of the dig, loose (m³)")} value={formatPrecise(fill.surplusLooseM3, 3)} />
            <Cell testId="fill-reused" label={t("boq.derived.fillReused", "Surplus used for the filling (m³)")} value={formatPrecise(fill.reusedM3, 3)} />
            <Cell testId="fill-imported" label={t("boq.derived.fillImported", "Earth brought in (m³)")} value={formatPrecise(fill.importedM3, 3)} />
            <Cell testId="fill-carted" label={t("boq.derived.fillCarted", "Surplus carted away, loose (m³)")} value={formatPrecise(fill.cartedLooseM3, 3)} />
          </div>
          <div className={NOTE} data-testid="fill-note">
            {fill.reuseOn
              ? t("boq.derived.fillReuseOn", "The surplus of the dig goes to the filling first; only the rest is carted away.")
              : t("boq.derived.fillReuseOff", "All the filling is counted as brought in, and the whole surplus of the dig as carted away. Switch on the reuse in the site assumptions to set one against the other.")}
            {fill.assumed.length > 0 ? ` ${t("boq.derived.fillAssumed", "Not given, so the standard value is used:")} ${fill.assumed.map((n) => t(`boq.derived.param.${n}`, n)).join(", ")}.` : ""}
            {` ${t("boq.derived.fillNoChange", "The balance only reports these figures; no quantity in the bill is changed by it.")}`}
          </div>
        </div>
      ) : null}
      {floor ? (
        floor.ran ? (
          <div className="space-y-2" data-testid="floor-works">
            <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.derived.floorWorksTitle", "Bed and termite treatment from the model's rooms")}</div>
            <div className="grid gap-2 sm:grid-cols-2">
              <Cell testId="floor-works-area" label={t("boq.derived.floorWorksArea", "Floor of the lowest storey (m²)")} value={formatPrecise(floor.areaM2, 3)} />
              <Cell testId="floor-works-rooms" label={t("boq.derived.floorWorksRooms", "Rooms")} value={floor.rooms} />
            </div>
            {floor.levelAssumed ? (
              <div className={`${NOTE} text-[var(--color-warning)]`} data-testid="floor-works-level">
                {t("boq.derived.floorWorksLevel", "The lowest storey was taken as the level whose members stand lowest. Check that it is the ground floor.")}
              </div>
            ) : null}
            {floor.skipped.length > 0 ? (
              <div className={NOTE} data-testid="floor-works-skipped">
                {t("boq.derived.floorWorksSkipped", "Left as they are, because they were already measured:")} {floor.skipped.map((s) => s.code).join(", ")}
              </div>
            ) : null}
          </div>
        ) : (
          <div className={NOTE} data-testid="floor-works-not-run">
            {t(`boq.derived.floorWorksReason.${floor.reason ?? "NO_ROOMS"}`, "The bed and termite treatment were not taken from the rooms of the model.")}
          </div>
        )
      ) : null}
    </div>
  );
}

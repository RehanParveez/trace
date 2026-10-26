import { useTranslation } from "react-i18next";
import type { ModelNotesStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";

const CARD = "space-y-2 rounded-[8px] border px-3 py-2 text-[12px] text-[var(--color-text-primary)]";
const WARN = `${CARD} border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)]`;
const INFO = `${CARD} border-[var(--color-border)] bg-[var(--color-surface-muted)]`;
const CHIP = "rounded-full bg-[var(--color-surface)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]";

export function ModelNotesCard({ notes }: { notes?: ModelNotesStats }) {
  const { t } = useTranslation();
  if (!notes) return null;
  const part = notes.partitions;
  const layered = notes.layered;
  const byRole = notes.billed_by_role;
  const skipped = (notes.skipped ?? []).filter((s) => s.with_volume > 0 || s.steel_named > 0);
  const hasPart = !!part && part.count > 0;
  const hasLayered = !!layered && layered.rows > 0;
  const hasRole = !!byRole && byRole.rows > 0;
  if (!hasPart && !hasLayered && !hasRole && skipped.length === 0) return null;
  return (
    <div className="space-y-2">
      {hasPart && part ? (
        <div className={WARN}>
          <div>
            {Number(part.area_m2) > 0
              ? t("boq.calculationRun.partitionsNotBilled", "{{count}} partition walls are not billed: about {{area}} m2 of wall ({{volume}} m3). They are not concrete or masonry, so they are left out of the wall totals. Your QS decides whether dry partitions are billed.", {
                  count: part.count, area: formatPrecise(part.area_m2, 1), volume: formatPrecise(part.volume_m3, 1),
                })
              : t("boq.calculationRun.partitionsNoArea", "{{count}} partition walls are not billed ({{volume}} m3). The model gives no thickness for them, so no area is counted. Your QS decides whether dry partitions are billed.", {
                  count: part.count, volume: formatPrecise(part.volume_m3, 1),
                })}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {part.groups.map((g) => (
              <span key={g.material} className={CHIP}>
                {g.material}: {g.count}{Number(g.area_m2) > 0 ? `, ${formatPrecise(g.area_m2, 1)} m2` : ""}{g.thickness_mm ? `, ${g.thickness_mm} mm` : ""}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {hasLayered && layered ? (
        <div className={WARN}>
          <div>
            {t("boq.calculationRun.layeredWhole", "{{rows}} walls, slabs or roofs list several materials in the model but not the thickness of each, so they are billed whole under one material ({{m3}} m3 in all). The quantity can be more than the masonry or concrete alone. Give the layers a thickness in the model, or give us the thickness of the structural layer.", {
              rows: layered.rows, m3: formatPrecise(layered.m3, 1),
            })}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {layered.groups.map((g) => (
              <span key={g.materials} className={CHIP}>{g.materials}: {g.rows}, {formatPrecise(g.m3, 1)} m3</span>
            ))}
          </div>
        </div>
      ) : null}

      {hasRole && byRole ? (
        <div className={INFO}>
          <div>
            {t("boq.calculationRun.billedByRole", "{{rows}} elements have no work-item mapping for their IFC type (stair flights, generic objects named as slabs or beams). They are billed under the concrete item because of their role ({{m3}} m3), and marked as assumed.", {
              rows: byRole.rows, m3: formatPrecise(byRole.m3, 2),
            })}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {byRole.groups.map((g) => (
              <span key={g.type} className={CHIP}>{g.type}: {g.rows}, {formatPrecise(g.m3, 2)} m3</span>
            ))}
          </div>
        </div>
      ) : null}

      {skipped.length > 0 ? (
        <div className={INFO}>
          <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
            {t("boq.calculationRun.skippedVolume", "Left out of the bill, with the model volume they hold")}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {skipped.map((s) => (
              <span key={s.role} className={CHIP} title={s.reason}>
                {s.role}: {s.count}, {formatPrecise(s.volume_m3, 2)} m3{s.steel_named > 0 ? `, steel about ${formatPrecise(s.steel_kg, 0)} kg` : ""}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

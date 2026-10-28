import { useTranslation } from "react-i18next";
import { Badge, ErrorState, LoadingState } from "../../../organizations/components/OrganizationUi";
import type { FloorDatums } from "../types/takeoff.types";
import { datumText, footingNote, floorRows, gradeLabel, gradeTone, unplacedFloors } from "../utils/floors";

interface Props {
  datums: FloorDatums | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}

export function FloorLevels({ datums, loading, error, onRetry }: Props) {
  const { t } = useTranslation();
  if (loading) return <LoadingState label={t("boq.takeoff.floors.loading", "Loading the floors…")} />;
  if (error) return <ErrorState title={t("boq.takeoff.floors.error", "Couldn't load the floor levels")} onRetry={onRetry} />;
  const rows = floorRows(datums);
  if (rows.length === 0) return null;
  const missing = unplacedFloors(datums);
  const footing = footingNote(datums?.footing);
  return (
    <div className="space-y-2 border-t border-[var(--color-border)] p-4" data-testid="floor-levels">
      <h3 className="text-[12px] font-semibold">{t("boq.takeoff.floors.title", "Floors in height")}</h3>
      <p className="text-[11.5px] text-[var(--color-text-secondary)]">
        {datumText(datums?.datum)} {t("boq.takeoff.floors.help", "A figure printed on a building section is firm; one taken from level marks or a typical floor height is an assumption.")}
      </p>
       {rows.some((r) => r.decisions.length > 0) ? (
        <p className="text-[11.5px] text-[var(--color-warning)]" data-testid="floor-decisions-help">
          {t("boq.takeoff.floors.decide", "Two sources give different levels for a floor. Give the right one as a reference level (FFL for the lowest floor, SLAB_1 and so on for the top of each floor) to settle it.")}
        </p>
      ) : null}
      <table className="w-full text-[11.5px]">
        <thead>
          <tr className="text-left text-[var(--color-text-muted)]">
            <th className="py-1 pr-2 font-normal">{t("boq.takeoff.floors.floor", "Floor")}</th>
            <th className="py-1 pr-2 text-right font-normal">{t("boq.takeoff.floors.level", "Level")}</th>
            <th className="py-1 pr-2 text-right font-normal">{t("boq.takeoff.floors.soffit", "Slab above, underside")}</th>
            <th className="py-1 text-right font-normal">{t("boq.takeoff.floors.top", "Slab above, top")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-t border-[var(--color-border)] align-top" data-testid={`floor-row-${r.key}`} data-placed={r.placed}>
              <td className="py-1 pr-2">
                <div className="font-semibold">{r.name}</div>
                <div className="flex flex-wrap items-center gap-1 text-[11px] text-[var(--color-text-muted)]">
                  {r.placed ? <Badge tone={gradeTone(r.grade)}>{gradeLabel(r.grade)}</Badge> : null}
                  <span>{r.reason ?? `${r.source} · ${r.levelSource}`}</span>
                </div>
                {r.sources.length > 0 ? (
                  <ul className="mt-0.5 text-[11px] text-[var(--color-text-muted)]" data-testid={`floor-sources-${r.key}`}>
                    {r.sources.map((s) => <li key={s}>{s}</li>)}
                  </ul>
                ) : null}
                {r.decisions.map((d) => (
                  <p key={d} className="mt-0.5 text-[11px] text-[var(--color-warning)]" data-testid={`floor-decision-${r.key}`} data-open={r.open}>{d}</p>
                ))}
                {r.sources.length > 0 ? (
                  <ul className="mt-0.5 text-[11px] text-[var(--color-text-muted)]" data-testid={`floor-sources-${r.key}`}>
                    {r.sources.map((s) => <li key={s}>{s}</li>)}
                  </ul>
                ) : null}
                {r.decisions.map((d) => (
                  <p key={d} className="mt-0.5 text-[11px] text-[var(--color-warning)]" data-testid={`floor-decision-${r.key}`} data-open={r.open}>{d}</p>
                ))}

              </td>
              <td className="py-1 pr-2 text-right font-mono">{r.level}</td>
              <td className="py-1 pr-2 text-right font-mono">{r.soffit}</td>
              <td className="py-1 text-right font-mono">{r.top}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {missing.length > 0 ? (
        <p className="text-[11.5px] text-[var(--color-warning)]" data-testid="floor-unplaced">
          {t("boq.takeoff.floors.unplaced", "No level for: {{floors}}. Their members get no height range.", { floors: missing.join(", ") })}
        </p>
      ) : null}
      <p className={`text-[11.5px] ${footing.tone === "green" ? "text-[var(--color-text-secondary)]" : "text-[var(--color-warning)]"}`} data-testid="floor-footing" data-tone={footing.tone}>{footing.text}</p>
    </div>
  );
}

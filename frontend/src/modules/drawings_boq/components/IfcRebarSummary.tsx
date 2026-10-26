import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { IfcRebarStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";

const heading = "mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

function Cell({ label, value, tone }: { label: string; value: ReactNode; tone?: "red" | "gold" }) {
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

export function IfcRebarSummary({ stats }: { stats?: IfcRebarStats }) {
  const { t } = useTranslation();
  if (!stats || Number(stats.bars ?? 0) === 0) {
    return null;
  }
  const bars = Number(stats.bars ?? 0);
  const measured = Number(stats.measured ?? 0);
  const notRead = Number(stats.bars_without_data ?? 0);
  const noDia = Number(stats.no_diameter ?? 0);
  const noLen = Number(stats.no_length ?? 0);
  const file = stats.file_weight;
  const diff = file?.difference_pct === null || file?.difference_pct === undefined ? null : Number(file.difference_pct);
  const dias = Object.entries(stats.by_dia ?? {});

  return (
    <div className="space-y-3">
      <div>
        <div className={heading}>{t("boq.ifcBars.title", "Bars in the model")}</div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Cell label={t("boq.ifcBars.bars", "Bars in the model")} value={bars} />
          <Cell label={t("boq.ifcBars.weighed", "Weighed")} value={measured} tone={measured < bars ? "gold" : undefined} />
          <Cell label={t("boq.ifcBars.tonnes", "Steel (tonnes)")} value={formatPrecise(stats.tonnes, 3)} />
          <Cell label={t("boq.ifcBars.length", "Bar length (m)")} value={formatPrecise(stats.length_m, 1)} />
        </div>
      </div>

      {notRead > 0 ? (
        <div className="rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-text-primary)]">
          {t("boq.ifcBars.notRead", {
            defaultValue: "{{count}} bars were stored before bar diameters and lengths were read. Upload the model again as a new revision to weigh them.",
            count: notRead,
          })}
        </div>
      ) : null}

      {noDia + noLen > 0 ? (
        <div className="text-[12px] text-[var(--color-text-secondary)]">
          {t("boq.ifcBars.unweighed", {
            defaultValue: "{{noDia}} bars give no diameter and {{noLen}} give no length, so they were not weighed. They are listed under the rejected elements.",
            noDia, noLen,
          })}
        </div>
      ) : null}

      {dias.length > 0 ? (
        <div>
          <div className="mb-1.5 text-[11px] text-[var(--color-text-muted)]">{t("boq.ifcBars.byDia", "Weight by bar diameter")}</div>
          <div className="flex flex-wrap gap-1.5">
            {dias.map(([dia, v]) => (
              <span key={dia} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]">
                {t("boq.ifcBars.diaChip", "{{dia}} mm: {{kg}} kg ({{bars}} bars)", { dia, kg: formatPrecise(v.kg, 1), bars: v.bars })}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {file && Number(file.bars ?? 0) > 0 ? (
        <div className="text-[12px] text-[var(--color-text-secondary)]">
          {t("boq.ifcBars.fileWeight", {
            defaultValue: "The model states its own weight for {{bars}} bars: {{file}} kg, against {{computed}} kg worked out here from diameter and length.",
            bars: file.bars, file: formatPrecise(file.file_kg, 1), computed: formatPrecise(file.computed_kg, 1),
          })}
          {diff !== null ? ` ${t("boq.ifcBars.fileDiff", "Difference {{pct}}%.", { pct: formatPrecise(diff, 2) })}` : ""}
        </div>
      ) : null}

      {Number(stats.no_host ?? 0) > 0 || Number(stats.length_from_geometry ?? 0) > 0 ? (
        <div className="text-[12px] text-[var(--color-text-muted)]">
          {Number(stats.no_host ?? 0) > 0
            ? t("boq.ifcBars.noHost", "{{count}} bars are not tied to a member in the model, so they appear under no member.", { count: stats.no_host })
            : ""}{" "}
          {Number(stats.length_from_geometry ?? 0) > 0
            ? t("boq.ifcBars.fromGeometry", "{{count}} bar lengths were measured from the bar's centre line, not stated by the model.", { count: stats.length_from_geometry })
            : ""}
        </div>
      ) : null}
    </div>
  );
}

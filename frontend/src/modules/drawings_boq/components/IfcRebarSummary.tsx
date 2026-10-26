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

export function IfcRebarSummary({ stats, estimated = 0 }: { stats?: IfcRebarStats; estimated?: number }) {
  const { t } = useTranslation();
  if (!stats || Number(stats.bars ?? 0) === 0) {
    return null;
  }
  const elements = Number(stats.bars ?? 0);
  const bars = Number(stats.bar_count ?? 0) || elements;
  const measured = Number(stats.measured ?? 0);
  const notRead = Number(stats.bars_without_data ?? 0);
  const absorbed = Number(stats.absorbed ?? 0);
  const partial = stats.partial;
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
          <Cell label={t("boq.ifcBars.weighed", "Bar elements weighed")} value={`${measured + absorbed} / ${elements}`} tone={measured + absorbed < elements ? "gold" : undefined} />
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

      {partial && Number(partial.hosts) > 0 ? (
        <div className="space-y-2 rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-text-primary)]">
          <div>
            {t("boq.ifcBars.partial", {
              defaultValue:
                "{{hosts}} members hold fewer modelled bars than the steel band expects ({{kg}} kg in the model). They are billed on the rule estimate, with the modelled steel as its lowest value, so the same bars are not billed twice.",
              hosts: partial.hosts, kg: formatPrecise(partial.modelled_kg, 1),
            })}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {partial.items.slice(0, 8).map((item, index) => (
              <span key={`${item.name}-${index}`} className="rounded-full bg-[var(--color-surface)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]">
                {t("boq.ifcBars.partialChip", "{{name}}: {{kg}} kg, {{perM3}} kg/m3 (band from {{low}})", {
                  name: item.name ?? item.role, kg: formatPrecise(item.modelled_kg, 1), perM3: formatPrecise(item.kg_per_m3, 1), low: formatPrecise(item.band_low, 1),
                })}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {Number(stats.host_states?.NO_BAND ?? 0) > 0 ? (
        <div className="text-[12px] text-[var(--color-text-muted)]">
          {t("boq.ifcBars.noBand", "{{count}} members hold modelled bars but have no steel band to compare with (for example pile caps and walls), so their bars are billed as modelled and may be incomplete.", {
            count: stats.host_states?.NO_BAND,
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

      {Number(stats.no_host ?? 0) > 0 && estimated > 0 ? (
        <div className="rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-text-primary)]">
          {t("boq.ifcBars.estimateOverlap", {
            defaultValue: "{{bars}} bar elements are tied to no member, and {{members}} members still carry the rule estimate. The two may cover the same steel; compare them on the Steel tab before using the total.",
            bars: stats.no_host, members: estimated,
          })}
        </div>
      ) : null}

      {Number(stats.count_assumed ?? 0) > 0 ? (
        <div className="rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-text-primary)]">
          {t("boq.ifcBars.countAssumed", {
            defaultValue: "{{count}} bar elements draw no bars and state no count, so one bar was assumed for each. Check these against the bar schedule.",
            count: stats.count_assumed,
          })}
        </div>
      ) : null}

      {Number(stats.length_mismatch ?? 0) > 0 ? (
        <div className="text-[12px] text-[var(--color-text-secondary)]">
          {t("boq.ifcBars.lengthMismatch", {
            defaultValue: "{{count}} bar elements state a bar length that differs from the drawn bars by more than the model tolerance. The drawn bars were used.",
            count: stats.length_mismatch,
          })}
        </div>
      ) : null}

      {Number(stats.no_host ?? 0) > 0 || Number(stats.length_from_geometry ?? 0) > 0 ? (
        <div className="text-[12px] text-[var(--color-text-muted)]">
          {Number(stats.no_host ?? 0) > 0
            ? t("boq.ifcBars.noHost", "{{count}} bar elements are not tied to a member in the model, so they appear under their group name or no member.", { count: stats.no_host })
            : ""}{" "}
          {Number(stats.length_from_geometry ?? 0) > 0
            ? t("boq.ifcBars.fromGeometry", "{{count}} bar elements were weighed from the drawn bars (centre line and diameter), not from stated lengths.", { count: stats.length_from_geometry })
            : ""}
        </div>
      ) : null}
    </div>
  );
}

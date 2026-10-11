import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { LedgerRowResponse, RebarStats, SteelStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";

export function ledgerRangeText(row: Pick<LedgerRowResponse, "trace" | "unit">): string | null {
  const net = row.trace?.net;
  if (!net || row.unit !== "kg" || net.kg_low === undefined || net.kg_high === undefined) return null;
  return `(${formatPrecise(net.kg_low, 0)} – ${formatPrecise(net.kg_high, 0)})`;
}

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

function Title({ children }: { children: ReactNode }) {
  return <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{children}</div>;
}

function Note({ children, tone }: { children: ReactNode; tone?: "gold" | "red" }) {
  const cls =
    tone === "red" ? "border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
    : tone === "gold" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
    : "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]";
  return <div className={`rounded-[8px] border px-3 py-2 text-[12px] ${cls}`}>{children}</div>;
}

function SteelBlock({ steel }: { steel: SteelStats }) {
  const { t } = useTranslation();
  const roles = Object.entries(steel.by_role ?? {});
  const notMeasured = Number(steel.not_measured ?? 0);
  const suspected = Number(steel.suspected_solid_sections ?? 0);
  const duplicates = Number(steel.duplicates_suspected ?? 0);
  const uncertain = Number(steel.uncertain_material ?? 0);
  return (
    <div className="space-y-2">
      <Title>{t("boq.calculationRun.statsSteel", "Structural steel")}</Title>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Cell label={t("boq.calculationRun.steelTonnes", "Sections (tonnes)")} value={formatPrecise(steel.sections_tonnes, 3)} />
        <Cell label={t("boq.calculationRun.steelKg", "Sections (kg)")} value={formatPrecise(steel.sections_kg, 2)} />
        <Cell label={t("boq.calculationRun.steelPiles", "Steel piles")} value={steel.piles ?? 0} />
        <Cell label={t("boq.calculationRun.steelPileLength", "Pile length (m)")} value={formatPrecise(steel.pile_length_m, 2)} />
        <Cell label={t("boq.calculationRun.steelMeasured", "Members measured")} value={steel.measured ?? 0} />
        <Cell label={t("boq.calculationRun.steelNotMeasured", "Members not measured")} value={notMeasured}
          tone={notMeasured > 0 ? "red" : undefined} />
        <Cell label={t("boq.calculationRun.steelSuspected", "Solid sections to check")} value={suspected}
          tone={suspected > 0 ? "gold" : undefined} />
        <Cell label={t("boq.calculationRun.steelDuplicates", "Possible duplicates")} value={duplicates}
          tone={duplicates > 0 ? "gold" : undefined} />
        <Cell label={t("boq.calculationRun.steelUncertain", "Material to confirm")} value={uncertain}
          tone={uncertain > 0 ? "gold" : undefined} />
        <Cell label={t("boq.calculationRun.steelDensity", "Density (kg/m3)")} value={steel.density_kg_m3 ?? "—"} />
      </div>
      {roles.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {roles.map(([role, v]) => (
            <span key={role} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]">
              {role}: {v.count} · {formatPrecise(v.kg, 0)} kg
            </span>
          ))}
        </div>
      ) : null}
      {(steel.piles ?? 0) > 0 ? (
        <Note>
          {t("boq.calculationRun.steelPileNote",
            "Piles are billed by driven length in metres. The model draws a pipe pile as a solid cylinder, so weighing its volume would overstate it badly.")}
        </Note>
      ) : null}
      {suspected > 0 ? (
        <Note tone="gold">
          {t("boq.calculationRun.steelSuspectedNote",
            "Some members look like solid sections: either they weigh more than 800 kg per metre or they are a plain solid rectangle or circle of section size. The model probably drew a hollow or rolled section as a solid. Check them before pricing.")}
        </Note>
      ) : null}
      {duplicates > 0 ? (
        <Note tone="gold">
          {t("boq.calculationRun.steelDuplicatesNote",
            "Some steel members sit exactly on top of another member of the same size. They are still counted; remove the copy in the model or confirm both exist.")}
        </Note>
      ) : null}
      {uncertain > 0 ? (
        <Note tone="gold">
          {t("boq.calculationRun.steelUncertainNote",
            "Some members are only described as metal or iron, or were taken as steel from their name. Give them a steel material in the model.")}
        </Note>
      ) : null}
      {notMeasured > 0 ? (
        <Note tone="red">
          {t("boq.calculationRun.steelNotMeasuredNote",
            "Some steel members have no usable model volume or length, so they were left out rather than guessed.")}
        </Note>
      ) : null}
    </div>
  );
}

function RebarBandBlock({ rebar }: { rebar: RebarStats }) {
  const { t } = useTranslation();
  const bands = Object.entries(rebar.estimate_bands ?? {});
  const dias = Object.entries(rebar.by_dia_kg ?? {}).sort((a, b) => Number(a[0]) - Number(b[0]));
  const estimated = Number(rebar.estimated_elements ?? 0);
  const measuredShare = rebar.measured_share_pct;
  return (
    <div className="space-y-2">
      <Title>{t("boq.calculationRun.statsRebarRange", "Reinforcement range")}</Title>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Cell label={t("boq.calculationRun.rebarLow", "Low (kg)")} value={formatPrecise(rebar.total_low_kg, 0)} />
        <Cell label={t("boq.calculationRun.rebarLikely", "Total, likely (kg)")} value={formatPrecise(rebar.total_kg, 0)} />
        <Cell label={t("boq.calculationRun.rebarHigh", "High (kg)")} value={formatPrecise(rebar.total_high_kg, 0)} />
        <Cell label={t("boq.calculationRun.rebarMeasuredShare", "Measured or scheduled")}
          value={measuredShare === undefined ? "—" : `${formatPrecise(measuredShare, 1)}%`} />
      </div>
      {estimated > 0 ? (
        <Note tone="gold">
          {t("boq.calculationRun.rebarRangeNote",
            "{{n}} elements carry an estimated weight, not a measured one. Likely is the planning figure; low and high show how far it can move until a bar schedule is imported.", { n: estimated })}
        </Note>
      ) : null}
      {bands.length > 0 ? (
        <div className="overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[var(--color-surface-muted)] text-[10px] uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
              <tr>
                <th className="px-3 py-2">{t("boq.calculationRun.bandFamily", "Family")}</th>
                <th className="px-3 py-2 text-right">{t("boq.calculationRun.bandElements", "Elements")}</th>
                <th className="px-3 py-2 text-right">{t("boq.calculationRun.bandConcrete", "Concrete (m3)")}</th>
                <th className="px-3 py-2 text-right">{t("boq.calculationRun.rebarLow", "Low (kg)")}</th>
                <th className="px-3 py-2 text-right">{t("boq.calculationRun.bandLikely", "Likely (kg)")}</th>
                <th className="px-3 py-2 text-right">{t("boq.calculationRun.rebarHigh", "High (kg)")}</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[var(--color-text-primary)]">
              {bands.map(([family, b]) => (
                <tr key={family} className="border-t border-[var(--color-border)]">
                  <td className="px-3 py-1.5">{family}</td>
                  <td className="px-3 py-1.5 text-right">{b.elements}</td>
                  <td className="px-3 py-1.5 text-right">{formatPrecise(b.m3, 2)}</td>
                  <td className="px-3 py-1.5 text-right">{formatPrecise(b.low_kg, 0)}</td>
                  <td className="px-3 py-1.5 text-right">{formatPrecise(b.likely_kg, 0)}</td>
                  <td className="px-3 py-1.5 text-right">{formatPrecise(b.high_kg, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {dias.length > 0 ? (
        <div>
          <div className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
            {t("boq.calculationRun.rebarByDia", "Estimated weight by bar diameter")}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {dias.map(([dia, kg]) => (
              <span key={dia} className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-text-secondary)]">
                {dia} mm: {formatPrecise(kg, 0)} kg
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function SteelRebarRange({ steel, rebar }: { steel?: SteelStats; rebar?: RebarStats }) {
  const hasSteel = !!steel && (Number(steel.elements ?? 0) > 0 || Number(steel.measured ?? 0) > 0);
  const hasRange = !!rebar && rebar.total_low_kg !== undefined && rebar.total_high_kg !== undefined;
  if (!hasSteel && !hasRange) return null;
  return (
    <div className="space-y-4">
      {hasSteel && steel ? <SteelBlock steel={steel} /> : null}
      {hasRange && rebar ? <RebarBandBlock rebar={rebar} /> : null}
    </div>
  );
}

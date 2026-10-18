import { useTranslation } from "react-i18next";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../../organizations/components/OrganizationUi";
import { useRunHistory } from "../hooks/useRunHistory";
import type { ClosenessPoint, RangePoint, RangeUnitPoint } from "../types/history.types";

const HEAD = "px-2 py-1 text-left text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";
const CELL = "px-2 py-1";

function when(at: string): string {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at : d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `${v.toFixed(1)}%`;
}

function figure(v: number): string {
  const rounded = Math.abs(v) >= 100 ? Math.round(v) : Math.round(v * 100) / 100;
  return rounded.toLocaleString("en-US");
}

function Change({ value, goodWhenUp, unit = "" }: { value: number | null; goodWhenUp: boolean; unit?: string }) {
  if (value === null || value === 0) return <span className="text-[var(--color-text-muted)]">—</span>;
  const good = goodWhenUp ? value > 0 : value < 0;
  return (
    <span className={good ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}>
      {value > 0 ? "+" : ""}
      {value.toFixed(1)}
      {unit}
    </span>
  );
}

function ClosenessTable({ points, runId }: { points: ClosenessPoint[]; runId: string }) {
  const { t } = useTranslation();
  return (
    <div className="overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
      <table className="w-full text-[12px]" data-testid="history-closeness">
        <thead>
          <tr className="bg-[var(--color-surface-muted)]">
            <th className={HEAD}>{t("drawings.history.colWhen", "Run of")}</th>
            <th className={HEAD}>{t("drawings.history.colBill", "Bill")}</th>
            <th className={`${HEAD} text-right`}>{t("drawings.history.colClose", "Closeness")}</th>
            <th className={`${HEAD} text-right`}>{t("drawings.history.colFound", "On lines found")}</th>
            <th className={`${HEAD} text-right`}>{t("drawings.history.colAdjusted", "Without QS-side")}</th>
            <th className={`${HEAD} text-right`}>{t("drawings.history.colChange", "Change")}</th>
            <th className={`${HEAD} text-right`}>{t("drawings.history.colOpen", "Open differences")}</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={`${p.run_id}|${p.label}`} className="border-t border-[var(--color-border)]" data-testid={`history-close-${p.run_id}`}>
              <td className={CELL}>
                {when(p.at)} {p.run_id === runId ? <Badge tone="gold">{t("drawings.history.thisRun", "this run")}</Badge> : null}
              </td>
              <td className={CELL}>{p.label.replace(/^[A-Z]+:/, "")}</td>
              <td className={`${CELL} text-right font-mono font-semibold`}>{pct(p.closeness_pct)}</td>
              <td className={`${CELL} text-right font-mono`}>{pct(p.found_pct)}</td>
              <td className={`${CELL} text-right font-mono`}>{pct(p.adjusted_pct)}</td>
              <td className={`${CELL} text-right font-mono`}>
                <Change value={p.change} goodWhenUp unit=" pts" />
              </td>
              <td className={`${CELL} text-right font-mono`}>{p.open_differences ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RangeTable({ unit, runs, runId }: { unit: string; runs: Array<{ point: RangePoint; u: RangeUnitPoint }>; runId: string }) {
  const { t } = useTranslation();
  return (
    <div data-testid={`history-range-${unit}`}>
      <div className="mb-1 font-semibold text-[var(--color-text-primary)]">{unit || "—"}</div>
      <div className="overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="bg-[var(--color-surface-muted)]">
              <th className={HEAD}>{t("drawings.history.colWhen", "Run of")}</th>
              <th className={`${HEAD} text-right`}>{t("drawings.history.colLikely", "Likely")}</th>
              <th className={`${HEAD} text-right`}>{t("drawings.history.colSpread", "Spread")}</th>
              <th className={`${HEAD} text-right`}>{t("drawings.history.colChange", "Change")}</th>
              <th className={`${HEAD} text-right`}>{t("drawings.history.colOpenRows", "Rows with no range")}</th>
              <th className={HEAD}>{t("drawings.history.colBiggest", "Biggest unknown")}</th>
            </tr>
          </thead>
          <tbody>
            {runs.map(({ point, u }) => (
              <tr key={point.run_id} className="border-t border-[var(--color-border)]" data-testid={`history-range-${unit}-${point.run_id}`}>
                <td className={CELL}>
                  {when(point.at)} {point.run_id === runId ? <Badge tone="gold">{t("drawings.history.thisRun", "this run")}</Badge> : null}
                </td>
                <td className={`${CELL} text-right font-mono`}>{figure(u.likely)}</td>
                <td className={`${CELL} text-right font-mono`}>{u.spread_pct === null ? "—" : `±${(u.spread_pct / 2).toFixed(1)}%`}</td>
                <td className={`${CELL} text-right font-mono`}>
                  <Change value={u.change === null ? null : u.change / 2} goodWhenUp={false} unit=" pts" />
                </td>
                <td className={`${CELL} text-right font-mono`}>
                  {u.open_rows}
                  {u.open_change ? <span className={u.open_change < 0 ? "ml-1 text-[var(--color-success)]" : "ml-1 text-[var(--color-danger)]"}>({u.open_change > 0 ? "+" : ""}{u.open_change})</span> : null}
                </td>
                <td className={CELL}>
                  {u.top_driver
                    ? `${u.top_driver.name} (${Math.round(u.top_driver.share_pct)}%)`
                    : u.open_inputs.length > 0
                      ? `${u.open_inputs[0].name} (${t("drawings.history.missing", "missing")})`
                      : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function RunHistoryPanel({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const q = useRunHistory(runId);
  if (q.isLoading) return <LoadingState label={t("drawings.history.loading", "Loading the history of this project's runs…")} />;
  if (q.isError) return <ErrorState title={t("drawings.history.loadError", "The history could not be loaded.")} onRetry={() => void q.refetch()} />;
  const d = q.data;
  if (!d || (d.closeness.length === 0 && d.ranges.length === 0)) {
    return <EmptyState icon="building" title={t("drawings.history.empty", "Nothing is recorded yet. Finish a run, or compare a QS bill, and it appears here.")} description="" />;
  }

  const units = Array.from(new Set(d.ranges.flatMap((r) => r.units.map((u) => u.unit)))).sort();
  return (
    <div className="space-y-4 px-4 py-3 text-[12.5px]" data-testid="run-history">
      <p className="text-[var(--color-text-muted)]">
        {t("drawings.history.intro", "Each run of this project is kept here. Confirm values on the drawing, run again, and the spread of the quantities narrows. A bill you compare keeps its score, so you can see whether the software is getting closer.")}
      </p>
      {d.closeness.length > 0 ? (
        <section className="space-y-1">
          <h4 className="font-semibold text-[var(--color-text-primary)]">{t("drawings.history.closeTitle", "Closeness to the QS")}</h4>
          <ClosenessTable points={d.closeness} runId={d.current_run_id} />
        </section>
      ) : null}
      {units.length > 0 ? (
        <section className="space-y-2">
          <h4 className="font-semibold text-[var(--color-text-primary)]">{t("drawings.history.rangeTitle", "How sure the quantities are, run by run")}</h4>
          {units.map((unit) => (
            <RangeTable
              key={unit}
              unit={unit}
              runId={d.current_run_id}
              runs={d.ranges.flatMap((point) => point.units.filter((u) => u.unit === unit).map((u) => ({ point, u })))}
            />
          ))}
          <p className="text-[11.5px] text-[var(--color-text-muted)]">
            {t("drawings.history.rangeNote", "The spread is how far the total could be out either way. A run that covers different drawings is not like for like.")}
          </p>
        </section>
      ) : null}
    </div>
  );
}

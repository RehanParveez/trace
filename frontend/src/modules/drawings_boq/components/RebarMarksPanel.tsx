import { Fragment, useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, EmptyState, ErrorState, LoadingState, TableShell,
} from "../../organizations/components/OrganizationUi";
import { useRunBarMarks } from "../hooks";
import { formatPrecise, isRebarProvenanceEstimate, isLowConfidence, warningInfo } from "../utils/drawings-boq.utils";
import { TraceSteps } from "./TraceSteps";

const th = "px-3 py-2.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function RebarMarksPanel({ runId, solidId }: { runId: string; solidId?: string | null }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<string | null>(null);
  const query = useRunBarMarks(runId, { solid_id: solidId ?? null });
  const rows = query.rows;

  if (query.isLoading) return <LoadingState label={t("boq.rebar.loading", "Loading bar marks…")} />;
  if (query.isError)
    return <ErrorState title={t("boq.rebar.loadError", "Couldn't load bar marks.")} onRetry={() => void query.refetch()} />;
  if (rows.length === 0)
    return (
      <EmptyState
        icon="info"
        title={t("boq.rebar.empty", "No bar marks")}
        description={t("boq.rebar.emptyDesc", "Import a bar bending schedule or add a steel estimate rule to the rule set.")}
      />
    );

  const kg = (estimate: boolean) =>
    rows.filter((m) => isRebarProvenanceEstimate(m.provenance) === estimate)
      .reduce((s, m) => s + Number(m.total_kg), 0);

  return (
    <div>
      <div className="flex flex-wrap gap-6 px-4 py-3 text-[12px] text-[var(--color-text-secondary)]">
        <span>{t("boq.rebar.fromSchedule", "From schedule")}: <b className="font-mono">{formatPrecise(kg(false), 2)} kg</b></span>
        <span>{t("boq.rebar.estimated", "Estimated")}: <b className="font-mono text-[var(--color-warning)]">{formatPrecise(kg(true), 2)} kg</b></span>
      </div>

      <TableShell>
        <table className="w-full min-w-[1100px] text-left">
          <thead className="bg-[var(--color-surface-muted)]">
            <tr>
              <th className={th}>{t("boq.rebar.colMark", "Mark")}</th>
              <th className={th}>{t("boq.rebar.colRole", "Role")}</th>
              <th className={th}>{t("boq.rebar.colShape", "Shape")}</th>
              <th className={`${th} text-right`}>{t("boq.rebar.colDia", "Dia mm")}</th>
              <th className={`${th} text-right`}>{t("boq.rebar.colCount", "Count")}</th>
              <th className={`${th} text-right`}>{t("boq.rebar.colCut", "Cut mm")}</th>
              <th className={`${th} text-right`}>{t("boq.rebar.colLaps", "Laps")}</th>
              <th className={`${th} text-right`}>{t("boq.rebar.colLength", "Total m")}</th>
              <th className={`${th} text-right`}>{t("boq.rebar.colKg", "kg")}</th>
              <th className={th}>{t("boq.rebar.colSource", "Source")}</th>
              <th className={th}>{t("boq.rebar.colStatus", "Status")}</th>
              <th className={th}>{t("boq.rebar.colWarnings", "Warnings")}</th>
              <th className={th} />
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => {
              const key = `${m.solid_id}|${m.mark}`;
              const estimate = isRebarProvenanceEstimate(m.provenance);
              return (
                <Fragment key={key}>
                  <tr className="border-t border-[var(--color-border)]">
                    <td className="px-3 py-2.5 font-mono text-[12.5px] font-semibold">{m.mark}</td>
                    <td className="px-3 py-2.5 text-[12px]">{m.role}</td>
                    <td className="px-3 py-2.5 font-mono text-[11.5px]">{m.shape_code}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {formatPrecise(m.dia_mm, 1)}
                      {m.designation ? <div className="text-[10.5px] text-[var(--color-text-muted)]">{m.designation}</div> : null}
                    </td>

                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{m.count}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{formatPrecise(m.cut_len_mm, 1)}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {m.lap_count > 0 ? `${m.lap_count} × ${formatPrecise(m.lap_len_mm, 0)}` : "—"}
                    </td>

                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{formatPrecise(m.total_len_m, 3)}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-[13px] font-semibold">{formatPrecise(m.total_kg, 3)}</td>
                    <td className="px-3 py-2.5">
                      <Badge tone={estimate ? "gold" : "blue"}>
                        {estimate ? t("boq.rebar.estimate", "Estimate") : t("boq.rebar.schedule", "Schedule")}
                      </Badge>
                      <div className={`mt-1 text-[11px] ${isLowConfidence(m.confidence) ? "text-[var(--color-warning)]" : "text-[var(--color-text-muted)]"}`}>
                        {Math.round(Number(m.confidence) * 100)}%
                      </div>
                    </td>

                    <td className="px-3 py-2.5">
                      <Badge tone={m.review_status === "REVIEW_REQUIRED" ? "gold" : m.review_status === "WAIVED" ? "slate" : "green"}>
                        {m.review_status}
                      </Badge>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {m.warnings.map((w) => (
                          <span key={w} title={warningInfo(w).message}>
                            <Badge tone={warningInfo(w).severity === "error" ? "red" : warningInfo(w).severity === "warning" ? "gold" : "slate"}>{w}</Badge>
                          </span>
                        ))}
                      </div>

                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <Button variant="ghost" size="sm" onClick={() => setOpen(open === key ? null : key)}>
                        {open === key ? t("boq.rebar.hide", "Hide working") : t("boq.rebar.working", "Working")}
                      </Button>
                    </td>
                  </tr>
                  {open === key ? (
                    <tr className="border-t border-[var(--color-border)] bg-[var(--color-surface-muted)]">
                      <td colSpan={13} className="px-4 py-3">
                        <TraceSteps steps={m.trace?.steps ?? []} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </TableShell>

      {query.hasNextPage ? (
        <div className="flex justify-center border-t border-[var(--color-border)] p-3">
          <Button variant="ghost" size="sm" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>
            {query.isFetchingNextPage ? t("common.loading") : t("boq.calculationRun.loadMore")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
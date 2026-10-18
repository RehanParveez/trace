import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../organizations/components/OrganizationUi";
import type { ConfirmFirst, DriverMark, MarkState, OpenMarks as OpenMarksData } from "../types/drawings-boq.types";
import { formatPrecise, triggerBlobDownload } from "../utils/drawings-boq.utils";
import { markHref, markLabel, worklistCsv } from "../utils/driverMarks";

const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";
const SHOW_MARKS = 4;

type Located = Pick<DriverMark, "measurement_id" | "sheet_id" | "drawing_id" | "project_id" | "page_no" | "tag" | "state">;

function StateBadge({ state }: { state: MarkState }) {
  const { t } = useTranslation();
  if (state === "confirmed") return null;
  const text: Record<Exclude<MarkState, "confirmed">, string> = {
    reopened: t("boq.marks.state.reopened", "edited since the run"),
    changed: t("boq.marks.state.changed", "re-confirmed since the run"),
    gone: t("boq.marks.state.gone", "deleted"),
  };
  return <Badge tone={state === "gone" ? "red" : "gold"}>{text[state]}</Badge>;
}

export function MarkLink({ mark }: { mark: Located }) {
  const { t } = useTranslation();
  const href = markHref(mark);
  const label = markLabel(mark, t("boq.marks.mark", "mark"));
  return (
    <span className="inline-flex items-center gap-1" data-testid={`mark-${mark.measurement_id}`}>
      {href ? (
        <Link to={href} className="font-semibold text-[var(--color-info)]" title={t("boq.marks.open", "Open on drawing")}>
          {label}
        </Link>
      ) : (
        <span className="font-semibold text-[var(--color-text-primary)]">{label}</span>
      )}
      <StateBadge state={mark.state} />
    </span>
  );
}

export function MarkList({ marks }: { marks: DriverMark[] | undefined }) {
  const { t } = useTranslation();
  if (!marks || marks.length === 0) return null;
  return (
    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11.5px]" data-testid="mark-list">
      {marks.slice(0, SHOW_MARKS).map((m) => (
        <MarkLink key={m.measurement_id} mark={m} />
      ))}
      {marks.length > SHOW_MARKS ? <span className="text-[var(--color-text-muted)]">{t("boq.marks.more", "+{{n}} more", { n: marks.length - SHOW_MARKS })}</span> : null}
    </div>
  );
}

function downloadList(unit: string, text: string): void {
  triggerBlobDownload(new Blob([`\uFEFF${text}`], { type: "text/csv;charset=utf-8" }), `marks-to-confirm-${unit || "units"}.csv`);
}

export function ConfirmFirstTable({ work, unit }: { work: ConfirmFirst | undefined; unit: string }) {
  const { t } = useTranslation();
  if (!work || (work.marks.length === 0 && work.unmarked_share_pct <= 0)) return null;
  return (
    <div className="mt-3" data-testid={`confirm-first-${unit}`}>
      <div className="flex flex-wrap items-center gap-2">
        <div className={HEAD}>{t("boq.marks.confirmTitle", "Marks to confirm first: open each one and fix its input")}</div>
        {work.marks.length > 0 ? (
          <Button size="sm" variant="ghost" type="button" onClick={() => downloadList(unit, worklistCsv(work.marks, unit))}>
            {t("boq.marks.csv", "Download list (.csv)")}
          </Button>
        ) : null}
      </div>
      {work.marks.length > 0 ? (
        <>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.marks.confirmHint", "Ranked by how much of this total's spread goes away if that one mark were exact.")}{" "}
            {work.halved_after !== null ? t("boq.marks.halved", "Confirming the first {{n}} marks halves the spread of this total.", { n: work.halved_after }) : null}
          </p>
          <div className="mt-1 overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-[var(--color-surface-muted)] text-left">
                  <th className={`${HEAD} px-3 py-2`}>#</th>
                  <th className={`${HEAD} px-3 py-2`}>{t("boq.marks.colMark", "Mark")}</th>
                  <th className={`${HEAD} px-3 py-2`}>{t("boq.marks.colItems", "Feeds")}</th>
                  <th className={`${HEAD} px-3 py-2`}>{t("boq.marks.colShare", "Share of the spread")}</th>
                  <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.marks.colExact", "Range if this mark were exact")}</th>
                  <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.marks.colRunning", "Range after this one and those above")}</th>
                </tr>
              </thead>
              <tbody>
                {work.marks.map((m, i) => (
                  <tr key={m.measurement_id} className="border-t border-[var(--color-border)] align-top" data-testid={`confirm-mark-${m.measurement_id}`}>
                    <td className="px-3 py-1.5 font-mono text-[var(--color-text-muted)]">{i + 1}</td>
                    <td className="px-3 py-1.5">
                      <MarkLink mark={m} />
                    </td>
                    <td className="px-3 py-1.5 text-[11.5px] text-[var(--color-text-muted)]">{m.items.join(" · ")}</td>
                    <td className="px-3 py-1.5">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-20 rounded-full bg-[var(--color-surface-muted)]" aria-hidden="true">
                          <div className="h-2 rounded-full bg-[var(--color-primary)]" style={{ width: `${Math.min(100, Math.max(0, m.share_pct))}%` }} />
                        </div>
                        <span className="font-mono">{m.share_pct.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono">
                      {formatPrecise(m.low_after, 3)} – {formatPrecise(m.high_after, 3)}
                      <div className="text-[10.5px] text-[var(--color-text-muted)]">{t("boq.marks.narrows", "narrows {{pct}}%", { pct: m.narrows_pct.toFixed(1) })}</div>
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono">
                      {formatPrecise(m.cum_low, 3)} – {formatPrecise(m.cum_high, 3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      {work.total_marks > work.marks.length ? (
        <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">{t("boq.marks.shown", "Showing {{shown}} of {{total}} marks.", { shown: work.marks.length, total: work.total_marks })}</p>
      ) : null}
      {work.unmarked_share_pct > 0 ? (
        <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]" data-testid="unmarked-share">
          {t("boq.marks.unmarked", "{{pct}}% of the spread comes from rows that were not measured from a PDF mark (the model or derived rows). They are not in this list.", {
            pct: work.unmarked_share_pct.toFixed(1),
          })}
        </p>
      ) : null}
    </div>
  );
}

export function OpenMarks({ work, unit }: { work: OpenMarksData | undefined; unit: string }) {
  const { t } = useTranslation();
  if (!work || (work.marks.length === 0 && work.unmarked_quantity <= 0)) return null;
  return (
    <div className="mt-3" data-testid={`open-marks-${unit}`}>
      <div className={HEAD}>{t("boq.marks.openTitle", "Marks with an input that was not found")}</div>
      {work.marks.length > 0 ? (
        <>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.marks.openHint", "These carry quantity with no range yet. Open each one and give the missing size.")}
          </p>
          <ul className="mt-1 list-none space-y-1 pl-0 text-[12px]">
            {work.marks.map((m) => (
              <li key={m.measurement_id} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 rounded-[6px] border border-[var(--color-border)] px-3 py-1.5" data-testid={`open-mark-${m.measurement_id}`}>
                <MarkLink mark={m} />
                <span className="font-mono">
                  {formatPrecise(m.quantity, 3)} {unit}
                </span>
                {m.share_of_quantity_pct !== null ? (
                  <span className="text-[var(--color-text-muted)]">{t("boq.drivers.ofTotal", "{{pct}}% of the total", { pct: m.share_of_quantity_pct.toFixed(1) })}</span>
                ) : null}
                <span className="text-[11.5px] text-[var(--color-text-muted)]">{m.items.join(" · ")}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {work.total_marks > work.marks.length ? (
        <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">{t("boq.marks.shown", "Showing {{shown}} of {{total}} marks.", { shown: work.marks.length, total: work.total_marks })}</p>
      ) : null}
      {work.unmarked_quantity > 0 ? (
        <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">
          {t("boq.marks.openUnmarked", "{{qty}} {{unit}} with a missing input is not on any PDF mark.", { qty: formatPrecise(work.unmarked_quantity, 3), unit })}
        </p>
      ) : null}
    </div>
  );
}

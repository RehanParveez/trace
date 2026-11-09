import { useTranslation } from "react-i18next";
import { Badge, TableShell } from "../../../../organizations/components/OrganizationUi";
import { CropByUrl } from "../../review/components/ReviewCrop";
import type { AccuracyReport } from "../types/flow.types";
import { bandTone, hasConfidence, notReadTotal, pctText, RANK_TEXT, sectionsByGap } from "../utils/accuracy";
import { moneyOrDash } from "../utils/flow";

interface Props {
  report: AccuracyReport;
}

export function AccuracyReportView({ report }: Props) {
  const { t } = useTranslation();
  const c = report.coverage;
  const m = report.money;
  const notRead = notReadTotal(c);
  return (
    <div className="space-y-5 text-[12.5px]" data-testid="accuracy-report">
      <p className="text-[var(--color-text-secondary)]">{report.intro}</p>

      <section className="space-y-2" data-testid="accuracy-coverage">
        <h3 className="text-[13px] font-semibold">{t("boq.flow.accuracyRead", "What was read")}</h3>
        {c.note ? <p className="font-semibold text-[var(--color-warning)]" data-testid="accuracy-not-read-note">{c.note}</p> : null}
        <TableShell>
          <table className="w-full min-w-[560px] text-left" data-testid="accuracy-coverage-table">
            <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase text-[var(--color-text-muted)]">
              <tr>
                <th className="px-3 py-2">{t("boq.flow.accSection", "Section")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.accMeasured", "Measured")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.accAssumed", "Assumed")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.accAsked", "Asked")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.accNotRead", "Not read")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.accWithQty", "With a quantity")}</th>
              </tr>
            </thead>
            <tbody>
              {sectionsByGap(c).map((s) => (
                <tr key={s.section} className="border-t border-[var(--color-border)]" data-testid={`accuracy-section-${s.section}`}>
                  <td className="px-3 py-2">{s.section}</td>
                  <td className="px-3 py-2 text-right font-mono">{s.MEASURED}</td>
                  <td className="px-3 py-2 text-right font-mono">{s.ASSUMED}</td>
                  <td className="px-3 py-2 text-right font-mono">{s.ASKED}</td>
                  <td className="px-3 py-2 text-right font-mono">{s.NOT_READ > 0 ? <Badge tone="gold">{s.NOT_READ}</Badge> : s.NOT_READ}</td>
                  <td className="px-3 py-2 text-right font-mono">{pctText(s.with_quantity_pct)}</td>
                </tr>
              ))}
              <tr className="border-t-2 border-[var(--color-border)] font-semibold">
                <td className="px-3 py-2">{t("boq.flow.accAll", "All sections")}</td>
                <td className="px-3 py-2 text-right font-mono">{c.total.MEASURED}</td>
                <td className="px-3 py-2 text-right font-mono">{c.total.ASSUMED}</td>
                <td className="px-3 py-2 text-right font-mono">{c.total.ASKED}</td>
                <td className="px-3 py-2 text-right font-mono" data-testid="accuracy-not-read-total">{notRead}</td>
                <td className="px-3 py-2 text-right font-mono">{pctText(c.total.with_quantity_pct)}</td>
              </tr>
            </tbody>
          </table>
        </TableShell>
        {c.not_read_items.length > 0 ? (
          <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]" data-testid="accuracy-not-read-items">
            {c.not_read_items.map((n) => (
              <li key={n.section}><span className="font-medium">{n.section}:</span> {n.items.join(", ")}{n.more ? t("boq.flow.accAndMore", " and {{n}} more", { n: n.more }) : ""}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="space-y-2" data-testid="accuracy-money">
        <h3 className="text-[13px] font-semibold">{t("boq.flow.accMoney", "The money")}</h3>
        {m.priced ? (
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label={t("boq.flow.total", "Total of priced lines")} value={moneyOrDash(m.total)} />
            <Stat label={t("boq.flow.measured", "Measured")} value={moneyOrDash(m.measured)} />
            <Stat label={t("boq.flow.accOnAssumptions", "Resting on assumptions")} value={`${moneyOrDash(m.assumed)} (${pctText(m.assumed_pct)})`} />
            <Stat label={t("boq.flow.accNoRate", "Lines with no rate")} value={`${m.unpriced_lines} / ${m.lines}`} />
          </div>
        ) : <p className="text-[var(--color-text-muted)]">{m.note}</p>}
      </section>

      <section className="space-y-2" data-testid="accuracy-confidence">
        <h3 className="text-[13px] font-semibold">{t("boq.flow.accSure", "How sure Trace is")}</h3>
        {hasConfidence(report) ? (
          <TableShell>
            <table className="w-full min-w-[420px] text-left">
              <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-3 py-2">{t("boq.flow.colConfidence", "Confidence")}</th>
                  <th className="px-3 py-2 text-right">{t("boq.flow.accLines", "Lines")}</th>
                  <th className="px-3 py-2 text-right">{report.confidence.basis === "MONEY" ? t("boq.flow.accMoneyCol", "Money") : "-"}</th>
                  <th className="px-3 py-2 text-right">{t("boq.flow.accShare", "Share")}</th>
                </tr>
              </thead>
              <tbody>
                {report.confidence.bands.map((b) => (
                  <tr key={b.band} className="border-t border-[var(--color-border)]" data-testid={`accuracy-band-${b.band}`}>
                    <td className="px-3 py-2"><Badge tone={bandTone(b.band)}>{b.band}</Badge></td>
                    <td className="px-3 py-2 text-right font-mono">{b.lines}</td>
                    <td className="px-3 py-2 text-right font-mono">{b.amount === null ? "" : moneyOrDash(b.amount)}</td>
                    <td className="px-3 py-2 text-right font-mono">{pctText(b.pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        ) : <p className="text-[var(--color-text-muted)]" data-testid="accuracy-confidence-hidden">{report.confidence.why}</p>}
      </section>

      <section className="space-y-2" data-testid="accuracy-questions">
        <h3 className="text-[13px] font-semibold">{t("boq.flow.accQuestions", "Open questions")} ({report.questions.open})</h3>
        {report.questions.open === 0 ? <p className="text-[var(--color-text-muted)]">{t("boq.flow.accNoQuestions", "No review row is open.")}</p> : (
          <>
            <p className="text-[var(--color-text-muted)]">
              {report.questions.money === null
                ? t("boq.flow.accQuestionsNoMoney", "None of these has a money figure yet.")
                : t("boq.flow.accQuestionsMoney", "Money waiting on them: {{m}}", { m: moneyOrDash(report.questions.money) })}
              {report.questions.money !== null && report.questions.unvalued > 0 ? ` ${t("boq.flow.accUnvalued", "{{n}} have no money figure.", { n: report.questions.unvalued })}` : ""}
            </p>
            <ul className="space-y-1">
              {report.questions.rows.map((q) => (
                <li key={q.key} className="flex flex-wrap items-baseline gap-2 rounded-[8px] border border-[var(--color-border)] px-3 py-1.5" data-testid={`accuracy-question-${q.key}`}>
                  <span className="min-w-[14rem] flex-1">{q.item}{q.prompt ? `: ${q.prompt}` : ""}</span>
                  {q.page ? <span className="text-[11px] text-[var(--color-text-muted)]">{t("boq.flow.accSheet", "sheet {{p}}", { p: q.page })}</span> : null}
                  <span className="font-mono">{moneyOrDash(q.effect_rs)}</span>
                </li>
              ))}
            </ul>
            {report.questions.more > 0 ? <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.flow.accMore", "{{n}} more are in the review list.", { n: report.questions.more })}</p> : null}
          </>
        )}
      </section>

      <section className="space-y-2" data-testid="accuracy-assumptions">
        <h3 className="text-[13px] font-semibold">{t("boq.flow.accAssumptions", "Assumptions and where they come from")} ({report.assumptions.count})</h3>
        {report.assumptions.rows.length === 0 ? <p className="text-[var(--color-text-muted)]">{t("boq.flow.accNoAssumptions", "No quantity rests on an assumed input.")}</p> : (
          <ul className="space-y-1">
            {report.assumptions.rows.map((a) => (
              <li key={a.input} className="rounded-[8px] border border-[var(--color-border)] px-3 py-1.5" data-testid={`accuracy-assumption-${a.input}`}>
                <span className="font-medium">{a.input.replaceAll("_", " ")}</span>: {String(a.value)} {a.unit ?? ""}
                {a.range ? <span className="text-[var(--color-text-muted)]"> ({a.range[0]} to {a.range[1]})</span> : null}
                <span className="block text-[11.5px] text-[var(--color-text-muted)]">{a.source} · {t("boq.flow.accItems", "{{n}} item(s)", { n: a.items })}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2" data-testid="accuracy-check-first">
        <h3 className="text-[13px] font-semibold">{t("boq.flow.accCheckFirst", "Check these first")}</h3>
        <p className="text-[var(--color-text-muted)]">{RANK_TEXT[report.check_first.ranked_by]}</p>
        {report.check_first.lines.length === 0 ? <p className="text-[var(--color-text-muted)]">{t("boq.flow.accNothingFirst", "Nothing to check first.")}</p> : (
          <ol className="space-y-2">
            {report.check_first.lines.map((l, n) => (
              <li key={`${l.code}-${l.floor ?? ""}-${n}`} className="grid gap-2 rounded-[8px] border border-[var(--color-border)] p-3 md:grid-cols-[1fr_minmax(0,320px)]" data-testid={`accuracy-check-${l.code}`}>
                <div>
                  <div className="font-medium">{l.code} {l.description ?? ""}{l.floor ? ` · ${l.floor}` : ""}</div>
                  <div className="text-[11.5px] text-[var(--color-text-muted)]">
                    {moneyOrDash(l.amount)}{l.band ? ` · ${l.band}` : ""}{l.open_rows ? ` · ${t("boq.flow.accOpenRows", "{{n}} open row(s)", { n: l.open_rows })}` : ""}
                    {l.pages.length ? ` · ${t("boq.flow.accSheets", "sheets {{p}}", { p: l.pages.join(", ") })}` : ""}
                  </div>
                  {l.why ? <div className="text-[11.5px] text-[var(--color-text-secondary)]">{l.why}</div> : null}
                </div>
                <CropByUrl url={l.crop_url} item={l.code} page={l.pages[0] ?? null} />
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="space-y-1" data-testid="accuracy-track">
        <h3 className="text-[13px] font-semibold">{t("boq.flow.accTrack", "Track record")}</h3>
        <p data-testid="accuracy-track-text">{report.track_record.text}</p>
        <p className="text-[11.5px] text-[var(--color-text-muted)]">{report.track_record.rule}</p>
        {report.track_record.unscored_sets.length > 0 ? <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.flow.accUnscored", "Entered as first sight and not yet scored: {{s}}.", { s: report.track_record.unscored_sets.join(", ") })}</p> : null}
      </section>
      <p className="text-[11px] text-[var(--color-text-muted)]">{report.footer}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
      <div className="text-[11px] uppercase text-[var(--color-text-muted)]">{label}</div>
      <div className="font-mono text-[14px] font-semibold">{value}</div>
    </div>
  );
}

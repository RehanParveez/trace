import { useTranslation } from "react-i18next";
import { Badge, EmptyState, ErrorState, LoadingState, Panel, PanelHeader } from "../../organizations/components/OrganizationUi";
import { useBOQValueAtRisk } from "../hooks";
import type { ValueAtRisk, ValueAtRiskFlag, ValueAtRiskLine } from "../types/drawings-boq.types";
import { formatCurrency, formatPrecise } from "../utils/drawings-boq.utils";
import { useGradeLabel } from "../utils/gradeLabel";
import { gradeTone } from "../utils/quantityRange";

const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";

function Figure({ label, value, hint, testId }: { label: string; value: string; hint?: string; testId: string }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] px-3 py-2" data-testid={testId}>
      <div className={HEAD}>{label}</div>
      <div className="mt-0.5 font-mono text-[14px] font-semibold text-[var(--color-text-primary)]">{value}</div>
      {hint ? <div className="mt-0.5 text-[11.5px] text-[var(--color-text-muted)]">{hint}</div> : null}
    </div>
  );
}

function Names({ lines }: { lines: ValueAtRiskLine[] }) {
  if (lines.length === 0) return null;
  return <span className="text-[var(--color-text-muted)]">{lines.map((l) => l.name ?? "—").join(" · ")}</span>;
}

function LineTable({ lines, withSwing }: { lines: ValueAtRiskLine[]; withSwing: boolean }) {
  const { t } = useTranslation();
  const gradeLabel = useGradeLabel();
  return (
    <div className="mt-1 overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="bg-[var(--color-surface-muted)] text-left">
            <th className={`${HEAD} px-3 py-2`}>{t("boq.risk.colItem", "Item")}</th>
            <th className={`${HEAD} px-3 py-2`}>{t("boq.risk.colBasis", "Weakest input")}</th>
            <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.risk.colAmount", "Amount")}</th>
            {withSwing ? <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.risk.colSwing", "Could move")}</th> : null}
          </tr>
        </thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.item_id} className="border-t border-[var(--color-border)]" data-testid={`risk-line-${l.item_id}`}>
              <td className="px-3 py-1.5 font-semibold text-[var(--color-text-primary)]">{l.name ?? "—"}</td>
              <td className="px-3 py-1.5">{l.weakest ? <Badge tone={gradeTone(l.weakest)}>{gradeLabel(l.weakest)}</Badge> : null}</td>
              <td className="px-3 py-1.5 text-right font-mono">{formatCurrency(l.amount ?? null)}</td>
              {withSwing ? (
                <td className="px-3 py-1.5 text-right font-mono">
                  −{formatCurrency(l.down ?? 0)} / +{formatCurrency(l.up ?? 0)}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Flags({ flags }: { flags: ValueAtRiskFlag[] }) {
  const { t } = useTranslation();
  if (flags.length === 0) {
    return <p className="mt-2 text-[12px] text-[var(--color-text-secondary)]">{t("boq.risk.flagsNone", "Every priced line has a published rate in force.")}</p>;
  }
  return (
    <ul className="mt-1 list-none space-y-1.5 pl-0 text-[12px]">
      {flags.map((f) => (
        <li key={f.code} className="rounded-[6px] border border-[var(--color-border)] px-3 py-2" data-testid={`rate-flag-${f.code}`}>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={f.code === "NO_RATE" || f.code === "RATE_ZERO" ? "red" : "gold"}>{t(`boq.risk.flag.${f.code}`, f.code.replace(/_/g, " ").toLowerCase())}</Badge>
            <span className="font-mono">{t("boq.risk.flagItems", "{{n}} lines", { n: f.items })}</span>
            {f.amount !== null ? <span className="font-mono">{formatCurrency(f.amount)}</span> : null}
          </div>
          <div className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">{t(`boq.risk.flagText.${f.code}`, f.text)}</div>
          <div className="mt-0.5 text-[11.5px]">
            <Names lines={f.top_items} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function Body({ data }: { data: ValueAtRisk }) {
  const { t } = useTranslation();
  const gradeLabel = useGradeLabel();
  const x = data.totals;
  return (
    <div data-testid="value-at-risk">
      <div className="grid gap-2 border-b border-[var(--color-border)] px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
        <Figure testId="risk-likely" label={t("boq.risk.likely", "Priced bill")} value={formatCurrency(x.likely)} hint={t("boq.risk.pricedCount", "{{n}} priced lines", { n: x.priced_items })} />
        <Figure
          testId="risk-band"
          label={t("boq.risk.band", "Likely range")}
          value={`${formatCurrency(x.low)} – ${formatCurrency(x.high)}`}
          hint={t("boq.risk.bandHint", "Worst case if every line is out the same way: {{low}} – {{high}}", { low: formatCurrency(x.worst_low), high: formatCurrency(x.worst_high) })}
        />
        <Figure
          testId="risk-assumed"
          label={t("boq.risk.assumed", "Resting on assumption")}
          value={formatCurrency(x.behind_assumption)}
          hint={x.behind_assumption_pct === null ? undefined : t("boq.risk.ofBill", "{{pct}}% of the priced bill", { pct: x.behind_assumption_pct.toFixed(1) })}
        />
        <Figure
          testId="risk-open"
          label={t("boq.risk.open", "No bound on the quantity")}
          value={formatCurrency(x.open_amount)}
          hint={x.open_amount_pct === null ? undefined : t("boq.risk.ofBill", "{{pct}}% of the priced bill", { pct: x.open_amount_pct.toFixed(1) })}
        />
      </div>
      {x.minimum_amount > 0 || x.unpriced_items > 0 || x.labour_left_out > 0 || x.typed_amount > 0 ? (
        <ul className="m-0 list-none space-y-0.5 border-b border-[var(--color-border)] px-5 py-3 text-[11.5px] text-[var(--color-text-secondary)]">
          {x.minimum_amount > 0 ? <li>{t("boq.risk.minimum", "{{amount}} is on lines that leave something out, so it is a minimum, not a total.", { amount: formatCurrency(x.minimum_amount) })}</li> : null}
          {x.unpriced_items > 0 ? <li className="text-[var(--color-warning)]">{t("boq.risk.unpriced", "{{n}} lines have a quantity and no rate, so they add nothing to the bill yet.", { n: x.unpriced_items })}</li> : null}
          {x.typed_amount > 0 ? <li>{t("boq.risk.typed", "{{amount}} is on lines a person typed; they are not at risk of being misread.", { amount: formatCurrency(x.typed_amount) })}</li> : null}
          {x.labour_left_out > 0 ? <li>{t("boq.risk.labour", "Labour lines ({{amount}}) are left out: they repeat the quantity of the material they follow.", { amount: formatCurrency(x.labour_left_out) })}</li> : null}
        </ul>
      ) : null}
      <section className="border-b border-[var(--color-border)] px-5 py-4">
        <div className={HEAD}>{t("boq.risk.byGrade", "How the priced bill was found")}</div>
        <ul className="mt-1 list-none space-y-1 pl-0 text-[12px]">
          {data.by_grade.map((g) => (
            <li key={g.grade} className="flex flex-wrap items-center gap-2" data-testid={`risk-grade-${g.grade}`}>
              <Badge tone={gradeTone(g.grade)}>{g.grade === "NOT_GRADED" ? t("boq.risk.notGraded", "never graded") : gradeLabel(g.grade)}</Badge>
              <span className="font-mono">{formatCurrency(g.amount)}</span>
              {g.share_pct !== null ? <span className="font-mono text-[var(--color-text-muted)]">{formatPrecise(g.share_pct, 1)}%</span> : null}
              <span className="text-[var(--color-text-muted)]">{t("boq.risk.flagItems", "{{n}} lines", { n: g.items })}</span>
            </li>
          ))}
        </ul>
      </section>
      {data.top_swing.length > 0 ? (
        <section className="border-b border-[var(--color-border)] px-5 py-4">
          <div className={HEAD}>{t("boq.risk.topSwing", "Lines that could move the bill most")}</div>
          <LineTable lines={data.top_swing} withSwing />
        </section>
      ) : null}
      {data.top_open.length > 0 ? (
        <section className="border-b border-[var(--color-border)] px-5 py-4">
          <div className={HEAD}>{t("boq.risk.topOpen", "Largest amounts with no bound on the quantity")}</div>
          <LineTable lines={data.top_open} withSwing={false} />
        </section>
      ) : null}
      <section className="px-5 py-4">
        <div className={HEAD}>{t("boq.risk.flagsTitle", "Rates in doubt")}</div>
        <Flags flags={data.flags} />
      </section>
    </div>
  );
}

export function ValueAtRiskPanel({ versionId }: { versionId: string }) {
  const { t } = useTranslation();
  const q = useBOQValueAtRisk(versionId);
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.risk.eyebrow", "MONEY AT RISK")}
        title={t("boq.risk.title", "What the unknowns put at risk in the bill")}
        description={t(
          "boq.risk.description",
          "Each line's amount moves with its quantity range. The bill's range adds the lines as if they err independently; the worst case adds them as if every line were out the same way. Rates that were guessed, converted or taken without a clear specification are listed with the money that rides on them.",
        )}
      />
      {q.isLoading ? (
        <LoadingState label={t("boq.risk.loading", "Working out the money at risk…")} />
      ) : q.isError ? (
        <ErrorState title={t("boq.risk.loadError", "The money at risk could not be worked out.")} onRetry={() => void q.refetch()} />
      ) : !q.data || q.data.totals.priced_items + q.data.totals.unpriced_items === 0 ? (
        <EmptyState icon="building" title={t("boq.risk.empty", "There are no lines to value yet.")} description="" />
      ) : (
        <Body data={q.data} />
      )}
    </Panel>
  );
}

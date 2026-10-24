import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, Field, inputClass, LoadingState, Panel, PanelHeader, StatCard, TableShell, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { useRateBooks } from "../../hooks";
import type { RateBook } from "../../types/pricing.types";
import { canEscalate, deltaClass, formatDate, formatPercent, rateBookTitle } from "../../utils/pricing.utils";
import { useCompareBooks, useEscalationsFromCompare, useRateHistory } from "../hooks/useSchedules";
import type { CompareLine, CompareMatch, EscalationFromCompareResult, EscalationStatus } from "../types/schedules.types";
import { formatRate } from "../utils/schedules.utils";

const LINE_CAP = 200;
const STATUS_TONE: Record<CompareLine["status"], "green" | "red" | "gold" | "slate"> = { ADDED: "green", REMOVED: "red", CHANGED: "gold", UNIT_MISMATCH: "slate" };
const STATUS_LABEL: Record<CompareLine["status"], string> = { ADDED: "Only in the other book", REMOVED: "Not in the other book", CHANGED: "Changed", UNIT_MISMATCH: "Units don't convert" };

const ESC_TONE: Record<EscalationStatus, "green" | "red" | "gold" | "slate" | "blue"> = { NEW: "blue", ADDED: "green", EXISTS: "slate", UNCHANGED: "slate", OUT_OF_RANGE: "red", NO_TRADE: "gold", TOO_FEW: "gold" };
const ESC_LABEL: Record<EscalationStatus, string> = {
  NEW: "Will be added",
  ADDED: "Added",
  EXISTS: "Already there on this date",
  UNCHANGED: "No change (×1)",
  OUT_OF_RANGE: "Outside ×0.5 to ×3: type it by hand if it is right",
  NO_TRADE: "These rates have no trade name",
  TOO_FEW: "Fewer than 5 matched rates",
};

export function BookToolsPanel({ book, canManage = false }: { book: RateBook; canManage?: boolean }) {
  return (
    <div className="space-y-7">
      <ComparePanel book={book} canManage={canManage} />
      <HistoryPanel book={book} />
    </div>
  );
}

function ComparePanel({ book, canManage }: { book: RateBook; canManage: boolean }) {
  const { t } = useTranslation();
  const books = useRateBooks({});
  const [otherId, setOtherId] = useState("");
  const [matchOn, setMatchOn] = useState<CompareMatch>("code");
  const compare = useCompareBooks(book.id, otherId, matchOn);
  const others = books.books.filter((b) => b.id !== book.id && b.status !== "DRAFT");
  const result = compare.data;

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("schedules.compare.eyebrow", "COMPARE")}
        title={t("schedules.compare.title", "Compare with another edition")}
        description={t("schedules.compare.desc", "This book is the “before”, the one you pick is the “after”. Rates in a different unit of the same kind (cft against m³) are converted before they are compared.")}
      />
      <div className="grid gap-4 border-b border-[var(--color-border)] p-4 sm:grid-cols-[1fr_220px]">
        <Field label={t("schedules.compare.other", "Compare with")}>
          <select className={inputClass} value={otherId} onChange={(e) => setOtherId(e.target.value)}>
            <option value="">{t("schedules.compare.choose", "Choose a published book…")}</option>
            {others.map((b) => <option key={b.id} value={b.id}>{rateBookTitle(b)} — {b.name}</option>)}
          </select>
        </Field>
        <Field label={t("schedules.compare.match", "Match rows by")}>
          <select className={inputClass} value={matchOn} onChange={(e) => setMatchOn(e.target.value as CompareMatch)}>
            <option value="code">{t("schedules.compare.byCode", "Work item code")}</option>
            <option value="csr_ref">{t("schedules.compare.byRef", "Reference number")}</option>
          </select>
        </Field>
      </div>
      {!otherId ? (
        <EmptyState icon="trend" title={t("schedules.compare.emptyTitle", "Pick an edition to compare")} description={t("schedules.compare.emptyDesc", "You see what was added, removed and repriced, and the typical change per trade.")} />
      ) : compare.isLoading ? <LoadingState label={t("schedules.compare.loading", "Comparing…")} /> : compare.isError || !result ? (
        <div className="p-5"><ErrorState title={t("schedules.compare.error", "We couldn't compare these books")} onRetry={() => void compare.refetch()} /></div>
      ) : (
        <div className="space-y-5 p-5">
          <div className="grid gap-3 sm:grid-cols-4">
            <StatCard label={t("schedules.compare.changed", "Repriced")} value={result.counts.changed} note={t("schedules.compare.unchanged", "{{n}} unchanged", { n: result.counts.unchanged })} icon="trend" tone="gold" />
            <StatCard label={t("schedules.compare.median", "Typical change")} value={result.median_change_pct ? formatPercent(result.median_change_pct, 1) : "—"} note={t("schedules.compare.medianNote", "Median of repriced rates")} icon="trend" tone="blue" />
            <StatCard label={t("schedules.compare.added", "Only in the other")} value={result.counts.added} note={t("schedules.compare.addedNote", "New items")} icon="check" tone="green" />
            <StatCard label={t("schedules.compare.removed", "Not in the other")} value={result.counts.removed} note={t("schedules.compare.removedNote", "{{n}} units don't convert", { n: result.counts.unit_mismatch })} icon="alert" tone="blue" />
          </div>

          {result.suggested_factors.length > 0 ? (
            <div>
              <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">{t("schedules.compare.factors", "Typical change per trade (5 or more matches)")}</div>
              <div className="flex flex-wrap gap-2">
                {result.suggested_factors.map((f) => (
                  <Badge key={f.trade} tone="blue">{f.trade}: ×{f.median_ratio} ({f.matched})</Badge>
                ))}
              </div>
              <div className="mt-1.5 text-[12px] text-[var(--color-text-muted)]">{t("schedules.compare.factorsHint", "Use these as a starting point for a dated escalation on the older book.")}</div>
            </div>
          ) : null}

          {canManage && canEscalate(book) ? <EscalationApproval book={book} otherId={otherId} matchOn={matchOn} otherFrom={result.book_b.effective_from} /> : null}

          <TableShell>
            <table className="w-full min-w-[760px] text-left text-[12.5px]">
              <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-3 py-2.5">{t("schedules.compare.col.item", "Work item")}</th>
                  <th className="px-3 py-2.5">{t("schedules.compare.col.status", "Status")}</th>
                  <th className="px-3 py-2.5">{t("schedules.compare.col.unit", "Unit")}</th>
                  <th className="px-3 py-2.5 text-right">{t("schedules.compare.col.before", "Before")}</th>
                  <th className="px-3 py-2.5 text-right">{t("schedules.compare.col.after", "After")}</th>
                  <th className="px-3 py-2.5 text-right">{t("schedules.compare.col.change", "Change")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {result.lines.slice(0, LINE_CAP).map((line) => (
                  <tr key={`${line.work_item_code}-${line.unit}-${line.status}`}>
                    <td className="px-3 py-2.5"><span className="font-mono font-semibold">{line.work_item_code}</span><div className="max-w-[320px] truncate text-[11.5px] text-[var(--color-text-muted)]">{line.description}</div></td>
                    <td className="px-3 py-2.5"><Badge tone={STATUS_TONE[line.status]}>{t(`schedules.compare.status.${line.status}`, STATUS_LABEL[line.status])}</Badge></td>
                    <td className="px-3 py-2.5">{line.unit}</td>
                    <td className="px-3 py-2.5 text-right">{formatRate(line.rate_a)}</td>
                    <td className="px-3 py-2.5 text-right">{formatRate(line.rate_b)}</td>
                    <td className={`px-3 py-2.5 text-right font-semibold ${deltaClass(line.pct)}`}>{line.pct ? `${Number(line.pct) > 0 ? "+" : ""}${formatPercent(line.pct, 2)}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
          {result.lines.length > LINE_CAP || result.truncated ? (
            <div className="text-[12px] text-[var(--color-text-muted)]">{t("schedules.compare.capped", "Showing the first {{n}} differences.", { n: LINE_CAP })}</div>
          ) : null}
        </div>
      )}
    </Panel>
  );
}

function EscalationApproval({ book, otherId, matchOn, otherFrom }: { book: RateBook; otherId: string; matchOn: CompareMatch; otherFrom: string | null }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const run = useEscalationsFromCompare(book.id);
  const [date, setDate] = useState(otherFrom ?? "");
  const [overall, setOverall] = useState(false);
  const [plan, setPlan] = useState<EscalationFromCompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toAdd = plan ? plan.proposals.filter((p) => p.status === "NEW").length : 0;

  function send(apply: boolean) {
    setError(null);
    run.mutate(
      { other_book_id: otherId, match_on: matchOn, include_overall: overall, effective_from: date || null, apply },
      {
        onSuccess: (result) => {
          setPlan(result);
          if (result.applied) showToast({ tone: "success", title: t("schedules.esc.addedToast", "{{n}} escalation(s) added", { n: result.created }) });
        },
        onError: (e) => setError(getApiErrorMessage(e, t("schedules.esc.error", "Couldn't work out the escalations."))),
      },
    );
  }

  return (
    <div className="rounded-[8px] border border-[var(--color-border)] p-4" data-testid="escalation-approval">
      <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">{t("schedules.esc.title", "Add these as escalations on this book")}</div>
      <p className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
        {t("schedules.esc.desc", "Each trade's factor is the median of new rate over old rate, worked out from the two books. Look at the list first; nothing is added until you approve it. A bill priced on or after the date then carries the factor.")}
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-[200px_1fr_auto] sm:items-end">
        <Field label={t("schedules.esc.date", "Applies from")}>
          <input type="date" className={inputClass} value={date} onChange={(e) => { setDate(e.target.value); setPlan(null); }} />
        </Field>
        <label className="flex items-center gap-2 text-[12.5px]">
          <input type="checkbox" checked={overall} onChange={(e) => { setOverall(e.target.checked); setPlan(null); }} />
          {t("schedules.esc.overall", "Also add one factor for the whole book (median of every matched rate)")}
        </label>
        <Button variant="secondary" size="sm" onClick={() => send(false)} disabled={run.isPending || (!date && !otherFrom)}>
          {t("schedules.esc.preview", "Show the escalations")}
        </Button>
      </div>
      {!otherFrom && !date ? <p className="mt-2 text-[12px] text-[var(--color-warning)]">{t("schedules.esc.noDate", "The other edition has no effective date. Give the date the new rates apply from.")}</p> : null}
      {error ? <p className="mt-2 text-[12px] text-[var(--color-danger)]">{error}</p> : null}
      {plan ? (
        <div className="mt-3">
          {plan.proposals.length === 0 ? (
            <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("schedules.esc.none", "No trade has 5 or more matched rates, so there is nothing to add.")}</p>
          ) : (
            <ul className="m-0 list-none space-y-1.5 pl-0 text-[12.5px]">
              {plan.proposals.map((p) => (
                <li key={p.trade_scope} className="flex flex-wrap items-center gap-2" data-testid={`esc-${p.trade_scope}`}>
                  <span className="min-w-[120px] font-semibold">{p.trade_scope === "ALL" ? t("schedules.esc.all", "Whole book") : p.trade_scope}</span>
                  <span className="font-mono">×{p.factor}</span>
                  <span className="text-[var(--color-text-muted)]">{t("schedules.esc.matched", "{{n}} matched rates", { n: p.matched })}</span>
                  <Badge tone={ESC_TONE[p.status]}>{t(`schedules.esc.status.${p.status}`, ESC_LABEL[p.status])}</Badge>
                </li>
              ))}
            </ul>
          )}
          {!plan.applied && toAdd > 0 ? (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button variant="primary" size="sm" onClick={() => send(true)} disabled={run.isPending}>
                {t("schedules.esc.approve", "Approve and add {{n}} escalation(s) from {{date}}", { n: toAdd, date: formatDate(plan.effective_from) })}
              </Button>
              <span className="text-[12px] text-[var(--color-text-muted)]">{t("schedules.esc.undo", "You can remove any of them later on the Escalations tab.")}</span>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function HistoryPanel({ book }: { book: RateBook }) {
  const { t } = useTranslation();
  const [code, setCode] = useState("");
  const [unit, setUnit] = useState("");
  const [submitted, setSubmitted] = useState({ code: "", unit: "" });
  const history = useRateHistory(book.id, submitted.code, submitted.unit);
  const points = history.data?.points ?? [];

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("schedules.history.eyebrow", "HISTORY")}
        title={t("schedules.history.title", "One rate across editions")}
        description={t("schedules.history.desc", "Follows a work item through every published version of this book, with the change from the one before.")}
      />
      <form className="grid gap-4 border-b border-[var(--color-border)] p-4 sm:grid-cols-[1fr_140px_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); setSubmitted({ code: code.trim().toUpperCase(), unit: unit.trim() }); }}>
        <Field label={t("schedules.history.code", "Work item code")}><input className={inputClass} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} /></Field>
        <Field label={t("schedules.history.unit", "Unit (optional)")}><input className={inputClass} value={unit} onChange={(e) => setUnit(e.target.value)} /></Field>
        <button type="submit" className="min-h-10 rounded-[var(--radius-sm)] border border-[var(--color-trace-gold)] bg-[var(--color-trace-gold)] px-4 text-[14px] font-semibold text-[var(--color-trace-navy)]">{t("schedules.history.show", "Show")}</button>
      </form>
      {!submitted.code ? null : history.isLoading ? <LoadingState label={t("schedules.history.loading", "Loading…")} /> : points.length === 0 ? (
        <EmptyState icon="trend" title={t("schedules.history.noneTitle", "No history for that code")} description={t("schedules.history.noneDesc", "It isn't in any published version of this book.")} />
      ) : (
        <TableShell>
          <table className="w-full min-w-[560px] text-left text-[12.5px]">
            <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
              <tr>
                <th className="px-4 py-2.5">{t("schedules.history.col.version", "Version")}</th>
                <th className="px-4 py-2.5">{t("schedules.history.col.edition", "Edition")}</th>
                <th className="px-4 py-2.5">{t("schedules.history.col.from", "Valid from")}</th>
                <th className="px-4 py-2.5">{t("schedules.history.col.unit", "Unit")}</th>
                <th className="px-4 py-2.5 text-right">{t("schedules.history.col.rate", "Rate")}</th>
                <th className="px-4 py-2.5 text-right">{t("schedules.history.col.change", "Change")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {points.map((p) => (
                <tr key={`${p.book_id}-${p.unit}`}>
                  <td className="px-4 py-2.5 font-mono">{p.book_code} v{p.version}</td>
                  <td className="px-4 py-2.5">{p.edition ?? "—"}</td>
                  <td className="px-4 py-2.5">{formatDate(p.effective_from)}</td>
                  <td className="px-4 py-2.5">{p.unit}</td>
                  <td className="px-4 py-2.5 text-right font-semibold">{formatRate(p.rate)}</td>
                  <td className={`px-4 py-2.5 text-right ${deltaClass(p.pct_from_previous)}`}>{p.pct_from_previous ? `${Number(p.pct_from_previous) > 0 ? "+" : ""}${formatPercent(p.pct_from_previous, 2)}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}

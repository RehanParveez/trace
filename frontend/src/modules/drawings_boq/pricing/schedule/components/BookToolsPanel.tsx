import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, EmptyState, ErrorState, Field, inputClass, LoadingState, Panel, PanelHeader, StatCard, TableShell } from "../../../../organizations/components/OrganizationUi";
import { useRateBooks } from "../../hooks";
import type { RateBook } from "../../types/pricing.types";
import { deltaClass, formatDate, formatPercent, rateBookTitle } from "../../utils/pricing.utils";
import { useCompareBooks, useRateHistory } from "../hooks/useSchedules";
import type { CompareLine, CompareMatch } from "../types/schedules.types";
import { formatRate } from "../utils/schedules.utils";

const LINE_CAP = 200;
const STATUS_TONE: Record<CompareLine["status"], "green" | "red" | "gold" | "slate"> = { ADDED: "green", REMOVED: "red", CHANGED: "gold", UNIT_MISMATCH: "slate" };
const STATUS_LABEL: Record<CompareLine["status"], string> = { ADDED: "Only in the other book", REMOVED: "Not in the other book", CHANGED: "Changed", UNIT_MISMATCH: "Units don't convert" };

export function BookToolsPanel({ book }: { book: RateBook }) {
  return (
    <div className="space-y-7">
      <ComparePanel book={book} />
      <HistoryPanel book={book} />
    </div>
  );
}

function ComparePanel({ book }: { book: RateBook }) {
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

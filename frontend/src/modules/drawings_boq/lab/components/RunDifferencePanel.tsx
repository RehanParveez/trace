import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import { useComparableRuns, useExportDifference, useRunDifference } from "../hooks/useDifference";
import type { DiffItem, RunDifference } from "../types/difference.types";
import { KIND_TONE, KIND_WORDS, STATUS_TONE, STATUS_WORDS, apiErrorText, defaultPair, deltaText, filterItems, headline, memberText, pctText, qtyText, sourceMoveText, type DiffFilter } from "../utils/difference";

const TONE: Record<string, string> = {
  ok: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  warn: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  bad: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
  muted: "bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]",
};

function ItemDetail({ item }: { item: DiffItem }) {
  const { t } = useTranslation();
  const move = sourceMoveText(item);
  return (
    <div className="space-y-1 bg-[var(--color-surface-muted)] px-3 py-2 text-[12px]" data-testid={`difference-detail-${item.code}`}>
      {move ? <p>{move}</p> : null}
      {item.storeys.length > 0 ? (
        <p>
          <span className="font-semibold">{t("drawings.difference.byStorey", "By storey")}: </span>
          {item.storeys.map((s) => `${s.level} ${qtyText(s.a)} to ${qtyText(s.b)} (${deltaText(s.delta)})`).join("; ")}
        </p>
      ) : null}
      {item.members.length > 0 ? (
        <div>
          <p className="font-semibold">
            {t("drawings.difference.byMember", "By member")}
            {item.members_changed > item.members.length ? ` (${item.members.length} of ${item.members_changed})` : ""}
          </p>
          <ul className="list-disc pl-5">
            {item.members.map((m, n) => <li key={`${m.label ?? m.key}-${n}`}>{memberText(m, item.unit)}</li>)}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function DifferenceTable({ result }: { result: RunDifference }) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<DiffFilter>("CHANGES");
  const [open, setOpen] = useState<string | null>(null);
  const items = filterItems(result.items, filter);
  return (
    <div className="space-y-2" data-testid="difference-table">
      <div className="flex flex-wrap items-center gap-3">
        <p className="font-semibold" data-testid="difference-headline">{headline(result.measures)}</p>
        <label className="flex items-center gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.difference.show", "Show")}</span>
          <select className="rounded-[6px] border border-[var(--color-border)] px-2 py-1" value={filter} onChange={(e) => setFilter(e.target.value as DiffFilter)} data-testid="difference-filter">
            <option value="CHANGES">{t("drawings.difference.onlyChanges", "Only what changed")}</option>
            <option value="ALL">{t("drawings.difference.everything", "Every work item")}</option>
          </select>
        </label>
      </div>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[var(--color-text-muted)]">
            <th className="font-medium">{t("drawings.difference.item", "Work item")}</th>
            <th className="font-medium">{t("drawings.difference.status", "Result")}</th>
            <th className="text-right font-medium">{t("drawings.difference.earlier", "Earlier")}</th>
            <th className="text-right font-medium">{t("drawings.difference.later", "Later")}</th>
            <th className="text-right font-medium">{t("drawings.difference.change", "Change")}</th>
            <th className="text-right font-medium">%</th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => {
            const key = `${i.code}|${i.unit}`;
            const expandable = i.storeys.length > 0 || i.members.length > 0 || i.source_moved;
            return (
              <Fragment key={key}>
                <tr data-testid={`difference-row-${i.code}`} className={expandable ? "cursor-pointer" : ""} onClick={() => expandable && setOpen(open === key ? null : key)}>
                  <td title={i.code}>{i.name || i.code}</td>
                  <td>
                    <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${TONE[STATUS_TONE[i.status]]}`}>{t(`drawings.difference.status.${i.status}`, STATUS_WORDS[i.status])}</span>
                  </td>
                  <td className="text-right">{qtyText(i.a, i.unit)}</td>
                  <td className="text-right">{qtyText(i.b, i.unit)}</td>
                  <td className="text-right">{deltaText(i.delta, i.unit)}</td>
                  <td className="text-right">{pctText(i.pct)}</td>
                </tr>
                {open === key ? <tr><td colSpan={6}><ItemDetail item={i} /></td></tr> : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
      {items.length === 0 ? <p className="text-[var(--color-text-muted)]">{t("drawings.difference.nothing", "Nothing to show with this filter.")}</p> : null}
    </div>
  );
}

function VariationTable({ result }: { result: RunDifference }) {
  const { t } = useTranslation();
  const v = result.variation;
  return (
    <div className="space-y-2" data-testid="variation-table">
      <p className="text-[var(--color-text-muted)]">{v.note}</p>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[var(--color-text-muted)]">
            <th className="font-medium">{t("drawings.difference.item", "Work item")}</th>
            <th className="font-medium">{t("drawings.difference.kind", "Kind")}</th>
            <th className="text-right font-medium">{t("drawings.difference.previous", "Previous")}</th>
            <th className="text-right font-medium">{t("drawings.difference.revised", "Revised")}</th>
            <th className="text-right font-medium">{t("drawings.difference.addition", "Addition")}</th>
            <th className="text-right font-medium">{t("drawings.difference.omission", "Omission")}</th>
          </tr>
        </thead>
        <tbody>
          {v.lines.map((l) => (
            <tr key={`${l.code}|${l.unit}`} data-testid={`variation-row-${l.code}`} title={l.basis}>
              <td>{l.name || l.code}</td>
              <td><span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${TONE[KIND_TONE[l.kind]]}`}>{t(`drawings.difference.kind.${l.kind}`, KIND_WORDS[l.kind])}</span></td>
              <td className="text-right">{qtyText(l.previous, l.unit)}</td>
              <td className="text-right">{qtyText(l.revised, l.unit)}</td>
              <td className="text-right">{l.addition ? qtyText(l.addition, l.unit) : "-"}</td>
              <td className="text-right">{l.omission ? qtyText(l.omission, l.unit) : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {v.lines.length === 0 ? <p className="text-[var(--color-text-muted)]">{t("drawings.difference.noVariation", "No work item changed by enough to be a variation.")}</p> : null}
    </div>
  );
}

export function RunDifferencePanel({ projectId, runId }: { projectId: string; runId: string }) {
  const { t } = useTranslation();
  const runs = useComparableRuns(projectId);
  const list = runs.data ?? [];
  const pair = defaultPair(list, runId);
  const [from, setFrom] = useState<string | undefined>();
  const [to, setTo] = useState<string | undefined>();
  const [view, setView] = useState<"difference" | "variation">("difference");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setFrom(undefined);
    setTo(undefined);
  }, [runId]);
  const earlier = from ?? pair.from;
  const later = to ?? pair.to;
  const diff = useRunDifference(earlier, later);
  const exporter = useExportDifference();
  const download = (kind: "difference" | "variation") => {
    if (!diff.data) return;
    setError(null);
    exporter.mutate({ result: diff.data, kind }, {
      onSuccess: (blob) => triggerBlobDownload(blob, kind === "variation" ? "variation-statement.xlsx" : "run-difference.xlsx"),
      onError: (e) => setError(apiErrorText(e, t("drawings.difference.exportFailed", "The file could not be made."))),
    });
  };
  const select = (label: string, value: string | undefined, set: (v: string) => void, testid: string) => (
    <label className="flex flex-col gap-1">
      <span className="text-[var(--color-text-muted)]">{label}</span>
      <select className="max-w-[28rem] rounded-[6px] border border-[var(--color-border)] px-2 py-1" value={value ?? ""} onChange={(e) => set(e.target.value)} data-testid={testid}>
        {value === undefined ? <option value="">{t("drawings.difference.choose", "Choose a run")}</option> : null}
        {list.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
      </select>
    </label>
  );
  return (
    <div className="space-y-3 px-4 py-3 text-[12.5px]" data-testid="run-difference-panel">
      <p className="text-[12px] text-[var(--color-text-muted)]">
        {t("drawings.difference.intro", "Compare two finished runs of this project, for example two revisions of the drawings. The change is shown work item by work item, down to the storey and the member, and as a variation statement of quantities.")}
      </p>
      {list.length < 2 && !runs.isLoading ? <p className="text-[var(--color-text-muted)]" data-testid="difference-need-two">{t("drawings.difference.needTwo", "This project needs two finished runs to compare.")}</p> : (
        <div className="flex flex-wrap items-end gap-3">
          {select(t("drawings.difference.from", "Earlier run"), earlier, setFrom, "difference-from")}
          {select(t("drawings.difference.to", "Later run"), later, setTo, "difference-to")}
        </div>
      )}
      {earlier && later && earlier === later ? <p className="text-[var(--color-warning)]">{t("drawings.difference.same", "Choose two different runs.")}</p> : null}
      {diff.isError ? <p role="alert" className="text-[var(--color-danger)]">{apiErrorText(diff.error, t("drawings.difference.failed", "The runs could not be compared."))}</p> : null}
      {error ? <p role="alert" className="text-[var(--color-danger)]">{error}</p> : null}
      {diff.isLoading ? <p className="text-[var(--color-text-muted)]">{t("drawings.difference.loading", "Comparing...")}</p> : null}
      {diff.data ? (
        <>
          {diff.data.causes.length > 0 ? (
            <div data-testid="difference-causes">
              <p className="font-semibold">{t("drawings.difference.why", "Why the runs differ")}</p>
              <ul className="list-disc pl-5">
                {diff.data.causes.map((c, n) => <li key={`${c.kind}-${n}`}>{c.text}</li>)}
              </ul>
            </div>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            {(["difference", "variation"] as const).map((k) => (
              <button key={k} type="button" onClick={() => setView(k)} data-testid={`difference-tab-${k}`}
                className={`rounded-[6px] px-3 py-1 text-[12px] font-semibold ${view === k ? "bg-[var(--color-trace-gold-dark)] text-white" : "border border-[var(--color-border)]"}`}>
                {k === "difference" ? t("drawings.difference.tabDifference", "Difference") : t("drawings.difference.tabVariation", "Variation statement")}
              </button>
            ))}
            <button type="button" className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] underline" disabled={exporter.isPending} onClick={() => download(view)} data-testid="difference-export">
              {t("drawings.difference.export", "Download as Excel")}
            </button>
          </div>
          {view === "difference" ? <DifferenceTable result={diff.data} /> : <VariationTable result={diff.data} />}
        </>
      ) : null}
    </div>
  );
}

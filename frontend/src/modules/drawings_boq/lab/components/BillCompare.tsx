import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { BillClass, BillClasses, BillCompareLine, BillCompareResult, BillFilter } from "../types/billCompare.types";
import { BILL_CLASSES, BILL_CLASS_TEXT, BILL_STATUS_TEXT, BILL_STATUS_TONE, applyClasses, errorText, filterLines, parseTolerance, qtyText } from "../utils/billCompare";

const TONE: Record<string, string> = {
  ok: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  warn: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  bad: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
  muted: "bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]",
};

interface Props {
  result: BillCompareResult | undefined;
  classes: BillClasses;
  busy: boolean;
  error: string | null;
  tolerancePct: number;
  onToleranceChange: (pct: number) => void;
  onUpload: (file: File) => void;
  onClassChange: (key: string, cls: BillClass | null, note: string) => void;
  onExport: () => void;
}

function Measure({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[6px] border border-[var(--color-border)] px-3 py-2">
      <div className="text-[10.5px] uppercase text-[var(--color-text-muted)]">{label}</div>
      <div className="text-[15px] font-semibold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

function LineRow({ line, onClassChange }: { line: BillCompareLine; onClassChange: Props["onClassChange"] }) {
  const { t } = useTranslation();
  const tone = TONE[BILL_STATUS_TONE[line.status]];
  const needsClass = line.status === "DIFF" || line.status === "MISSING" || line.status === "EXTRA";
  return (
    <li className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid={`bill-line-${line.key}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="min-w-[10rem] font-semibold text-[var(--color-text-primary)]">{line.label}</span>
        <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${tone}`}>{t(`drawings.bill.status.${line.status}`, BILL_STATUS_TEXT[line.status])}</span>
        <span className="text-[var(--color-text-muted)]">
          {t("drawings.bill.qs", "QS")} {qtyText(line.qs, line.unit)}
        </span>
        <span className="text-[var(--color-text-muted)]">
          {t("drawings.bill.software", "Software")} {qtyText(line.software, line.unit)}
        </span>
        <span className="font-semibold text-[var(--color-text-primary)]">{errorText(line.error_pct)}</span>
      </div>
      {needsClass ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <select
            className="rounded-[6px] border border-[var(--color-border)] px-2 py-1"
            value={line.class ?? ""}
            aria-label={t("drawings.bill.classFor", "Why it differs: {{item}}", { item: line.label })}
            onChange={(e) => onClassChange(line.key, (e.target.value || null) as BillClass | null, line.note)}
          >
            <option value="">
              {line.suggested_class
                ? t("drawings.bill.chooseSuggested", "Choose a reason (suggested: {{c}})", { c: t(`drawings.bill.class.${line.suggested_class}`, BILL_CLASS_TEXT[line.suggested_class]) })
                : t("drawings.bill.choose", "Choose a reason")}
            </option>
            {BILL_CLASSES.map((c) => (
              <option key={c} value={c}>
                {t(`drawings.bill.class.${c}`, BILL_CLASS_TEXT[c])}
              </option>
            ))}
          </select>
          <input
            className="min-w-[14rem] flex-1 rounded-[6px] border border-[var(--color-border)] px-2 py-1"
            value={line.note}
            disabled={!line.class}
            placeholder={t("drawings.bill.note", "Note")}
            onChange={(e) => line.class && onClassChange(line.key, line.class, e.target.value)}
          />
        </div>
      ) : null}
      {line.floors && line.floors.length > 0 ? (
        <table className="mt-2 w-full max-w-[28rem] text-[11.5px]" data-testid={`bill-floors-${line.key}`}>
          <thead>
            <tr className="text-left text-[var(--color-text-muted)]">
              <th className="font-medium">{t("drawings.bill.floor", "Floor")}</th>
              <th className="text-right font-medium">{t("drawings.bill.qs", "QS")}</th>
              <th className="text-right font-medium">{t("drawings.bill.software", "Software")}</th>
            </tr>
          </thead>
          <tbody>
            {line.floors.map((f) => (
              <tr key={f.floor}>
                <td>{f.label}</td>
                <td className="text-right">{qtyText(f.qs, line.unit)}</td>
                <td className="text-right">{qtyText(f.software, line.unit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {line.assumed_rows ? (
        <p className="mt-1 text-[var(--color-warning)]">{t("drawings.bill.assumedRows", "{{n}} of the software's rows rest on an assumed value.", { n: line.assumed_rows })}</p>
      ) : null}
      <details className="mt-1 text-[var(--color-text-muted)]">
        <summary className="cursor-pointer">{t("drawings.bill.detail", "Where the figures come from")}</summary>
        <ul className="mt-1 list-none space-y-0.5 pl-0">
          {line.bill_rows.map((b) => (
            <li key={b.row}>
              {t("drawings.bill.billRow", "Bill row {{row}}: {{item}} ({{section}}) {{qty}}", { row: b.row, item: b.item, section: b.section || "-", qty: qtyText(b.quantity, b.unit) })}
            </li>
          ))}
          <li>{t("drawings.bill.softwareRows", "{{n}} software rows", { n: line.software_rows })}</li>
          {line.software_tags.map((s) => (
            <li key={s.tag}>
              {s.tag}: {qtyText(s.quantity, "")}
            </li>
          ))}
        </ul>
      </details>
    </li>
  );
}

export function BillCompare({ result, classes, busy, error, tolerancePct, onToleranceChange, onUpload, onClassChange, onExport }: Props) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<BillFilter>("OPEN");
  const view = result ? applyClasses(result, classes) : undefined;
  const lines = view ? filterLines(view.lines, filter) : [];
  const m = view?.measures;
  return (
    <section className="space-y-3 text-[12.5px]" data-testid="bill-compare">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.bill.file", "QS bill (Excel)")}</span>
          <input
            type="file"
            accept=".xlsx"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
              e.target.value = "";
            }}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.bill.tolerance", "Tolerance %")}</span>
          <input
            className="w-20 rounded-[6px] border border-[var(--color-border)] px-2 py-1"
            inputMode="decimal"
            defaultValue={String(tolerancePct)}
            onBlur={(e) => onToleranceChange(parseTolerance(e.target.value, tolerancePct))}
          />
        </label>
        <button
          type="button"
          className="rounded-[6px] border border-[var(--color-border)] px-3 py-1 disabled:opacity-50"
          disabled={!view}
          onClick={onExport}
        >
          {t("drawings.bill.export", "Download comparison")}
        </button>
        {busy ? <span className="text-[var(--color-text-muted)]">{t("drawings.bill.busy", "Comparing...")}</span> : null}
      </div>
      {error ? (
        <p className="rounded-[6px] bg-[var(--color-danger-bg)] px-3 py-2 text-[var(--color-danger)]" role="alert">
          {error}
        </p>
      ) : null}
      {!view && !busy && !error ? <p className="text-[var(--color-text-muted)]">{t("drawings.bill.empty", "Upload the QS bill to compare it with this run, item by item.")}</p> : null}
      {view && m ? (
        <>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
            <Measure label={t("drawings.bill.m.within", "Within tolerance")} value={`${m.within_tolerance} / ${m.compared}`} />
            <Measure label={t("drawings.bill.m.median", "Median line error")} value={m.line_error_median_pct === null ? "—" : `${m.line_error_median_pct}%`} />
            <Measure label={t("drawings.bill.m.coverage", "Coverage")} value={m.coverage_pct === null ? "—" : `${m.coverage_pct}%`} />
            <Measure label={t("drawings.bill.m.extra", "Extra lines")} value={String(m.extra_lines)} />
            <Measure label={t("drawings.bill.m.open", "Differences without a reason")} value={String(m.unclassified_differences)} />
          </div>
          <div className="flex gap-2" role="tablist">
            {(["OPEN", "MATCH", "ALL"] as BillFilter[]).map((f) => (
              <button
                key={f}
                type="button"
                role="tab"
                aria-selected={filter === f}
                className={`rounded-full px-3 py-1 ${filter === f ? "bg-[var(--color-primary)] text-white" : "border border-[var(--color-border)]"}`}
                onClick={() => setFilter(f)}
              >
                {t(`drawings.bill.filter.${f}`, f === "OPEN" ? "Differences" : f === "MATCH" ? "Matches" : "All")}
              </button>
            ))}
          </div>
          <ul className="list-none space-y-2 pl-0">
            {lines.map((l) => (
              <LineRow key={l.key} line={l} onClassChange={onClassChange} />
            ))}
          </ul>
          {view.unmapped.length > 0 ? (
            <div>
              <h4 className="font-semibold text-[var(--color-text-primary)]">{t("drawings.bill.unmapped", "Bill items not recognised")}</h4>
              <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
                {view.unmapped.map((u) => (
                  <li key={u.row}>
                    {u.item} · {qtyText(u.quantity, u.unit)}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {view.unclassified_software.length > 0 ? (
            <div>
              <h4 className="font-semibold text-[var(--color-text-primary)]">{t("drawings.bill.softwareOnly", "Software rows not grouped under any bill item")}</h4>
              <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
                {view.unclassified_software.map((u) => (
                  <li key={u.name}>
                    {u.name} · {u.rows} · {qtyText(u.quantity, u.unit)}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

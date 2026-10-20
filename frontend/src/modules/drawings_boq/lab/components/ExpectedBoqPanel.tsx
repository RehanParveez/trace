import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import { useCheckExpectedBoq, useDownloadExpectedBoq, useExpectedBoq, useExpectedBoqs, useRemoveExpectedBoq, useSaveExpectedBoq, useSetExpectedTolerances } from "../hooks/useExpectedBoq";
import type { ExpectedBoqDetail, ExpectedCheckResult } from "../types/expectedBoq.types";
import { FROM_WORDS, STATUS_TONE, STATUS_WORDS, apiErrorText, errorText, gateWords, hasChanges, marginText, qtyText, sortLines, tolerancesBody, unmappedNote } from "../utils/expectedBoq";

const TONE: Record<string, string> = {
  ok: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  warn: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  bad: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
  muted: "bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]",
};

function TolerancesTable({ detail, projectId }: { detail: ExpectedBoqDetail; projectId: string }) {
  const { t } = useTranslation();
  const save = useSetExpectedTolerances(projectId, detail.id);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [allText, setAllText] = useState(detail.default_tolerance_pct === null ? "" : String(detail.default_tolerance_pct));
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setEdits({});
    setAllText(detail.default_tolerance_pct === null ? "" : String(detail.default_tolerance_pct));
  }, [detail.id, detail.updated_at, detail.default_tolerance_pct]);
  const { wrong } = tolerancesBody(detail, edits, allText);
  const changed = hasChanges(detail, edits, allText);
  const apply = () => {
    const { body, wrong: bad } = tolerancesBody(detail, edits, allText);
    if (bad.length > 0) return;
    setError(null);
    save.mutate(body, { onError: (e) => setError(apiErrorText(e, t("drawings.expected.saveFailed", "The tolerances could not be saved."))) });
  };
  return (
    <div className="space-y-2" data-testid="expected-tolerances">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.expected.allTolerance", "One tolerance % for every item without its own")}</span>
          <input className={`w-24 rounded-[6px] border px-2 py-1 ${wrong.includes("all") ? "border-[var(--color-danger)]" : "border-[var(--color-border)]"}`} inputMode="decimal" value={allText}
            placeholder={t("drawings.expected.startingValues", "starting values")} aria-label={t("drawings.expected.allTolerance", "One tolerance % for every item without its own")} onChange={(e) => setAllText(e.target.value)} />
        </label>
        <button type="button" disabled={!changed || wrong.length > 0 || save.isPending} onClick={apply} data-testid="expected-save-tolerances"
          className="rounded-[6px] bg-[var(--color-trace-gold-dark)] px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50">
          {t("drawings.expected.saveTolerances", "Save tolerances")}
        </button>
      </div>
      {wrong.length > 0 ? <p className="text-[var(--color-danger)]">{t("drawings.expected.wrongTolerance", "A tolerance is a number from 0 to 100. Leave it empty to use the value for all items.")}</p> : null}
      {error ? <p role="alert" className="text-[var(--color-danger)]">{error}</p> : null}
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[var(--color-text-muted)]">
            <th className="font-medium">{t("drawings.expected.item", "Item")}</th>
            <th className="text-right font-medium">{t("drawings.expected.expected", "Expected")}</th>
            <th className="text-right font-medium">{t("drawings.expected.rows", "Rows")}</th>
            <th className="text-right font-medium">{t("drawings.expected.tolerance", "Tolerance %")}</th>
            <th className="font-medium">{t("drawings.expected.toleranceFrom", "Where it comes from")}</th>
          </tr>
        </thead>
        <tbody>
          {detail.families.map((f) => (
            <tr key={f.key} data-testid={`expected-family-${f.key}`}>
              <td>{f.label}</td>
              <td className="text-right">{qtyText(f.quantity, f.unit)}</td>
              <td className="text-right">{f.rows}</td>
              <td className="text-right">
                <input className={`w-16 rounded-[6px] border px-2 py-0.5 text-right ${wrong.includes(f.key) ? "border-[var(--color-danger)]" : "border-[var(--color-border)]"}`} inputMode="decimal"
                  aria-label={t("drawings.expected.toleranceFor", "Tolerance % for {{item}}", { item: f.label })}
                  value={f.key in edits ? edits[f.key] : detail.tolerances[f.key] === undefined ? "" : String(detail.tolerances[f.key])}
                  placeholder={String(f.tolerance_from === "family" ? f.default_pct : f.tolerance_pct)} onChange={(e) => setEdits({ ...edits, [f.key]: e.target.value })} />
              </td>
              <td className="text-[var(--color-text-muted)]">{t(`drawings.expected.from.${f.tolerance_from}`, FROM_WORDS[f.tolerance_from])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CheckResult({ result }: { result: ExpectedCheckResult }) {
  const { t } = useTranslation();
  const gate = gateWords(result.gate);
  return (
    <div className="space-y-2" data-testid="expected-result">
      <p className={`rounded-[6px] px-3 py-2 font-semibold ${TONE[gate.tone]}`} data-testid="expected-gate">
        {result.gate.passed && result.gate.families > 0 ? t("drawings.expected.passed", "Passed. ") : t("drawings.expected.failed", "Not passed. ")}
        {gate.text}
      </p>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[var(--color-text-muted)]">
            <th className="font-medium">{t("drawings.expected.item", "Item")}</th>
            <th className="font-medium">{t("drawings.expected.status", "Result")}</th>
            <th className="text-right font-medium">{t("drawings.expected.qs", "Expected")}</th>
            <th className="text-right font-medium">{t("drawings.expected.software", "This run")}</th>
            <th className="text-right font-medium">{t("drawings.expected.error", "Difference")}</th>
            <th className="text-right font-medium">{t("drawings.expected.limit", "Tolerance")}</th>
          </tr>
        </thead>
        <tbody>
          {sortLines(result.lines).map((l) => (
            <tr key={l.key} data-testid={`expected-line-${l.key}`}>
              <td>{l.label}</td>
              <td>
                <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${TONE[STATUS_TONE[l.status]]}`}>{t(`drawings.expected.status.${l.status}`, STATUS_WORDS[l.status])}</span>
              </td>
              <td className="text-right">{qtyText(l.qs, l.unit)}</td>
              <td className="text-right">{qtyText(l.software, l.unit)}</td>
              <td className="text-right" title={marginText(l)}>{errorText(l.error_pct)}</td>
              <td className="text-right text-[var(--color-text-muted)]">{l.status === "OUT_OF_SCOPE" ? "-" : `${l.tolerance_pct}%`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ExpectedBoqPanel({ projectId, runId }: { projectId: string; runId: string }) {
  const { t } = useTranslation();
  const list = useExpectedBoqs(projectId);
  const [selected, setSelected] = useState<string | undefined>();
  const [name, setName] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExpectedCheckResult | undefined>();
  const items = list.data ?? [];
  const current = selected && items.some((i) => i.id === selected) ? selected : items[0]?.id;
  const detail = useExpectedBoq(projectId, current);
  const save = useSaveExpectedBoq(projectId);
  const remove = useRemoveExpectedBoq(projectId);
  const check = useCheckExpectedBoq(runId);
  const download = useDownloadExpectedBoq(projectId);
  const fail = (fallback: string) => (e: unknown) => setError(apiErrorText(e, fallback));

  const upload = (file: File) => {
    setError(null);
    setNote(null);
    save.mutate({ file, name }, {
      onSuccess: (d) => {
        setSelected(d.id);
        setResult(undefined);
        setName("");
        setNote(unmappedNote(d.unmapped?.length ?? 0) || null);
      },
      onError: fail(t("drawings.expected.uploadFailed", "The file could not be read as an expected BOQ.")),
    });
  };
  const run = () => {
    if (!current) return;
    setError(null);
    check.mutate(current, { onSuccess: setResult, onError: fail(t("drawings.expected.checkFailed", "The run could not be checked.")) });
  };

  return (
    <div className="space-y-3 px-4 py-3 text-[12.5px]" data-testid="expected-boq-panel">
      <p className="text-[12px] text-[var(--color-text-muted)]">
        {t("drawings.expected.intro", "Keep the figures your QS holds for this project here once. Any run can then be checked against them item by item, each item with its own tolerance, without uploading the workbook again.")}
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.expected.file", "QS bill (Excel) or a saved expected BOQ (.json)")}</span>
          <input type="file" accept=".xlsx,.json" disabled={save.isPending} data-testid="expected-upload"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.expected.name", "Name (optional)")}</span>
          <input className="w-56 rounded-[6px] border border-[var(--color-border)] px-2 py-1" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        {items.length > 0 ? (
          <label className="flex flex-col gap-1">
            <span className="text-[var(--color-text-muted)]">{t("drawings.expected.kept", "Kept for this project")}</span>
            <select className="rounded-[6px] border border-[var(--color-border)] px-2 py-1" value={current ?? ""} onChange={(e) => { setSelected(e.target.value); setResult(undefined); }} data-testid="expected-select">
              {items.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
            </select>
          </label>
        ) : null}
      </div>
      {note ? <p className="text-[var(--color-warning)]">{note}</p> : null}
      {error ? <p role="alert" className="text-[var(--color-danger)]" data-testid="expected-error">{error}</p> : null}
      {items.length === 0 && !list.isLoading ? <p className="text-[var(--color-text-muted)]">{t("drawings.expected.none", "Nothing is kept for this project yet.")}</p> : null}
      {detail.data ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" disabled={check.isPending} onClick={run} data-testid="expected-check"
              className="rounded-[6px] bg-[var(--color-trace-gold-dark)] px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50">
              {check.isPending ? t("drawings.expected.checking", "Checking...") : t("drawings.expected.check", "Check this run against it")}
            </button>
            <button type="button" className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] underline" disabled={download.isPending}
              onClick={() => download.mutate(detail.data.id, { onSuccess: (blob) => triggerBlobDownload(blob, "expected-boq.json") })}>
              {t("drawings.expected.download", "Download as a file")}
            </button>
            <button type="button" className="text-[12px] font-semibold text-[var(--color-danger)] underline" disabled={remove.isPending}
              onClick={() => remove.mutate(detail.data.id, { onSuccess: () => { setSelected(undefined); setResult(undefined); } })}>
              {t("drawings.expected.remove", "Remove")}
            </button>
            <span className="text-[var(--color-text-muted)]">{detail.data.source ?? ""}</span>
          </div>
          {result && result.expected_id === detail.data.id ? <CheckResult result={result} /> : null}
          <TolerancesTable detail={detail.data} projectId={projectId} />
        </>
      ) : null}
    </div>
  );
}

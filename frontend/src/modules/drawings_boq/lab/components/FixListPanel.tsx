import { useState } from "react";
import { useTranslation } from "react-i18next";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import { useExportFixList, useFixList } from "../hooks/useDifference";
import type { FixAudience } from "../types/difference.types";
import { AUDIENCES, AUDIENCE_WORDS, PRIORITY_WORDS, apiErrorText, emptyFixWords, entriesFor, fixText, whereText } from "../utils/difference";

export function FixListPanel({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const fix = useFixList(runId);
  const exporter = useExportFixList();
  const [audience, setAudience] = useState<FixAudience>("ARCHITECT");
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rows = entriesFor(fix.data, audience);
  const copy = async () => {
    setError(null);
    try {
      await navigator.clipboard.writeText(fixText(fix.data, audience));
      setNote(t("drawings.fixList.copied", "Copied. Paste it into an email."));
    } catch {
      setError(t("drawings.fixList.copyFailed", "The list could not be copied."));
    }
  };
  return (
    <div className="space-y-3 px-4 py-3 text-[12.5px]" data-testid="fix-list-panel">
      <p className="text-[12px] text-[var(--color-text-muted)]">
        {t("drawings.fixList.intro", "Every open issue of this run, as a question to the person who can answer it. Send the architect's list as it is; the QS and Trace lists are for you.")}
      </p>
      {fix.isError ? <p role="alert" className="text-[var(--color-danger)]">{apiErrorText(fix.error, t("drawings.fixList.failed", "The list could not be made."))}</p> : null}
      {fix.isLoading ? <p className="text-[var(--color-text-muted)]">{t("drawings.fixList.loading", "Loading...")}</p> : null}
      {fix.data ? (
        <>
          <p className="text-[var(--color-text-muted)]" data-testid="fix-list-empty">{emptyFixWords(fix.data)}</p>
          <div className="flex flex-wrap items-center gap-2">
            {AUDIENCES.map((a) => (
              <button key={a} type="button" onClick={() => { setAudience(a); setNote(null); }} data-testid={`fix-tab-${a}`}
                className={`rounded-[6px] px-3 py-1 text-[12px] font-semibold ${audience === a ? "bg-[var(--color-trace-gold-dark)] text-white" : "border border-[var(--color-border)]"}`}>
                {t(`drawings.fixList.tab.${a}`, AUDIENCE_WORDS[a].tab)} ({fix.data.counts[a] ?? 0})
              </button>
            ))}
          </div>
          <p className="text-[12px] text-[var(--color-text-muted)]">{t(`drawings.fixList.intro.${audience}`, AUDIENCE_WORDS[audience].intro)}</p>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" disabled={rows.length === 0} onClick={copy} data-testid="fix-copy" className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] underline disabled:opacity-50">
              {t("drawings.fixList.copy", "Copy as text")}
            </button>
            <button type="button" disabled={exporter.isPending || fix.data.total === 0} data-testid="fix-export" className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] underline disabled:opacity-50"
              onClick={() => exporter.mutate(fix.data, { onSuccess: (blob) => triggerBlobDownload(blob, "fix-list.xlsx"), onError: (e) => setError(apiErrorText(e, t("drawings.fixList.exportFailed", "The file could not be made."))) })}>
              {t("drawings.fixList.export", "Download as Excel")}
            </button>
            {note ? <span className="text-[var(--color-success)]">{note}</span> : null}
          </div>
          {error ? <p role="alert" className="text-[var(--color-danger)]">{error}</p> : null}
          <ol className="space-y-2" data-testid="fix-list">
            {rows.map((e, n) => (
              <li key={`${e.code}-${n}`} className="rounded-[6px] border border-[var(--color-border)] px-3 py-2" data-testid={`fix-entry-${e.code}`}>
                <p className="font-semibold">{n + 1}. {e.topic} <span className="font-normal text-[var(--color-text-muted)]">({PRIORITY_WORDS[e.severity] ?? e.severity})</span></p>
                <p>{e.ask}</p>
                {whereText(e) ? <p className="text-[var(--color-text-muted)]">{whereText(e)}</p> : null}
              </li>
            ))}
          </ol>
          {rows.length === 0 && fix.data.total > 0 ? <p className="text-[var(--color-text-muted)]">{t("drawings.fixList.none", "Nothing for this person.")}</p> : null}
        </>
      ) : null}
    </div>
  );
}

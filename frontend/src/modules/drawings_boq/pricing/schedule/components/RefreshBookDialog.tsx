import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, Field, inputClass, Modal, TableShell, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { FormError } from "../../components/FormError";
import { useRateBooks } from "../../hooks";
import type { RateBook } from "../../types/pricing.types";
import { deltaClass, formatPercent, rateBookTitle } from "../../utils/pricing.utils";
import { useRefreshBook } from "../hooks/useSchedules";
import type { RefreshResult } from "../types/schedules.types";
import { formatRate } from "../utils/schedules.utils";

const SHOWN = 100;

export function RefreshBookDialog({ book, onClose }: { book: RateBook; onClose: () => void }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const refresh = useRefreshBook(book.id);
  const books = useRateBooks({});
  const sources = books.books.filter((b) => b.id !== book.id && b.status !== "DRAFT");

  const [sourceId, setSourceId] = useState("");
  const [matchOn, setMatchOn] = useState<"csr_ref" | "code">("csr_ref");
  const [recompute, setRecompute] = useState(true);
  const [preview, setPreview] = useState<RefreshResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function run(apply: boolean) {
    if (!sourceId) return;
    setError(null);
    refresh.mutate(
      { source_book_id: sourceId, match_on: matchOn, recompute_analyses: recompute, apply },
      {
        onSuccess: (result) => {
          if (apply) {
            showToast({ tone: "success", title: t("schedules.refresh.done", "Rates refreshed"), description: t("schedules.refresh.doneDesc", "{{n}} rates updated.", { n: result.updated }) });
            onClose();
          } else {
            setPreview(result);
          }
        },
        onError: (e) => setError(getApiErrorMessage(e, t("schedules.refresh.error", "It could not be refreshed. Nothing was changed."))),
      },
    );
  }

  return (
    <Modal
      title={t("schedules.refresh.title", "Refresh rates from another edition")}
      description={t(
        "schedules.refresh.desc",
        "Takes the rates of a published book (for example the new quarter's schedule) into this draft. Rows are matched by reference number or work item code; rates built from an analysis are recomputed from their ingredients instead of copied. Nothing changes until you press Apply.",
      )}
      onClose={onClose}
      wide
    >
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-[1fr_220px]">
          <Field label={t("schedules.refresh.source", "Take rates from")}>
            <select className={inputClass} value={sourceId} onChange={(e) => { setSourceId(e.target.value); setPreview(null); }}>
              <option value="">{t("schedules.compare.choose", "Choose a published book…")}</option>
              {sources.map((b) => <option key={b.id} value={b.id}>{rateBookTitle(b)} — {b.name}</option>)}
            </select>
          </Field>
          <Field label={t("schedules.compare.match", "Match rows by")}>
            <select className={inputClass} value={matchOn} onChange={(e) => { setMatchOn(e.target.value as "csr_ref" | "code"); setPreview(null); }}>
              <option value="csr_ref">{t("schedules.compare.byRef", "Reference number")}</option>
              <option value="code">{t("schedules.compare.byCode", "Work item code")}</option>
            </select>
          </Field>
        </div>
        <label className="flex items-center gap-2 text-[13px]">
          <input type="checkbox" checked={recompute} onChange={(e) => { setRecompute(e.target.checked); setPreview(null); }} />
          {t("schedules.refresh.recompute", "Recompute rate analyses afterwards")}
        </label>

        {preview ? (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Badge tone="gold">{t("schedules.refresh.updated", "{{n}} will change", { n: preview.updated })}</Badge>
              <Badge tone="slate">{t("schedules.refresh.unchanged", "{{n}} already the same", { n: preview.unchanged })}</Badge>
              <Badge tone={preview.unmatched > 0 ? "blue" : "slate"}>{t("schedules.refresh.unmatched", "{{n}} not found in the source", { n: preview.unmatched })}</Badge>
              <Badge tone="slate">{t("schedules.refresh.skipped", "{{n}} skipped", { n: preview.skipped })}</Badge>
            </div>
            {preview.changes.length > 0 ? (
              <TableShell>
                <table className="w-full text-left text-[12.5px]">
                  <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                    <tr><th className="px-3 py-2">{t("schedules.refresh.col.item", "Work item")}</th><th className="px-3 py-2">{t("schedules.compare.col.unit", "Unit")}</th><th className="px-3 py-2 text-right">{t("schedules.compare.col.before", "Before")}</th><th className="px-3 py-2 text-right">{t("schedules.compare.col.after", "After")}</th><th className="px-3 py-2 text-right">{t("schedules.compare.col.change", "Change")}</th></tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]">
                    {preview.changes.slice(0, SHOWN).map((c) => (
                      <tr key={c.id}>
                        <td className="px-3 py-2 font-mono">{c.work_item_code}</td><td className="px-3 py-2">{c.unit}</td>
                        <td className="px-3 py-2 text-right">{formatRate(c.old)}</td><td className="px-3 py-2 text-right font-semibold">{formatRate(c.new)}</td>
                        <td className={`px-3 py-2 text-right ${deltaClass(c.pct)}`}>{c.pct ? formatPercent(c.pct, 2) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableShell>
            ) : null}
            {preview.changes.length > SHOWN ? <div className="text-[12px] text-[var(--color-text-muted)]">{t("schedules.refresh.capped", "Showing the first {{n}} of {{total}}.", { n: SHOWN, total: preview.changes.length })}</div> : null}
            {preview.analyses.changed.length > 0 ? (
              <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[12.5px]">
                <div className="mb-1 font-semibold">{t("schedules.refresh.analyses", "Rates built from an analysis that will move")}</div>
                {preview.analyses.changed.slice(0, 20).map((a) => <div key={a.code}><span className="font-mono">{a.code}</span> {formatRate(a.old)} → <strong>{formatRate(a.new)}</strong> / {a.unit}</div>)}
              </div>
            ) : null}
            {preview.analyses.failed.length > 0 ? (
              <div className="text-[12.5px] text-[var(--color-danger)]">
                {t("schedules.refresh.analysisFailed", "{{n}} analyses could not be recomputed and keep their old rate:", { n: preview.analyses.failed.length })} {preview.analyses.failed.map((f) => f.code).join(", ")}
              </div>
            ) : null}
          </div>
        ) : null}

        <FormError message={error} />
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="secondary" disabled={!sourceId || refresh.isPending} onClick={() => run(false)}>{t("schedules.refresh.preview", "Preview changes")}</Button>
          <Button variant="primary" disabled={!preview || preview.updated + preview.analyses.changed.length === 0 || refresh.isPending} onClick={() => run(true)}>{t("schedules.refresh.apply", "Apply")}</Button>
        </div>
      </div>
    </Modal>
  );
}

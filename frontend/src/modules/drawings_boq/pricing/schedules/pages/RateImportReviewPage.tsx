import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, Button, ErrorState, inputClass, LoadingState, PageHeader, Panel, PanelHeader, StatCard, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage, usePermissionKeys } from "../../../../identity";
import { ConfirmDialog } from "../../../components/ConfirmDialog";
import { PRICING_PERMISSIONS } from "../../permissions";
import { rateBookPath } from "../../utils/pricing.utils";
import { ImportPublishDialog } from "../components/ImportPublishDialog";
import { ImportReportPanel } from "../components/ImportReportPanel";
import { ImportRowDialog } from "../components/ImportRowDialog";
import { ImportRowTable } from "../components/ImportRowTable";
import { ReparseDialog } from "../components/ReparseDialog";
import { useBulkRows, useDeleteImport, useImportChapters, useImportRows, useRateImport, useRefreshSuggestions, useUpdateImportRow } from "../hooks/useSchedules";
import type { BulkPayload, ImportRow, RowFilter } from "../types/schedules.types";
import { IMPORT_STATUS_LABEL, RATE_IMPORTS_PATH, formatBytes, importStatusTone } from "../utils/schedules.utils";

const FILTERS: Array<{ value: RowFilter; label: string }> = [
  { value: "all", label: "All rows" },
  { value: "review", label: "To review" },
  { value: "unmapped", label: "Not mapped" },
  { value: "mapped", label: "Mapped" },
  { value: "sample", label: "Spot-check rows" },
  { value: "flagged", label: "Flagged" },
  { value: "skipped", label: "Left out" },
];

export function RateImportReviewPage() {
  const { t } = useTranslation();
  const { importId = "" } = useParams<{ importId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(PRICING_PERMISSIONS.DRAWING_READ);
  const canManage = permissions.includes(PRICING_PERMISSIONS.RATEBOOK_MANAGE);

  const query = useRateImport(importId);
  const imp = query.data;
  const reviewing = imp?.status === "REVIEW";

  const [filter, setFilter] = useState<RowFilter>("review");
  const [chapter, setChapter] = useState<string | null>(null);
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [openRow, setOpenRow] = useState<ImportRow | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [reparsing, setReparsing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [mapCode, setMapCode] = useState("");
  const [minScore, setMinScore] = useState("90");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = window.setTimeout(() => setQ(qInput), 350);
    return () => window.clearTimeout(id);
  }, [qInput]);

  const rowQuery = useMemo(() => ({ filter, chapter, q }), [filter, chapter, q]);
  const rows = useImportRows(importId, rowQuery, Boolean(imp) && imp?.status !== "UPLOADED" && imp?.status !== "PARSING" && imp?.status !== "FAILED");
  const chapters = useImportChapters(importId, Boolean(imp) && (reviewing || imp?.status === "PUBLISHED"));
  const bulk = useBulkRows(importId);
  const rowUpdate = useUpdateImportRow(importId);
  const suggest = useRefreshSuggestions(importId);
  const remove = useDeleteImport();

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("schedules.unavailable", "Schedule imports unavailable")} description={t("pricing.noPermission", "You don't have permission to view this.")} />;
  }
  if (query.isLoading) return <LoadingState label={t("schedules.review.loading", "Loading schedule…")} />;
  if (query.isError || !imp) return <ErrorState title={t("schedules.review.loadError", "We couldn't load this schedule")} onRetry={() => void query.refetch()} />;

  const counts = imp.counts;
  const busy = imp.status === "UPLOADED" || imp.status === "PARSING";
  const editable = reviewing && canManage;
  const fail = (e: unknown) => setError(getApiErrorMessage(e, t("schedules.review.actionError", "That didn't work. Please try again.")));

  function runBulk(payload: BulkPayload, done: (changed: number) => string) {
    setError(null);
    bulk.mutate(payload, {
      onSuccess: (r) => { showToast({ tone: "success", title: done(r.changed) }); setSelected(new Set()); },
      onError: fail,
    });
  }

  function scope(): Pick<BulkPayload, "row_ids" | "filter" | "chapter" | "q"> {
    if (selected.size > 0) return { row_ids: Array.from(selected) };
    return { filter, chapter: chapter ?? undefined, q: q.trim() || undefined };
  }
  const wholeImport = selected.size === 0 && filter === "all" && chapter === null && !q.trim();
  const scopeLabel = selected.size > 0
    ? t("schedules.bulk.selected", "{{n}} selected", { n: selected.size })
    : t("schedules.bulk.allShown", "all rows in this view");

  function toggle(id: string) {
    setSelected((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  }
  function toggleAll(ids: string[], on: boolean) {
    setSelected((prev) => { const next = new Set(prev); ids.forEach((id) => (on ? next.add(id) : next.delete(id))); return next; });
  }
  function verify(row: ImportRow) {
    rowUpdate.mutate({ rowId: row.id, payload: { sample_verified: true } }, { onError: fail });
  }
  function doDelete() {
    remove.mutate(imp!.id, {
      onSuccess: () => { showToast({ tone: "success", title: t("schedules.review.deleted", "Import deleted") }); navigate(RATE_IMPORTS_PATH); },
      onError: (e) => { fail(e); setDeleting(false); },
    });
  }

  return (
    <div className="space-y-7">
      <div><Link to={RATE_IMPORTS_PATH} className="text-[12.5px] font-semibold text-[var(--color-info)] hover:underline">← {t("schedules.review.back", "All schedule imports")}</Link></div>

      <PageHeader
        eyebrow={t("schedules.eyebrow", "IMPORTS")}
        title={imp.book_name || imp.filename}
        description={`${imp.filename} · ${imp.source_kind} · ${formatBytes(imp.file_size)}${imp.page_count ? ` · ${imp.page_count} pages` : ""}${imp.edition ? ` · ${imp.edition}` : ""}`}
        actions={
          <>
            <Badge tone={importStatusTone(imp.status)}>{t(`schedules.status.${imp.status}`, IMPORT_STATUS_LABEL[imp.status])}</Badge>
            {canManage && imp.status !== "PUBLISHED" && !busy ? <Button variant="secondary" size="sm" onClick={() => setReparsing(true)}>{t("schedules.review.reparse", "Read again")}</Button> : null}
            {editable ? <Button variant="primary" size="sm" onClick={() => setPublishing(true)}>{t("schedules.review.publish", "Load into rate book")}</Button> : null}
            {imp.status === "PUBLISHED" && imp.rate_book_id ? <Button variant="primary" size="sm" onClick={() => navigate(rateBookPath(imp.rate_book_id!))}>{t("schedules.review.openBook", "Open the rate book")}</Button> : null}
            {canManage && imp.status !== "PUBLISHED" && !busy ? <Button variant="danger" size="sm" onClick={() => setDeleting(true)}>{t("schedules.review.delete", "Delete")}</Button> : null}
          </>
        }
      />

      {imp.duplicate_of_id ? (
        <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-info-bg)] px-4 py-3 text-[13px] text-[var(--color-text-secondary)]">
          {t("schedules.review.duplicate", "This exact file was uploaded before.")}{" "}
          <Link className="font-semibold text-[var(--color-info)] hover:underline" to={`${RATE_IMPORTS_PATH}/${imp.duplicate_of_id}`}>{t("schedules.review.openEarlier", "Open the earlier import")}</Link>
        </div>
      ) : null}

      {busy ? (
        <Panel><div className="p-6"><LoadingState label={t("schedules.review.reading", "Reading the file. This page updates by itself when the rows are ready.")} /></div></Panel>
      ) : null}

      {imp.status === "FAILED" ? (
        <ErrorState
          title={t("schedules.review.failed", "The file could not be read")}
          description={imp.error_message ?? t("schedules.review.failedDesc", "Try another page layout or a smaller page range.")}
          onRetry={canManage ? () => setReparsing(true) : undefined}
        />
      ) : null}

      {!busy && imp.status !== "FAILED" ? (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <StatCard label={t("schedules.stat.rows", "Rows read")} value={counts.rows ?? imp.row_count} note={t("schedules.stat.rowsNote", "{{n}} left out", { n: counts.skipped ?? 0 })} icon="budget" tone="blue" />
            <StatCard label={t("schedules.stat.review", "To review")} value={counts.to_review ?? 0} note={(counts.to_review ?? 0) > 0 ? t("schedules.stat.reviewNote", "Confirm, fix or leave out") : t("schedules.stat.reviewDone", "Nothing flagged")} icon={(counts.to_review ?? 0) > 0 ? "alert" : "check"} tone={(counts.to_review ?? 0) > 0 ? "gold" : "green"} />
            <StatCard label={t("schedules.stat.mapped", "Mapped")} value={counts.mapped ?? 0} note={t("schedules.stat.mappedNote", "{{n}} not mapped", { n: counts.unmapped ?? 0 })} icon="check" tone="green" />
            <StatCard label={t("schedules.stat.samples", "Spot-checks left")} value={counts.samples_unverified ?? 0} note={t("schedules.stat.samplesNote", "of {{n}} rows to compare with the page", { n: counts.samples ?? 0 })} icon="calendar" tone={(counts.samples_unverified ?? 0) > 0 ? "gold" : "green"} />
          </div>

          {imp.report ? <ImportReportPanel report={imp.report} /> : null}

          <Panel>
            <PanelHeader
              eyebrow={t("schedules.rows.eyebrow", "ROWS")}
              title={t("schedules.rows.title", "Review and map")}
              description={t(
                "schedules.rows.desc",
                "Flagged rows must be confirmed, corrected or left out. Map each row to the work item it prices; suggestions are never applied unless you accept them. Spot-check rows are compared with the page by hand before you can load the book.",
              )}
              action={editable ? (
                <Button variant="secondary" size="sm" disabled={suggest.isPending} onClick={() => suggest.mutate(undefined, { onSuccess: (r) => showToast({ tone: "success", title: t("schedules.rows.suggested", "Suggestions refreshed"), description: t("schedules.rows.suggestedDesc", "{{n}} rows have a suggestion.", { n: r.rows_with_suggestions }) }), onError: fail })}>
                  {t("schedules.rows.refreshSuggest", "Refresh suggestions")}
                </Button>
              ) : null}
            />
            <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] p-4">
              <select className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]" value={filter} onChange={(e) => { setFilter(e.target.value as RowFilter); setSelected(new Set()); }}>
                {FILTERS.map((f) => <option key={f.value} value={f.value}>{t(`schedules.filter.${f.value}`, f.label)}</option>)}
              </select>
              <select className="max-w-[260px] rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]" value={chapter ?? "__all"} onChange={(e) => { setChapter(e.target.value === "__all" ? null : e.target.value); setSelected(new Set()); }}>
                <option value="__all">{t("schedules.filter.allChapters", "All chapters")}</option>
                {(chapters.data ?? []).filter((c) => c.chapter).map((c) => <option key={c.chapter!} value={c.chapter!}>{c.chapter} ({c.rows}{c.to_review ? `, ${c.to_review} to review` : ""})</option>)}
              </select>
              <input className={`${inputClass} max-w-[260px] !py-2 !text-[12.5px]`} placeholder={t("schedules.filter.search", "Search description, item no or code")} value={qInput} onChange={(e) => setQInput(e.target.value)} />
            </div>

            {editable ? (
              <div className="flex flex-wrap items-center gap-2 border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-[12.5px]">
                <span className="font-semibold">{scopeLabel}:</span>
                {wholeImport ? <span className="text-[var(--color-text-muted)]">{t("schedules.bulk.narrow", "pick rows, a filter or a chapter first")}</span> : null}
                <Button size="sm" variant="secondary" disabled={bulk.isPending || wholeImport} onClick={() => runBulk({ action: "confirm", ...scope() }, (n) => t("schedules.bulk.confirmed", "{{n}} rows confirmed", { n }))}>{t("schedules.bulk.confirm", "Mark checked")}</Button>
                <Button size="sm" variant="secondary" disabled={bulk.isPending || wholeImport} onClick={() => runBulk({ action: "skip", ...scope() }, (n) => t("schedules.bulk.skipped", "{{n}} rows left out", { n }))}>{t("schedules.bulk.skip", "Leave out")}</Button>
                <Button size="sm" variant="ghost" disabled={bulk.isPending || wholeImport} onClick={() => runBulk({ action: "unskip", ...scope() }, (n) => t("schedules.bulk.unskipped", "{{n}} rows included again", { n }))}>{t("schedules.bulk.unskip", "Include again")}</Button>
                <span className="mx-1 h-5 w-px bg-[var(--color-border)]" />
                <input className={`${inputClass} !w-40 !py-1.5 !text-[12px]`} placeholder={t("schedules.bulk.codePlaceholder", "Work item code")} value={mapCode} onChange={(e) => setMapCode(e.target.value.toUpperCase())} />
                <Button size="sm" variant="secondary" disabled={bulk.isPending || wholeImport || !mapCode.trim()} onClick={() => runBulk({ action: "map", work_item_code: mapCode.trim(), ...scope() }, (n) => t("schedules.bulk.mapped", "{{n}} rows mapped to {{code}}", { n, code: mapCode.trim() }))}>{t("schedules.bulk.map", "Map to code")}</Button>
                <Button size="sm" variant="ghost" disabled={bulk.isPending || wholeImport} onClick={() => runBulk({ action: "clear_mapping", ...scope() }, (n) => t("schedules.bulk.cleared", "{{n}} mappings removed", { n }))}>{t("schedules.bulk.clear", "Clear mapping")}</Button>
                <span className="mx-1 h-5 w-px bg-[var(--color-border)]" />
                <label className="flex items-center gap-1 text-[var(--color-text-secondary)]">
                  {t("schedules.bulk.accept", "Accept suggestions at")}
                  <input className={`${inputClass} !w-14 !py-1.5 !text-[12px]`} inputMode="numeric" value={minScore} onChange={(e) => setMinScore(e.target.value.replace(/[^0-9]/g, ""))} />%
                </label>
                <Button size="sm" variant="secondary" disabled={bulk.isPending} onClick={() => runBulk({ action: "accept_suggestions", min_score: Math.min(100, Math.max(50, Number(minScore) || 90)) / 100, ...scope() }, (n) => t("schedules.bulk.accepted", "{{n}} suggestions accepted", { n }))}>{t("schedules.bulk.acceptGo", "Accept")}</Button>
              </div>
            ) : null}

            {error ? <div role="alert" className="border-b border-[var(--color-border)] bg-[var(--color-danger-bg)] px-4 py-2 text-[12.5px] text-[var(--color-danger)]">{error}</div> : null}

            {rows.isLoading ? <LoadingState label={t("schedules.rows.loading", "Loading rows…")} /> : rows.isError ? (
              <div className="p-5"><ErrorState title={t("schedules.rows.loadError", "We couldn't load the rows")} onRetry={() => void rows.refetch()} /></div>
            ) : (
              <ImportRowTable
                rows={rows.rows}
                selected={selected}
                canManage={canManage}
                editable={reviewing}
                hasMore={Boolean(rows.hasNextPage)}
                loadingMore={rows.isFetchingNextPage}
                onToggle={toggle}
                onToggleAll={toggleAll}
                onOpen={setOpenRow}
                onVerify={verify}
                onLoadMore={() => void rows.fetchNextPage()}
              />
            )}
          </Panel>
        </>
      ) : null}

      {openRow ? <ImportRowDialog importId={imp.id} row={rows.rows.find((r) => r.id === openRow.id) ?? openRow} canManage={editable} onClose={() => setOpenRow(null)} /> : null}
      {publishing ? <ImportPublishDialog imp={imp} onClose={() => setPublishing(false)} /> : null}
      {reparsing ? <ReparseDialog imp={imp} onClose={() => setReparsing(false)} /> : null}
      {deleting ? (
        <ConfirmDialog
          title={t("schedules.review.deleteTitle", "Delete this import?")}
          description={t("schedules.review.deleteBody", "The uploaded file and all of its rows are removed. Rate books already made from other imports are not affected.")}
          confirmLabel={t("schedules.review.delete", "Delete")}
          pending={remove.isPending}
          error={error}
          onConfirm={doDelete}
          onClose={() => setDeleting(false)}
        />
      ) : null}
    </div>
  );
}

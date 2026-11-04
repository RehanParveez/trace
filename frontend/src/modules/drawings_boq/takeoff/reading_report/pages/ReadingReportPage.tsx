import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../../../identity";
import { useToast } from "../../../../organizations/components/OrganizationUi";
import { usePdfDocument } from "../../hooks/usePdfDocument";
import { takeoffErrorMessage } from "../../utils/errors";
import { CompletenessPanel } from "../components/CompletenessPanel";
import { CoverageBars } from "../components/CoverageBars";
import { ElementInspector } from "../components/ElementInspector";
import { MarkManuallyForm, MisreadForm } from "../components/ReadingActions";
import { SheetCard } from "../components/SheetCard";
import { SheetStrip } from "../components/SheetStrip";
import { SheetViewer } from "../components/SheetViewer";
import { useAddMark, useInputCompleteness, useReadingReport, useReportMisread, useSheetItems, useSheetMarks, useWithdrawMark } from "../hooks/useReadingReport";
import type { Box, ReportItem } from "../types/readingReport.types";
import { classText, STATUS_ORDER, STATUS_VAR, statusText, totalsLine, visibleItems } from "../utils/readingReport";

type Action = null | { kind: "mark" } | { kind: "misread"; item: ReportItem | null };

export function ReadingReportPage() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { projectId, drawingId } = useParams<{ projectId: string; drawingId: string }>();
  const [search, setSearch] = useSearchParams();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(IDENTITY_PERMISSIONS.DRAWING_READ);
  const canEdit = permissions.includes(IDENTITY_PERMISSIONS.BOQ_UPDATE);

  const report = useReadingReport(drawingId);
  const completeness = useInputCompleteness(projectId);
  const pdf = usePdfDocument(drawingId);
  const sheets = report.data?.sheets ?? [];
  const wanted = search.get("sheet");
  const current = sheets.find((s) => s.sheet_id === wanted) ?? sheets[0] ?? null;
  const items = useSheetItems(drawingId, current?.sheet_id ?? null);
  const marks = useSheetMarks(drawingId, current?.sheet_id ?? null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());
  const [classFilter, setClassFilter] = useState<string | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [crop, setCrop] = useState(false);
  const [box, setBox] = useState<Box | null>(null);

  const addMark = useAddMark(drawingId);
  const withdraw = useWithdrawMark(drawingId);
  const misread = useReportMisread(drawingId);

  useEffect(() => {
    setSelectedId(null);
    setAction(null);
    setCrop(false);
    setBox(null);
    setClassFilter(null);
  }, [current?.sheet_id]);

  const all = useMemo(() => items.data?.items ?? [], [items.data]);
  const shown = useMemo(() => visibleItems(all, hidden, classFilter), [all, hidden, classFilter]);
  const selected = all.find((i) => i.id === selectedId) ?? null;

  function selectSheet(id: string) {
    const next = new URLSearchParams(search);
    next.set("sheet", id);
    setSearch(next, { replace: true });
  }

  function toggle(status: string) {
    setHidden((h) => {
      const n = new Set(h);
      if (n.has(status)) n.delete(status);
      else n.add(status);
      return n;
    });
  }

  function failure(title: string, e: unknown) {
    showToast({ tone: "error", title, description: takeoffErrorMessage(e) });
  }

  if (!canRead) return <div className="p-6 text-[13px]">{t("boq.reading.noAccess", "You do not have access to this drawing.")}</div>;

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--color-surface-muted)]" data-testid="reading-report-page">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2">
        <div>
          <h1 className="text-[15px] font-semibold">{t("boq.reading.title", "Reading report")}</h1>
          {report.data ? (
            <p className="text-[12px] text-[var(--color-text-secondary)]" data-testid="report-totals">
              {report.data.totals.ran} of {report.data.totals.sheets} sheets read · {report.data.totals.items} items · {totalsLine(report.data.totals.by_status)}
            </p>
          ) : null}
        </div>
        <Link to={`/takeoff/${projectId}/${drawingId}`} className="rounded-[8px] border border-[var(--color-border)] px-2 py-1 text-[12px]">{t("boq.reading.back", "Back to takeoff")}</Link>
      </header>

      {report.isLoading ? <p className="p-6 text-[12.5px] text-[var(--color-text-muted)]">{t("boq.reading.loading", "Loading the report…")}</p> : null}
      {report.isError ? (
        <p className="p-6 text-[12.5px] text-[var(--color-danger)]">
          {takeoffErrorMessage(report.error)} <button type="button" className="underline" onClick={() => void report.refetch()}>{t("boq.reading.retry", "Try again")}</button>
        </p>
      ) : null}
      {report.data && sheets.length === 0 ? <p className="p-6 text-[12.5px]">{t("boq.reading.noSheets", "This drawing has no sheets yet. Open it in the takeoff first so its sheets are read.")}</p> : null}

      {current ? (
        <>
          <SheetStrip sheets={sheets} currentId={current.sheet_id} onSelect={selectSheet} />
          <div className="grid min-h-0 flex-1 gap-3 overflow-auto p-3 lg:grid-cols-[300px_minmax(0,1fr)_320px]">
            <aside className="space-y-3">
              <SheetCard sheet={current} active onSelect={selectSheet} />
              {current.classes.length ? (
                <p className="px-1 text-[11px] text-[var(--color-text-muted)]">{classFilter ? `Showing only ${classText(classFilter).toLowerCase()}. ` : ""}Click a bar to show only that kind of item on the sheet.</p>
              ) : null}
              {current.classes.length ? <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3"><CoverageBars rows={current.classes} activeClass={classFilter} onPick={setClassFilter} /></div> : null}
              <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12px]" data-testid="status-filter">
                <h3 className="mb-1 font-semibold">Show on the sheet</h3>
                <div className="flex flex-wrap gap-1.5">
                  {STATUS_ORDER.map((s) => (
                    <button key={s} type="button" aria-pressed={!hidden.has(s)} onClick={() => toggle(s)} className={`flex items-center gap-1 rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[11.5px] ${hidden.has(s) ? "opacity-50" : ""}`}>
                      <span className="h-2 w-2 rounded-full" style={{ background: STATUS_VAR[s] }} />{statusText(s)}
                    </button>
                  ))}
                </div>
              </div>
            </aside>

            <main className="min-h-[480px]">
              <SheetViewer
                pdf={pdf}
                pageNo={current.page_no}
                items={shown}
                marks={marks.data ?? []}
                selectedId={selectedId}
                onSelect={(it) => setSelectedId(it?.id ?? null)}
                cropMode={crop}
                onCrop={(b) => {
                  setBox(b);
                  setCrop(false);
                }}
              />
              {items.isError ? <p className="mt-2 text-[12px] text-[var(--color-danger)]">{takeoffErrorMessage(items.error)}</p> : null}
            </main>

            <aside className="space-y-3">
              {action?.kind === "mark" ? (
                <MarkManuallyForm
                  box={box}
                  busy={addMark.isPending}
                  onChooseArea={() => setCrop(true)}
                  onCancel={() => {
                    setAction(null);
                    setCrop(false);
                    setBox(null);
                  }}
                  onSubmit={(v) =>
                    box &&
                    addMark.mutate(
                      { sheet_id: current.sheet_id, item_class: v.item_class, mark: v.mark || null, geometry: { box }, attrs: v.attrs, note: v.note || null },
                      {
                        onSuccess: () => {
                          showToast({ tone: "success", title: t("boq.reading.markSaved", "Mark saved"), description: t("boq.reading.markNote", "It is used for this project only until someone checks it against the sheet.") });
                          setAction(null);
                          setBox(null);
                        },
                        onError: (e) => failure(t("boq.reading.markFailed", "Could not save the mark"), e),
                      },
                    )
                  }
                />
              ) : action?.kind === "misread" ? (
                <MisreadForm
                  item={action.item}
                  box={box}
                  busy={misread.isPending}
                  onChooseArea={() => setCrop(true)}
                  onCancel={() => {
                    setAction(null);
                    setCrop(false);
                    setBox(null);
                  }}
                  onSubmit={(v) =>
                    misread.mutate(
                      {
                        sheet_id: current.sheet_id,
                        kind: v.kind,
                        candidate_id: action.item?.id ?? null,
                        box: action.item ? action.item.box : box,
                        expected: v.expected ? { text: v.expected } : {},
                        note: v.note || null,
                      },
                      {
                        onSuccess: () => {
                          showToast({ tone: "success", title: t("boq.reading.misreadSent", "Report sent"), description: t("boq.reading.misreadNote", "It will be checked against the drawing before the reader is changed.") });
                          setAction(null);
                          setBox(null);
                        },
                        onError: (e) => failure(t("boq.reading.misreadFailed", "Could not send the report"), e),
                      },
                    )
                  }
                />
              ) : (
                <ElementInspector item={selected} canEdit={canEdit} onReport={(it) => setAction({ kind: "misread", item: it })} onMark={() => { setAction({ kind: "mark" }); setBox(null); setCrop(true); }} />
              )}
              {!action ? (
                <button type="button" className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-[11.5px]" onClick={() => { setAction({ kind: "misread", item: null }); setBox(null); setCrop(true); }} data-testid="report-area-misread">
                  {t("boq.reading.reportArea", "Report something the reader got wrong in an area")}
                </button>
              ) : null}
              {(marks.data ?? []).length ? (
                <section className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12px]" data-testid="manual-marks">
                  <h3 className="font-semibold">Marked by hand</h3>
                  <ul className="mt-1 space-y-1">
                    {(marks.data ?? []).map((m) => (
                      <li key={m.id} className="flex items-center justify-between gap-2">
                        <span>{classText(m.item_class)}{m.mark ? ` ${m.mark}` : ""} <span className="text-[var(--color-text-muted)]">{m.image_checked ? "checked" : "not checked yet"}</span></span>
                        {canEdit ? <button type="button" className="text-[11px] underline" disabled={withdraw.isPending} onClick={() => withdraw.mutate(m.id, { onError: (e) => failure(t("boq.reading.withdrawFailed", "Could not withdraw the mark"), e) })}>Withdraw</button> : null}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-1 text-[10.5px] text-[var(--color-text-muted)]">Marks made by hand are not scored as readings until they are checked against the sheet.</p>
                </section>
              ) : null}
            </aside>
          </div>

          <div className="grid gap-3 border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 lg:grid-cols-2">
            <CompletenessPanel data={completeness.data} loading={completeness.isLoading} error={completeness.isError} onRetry={() => void completeness.refetch()} />
            <section className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12px]" data-testid="report-limits">
              <h3 className="font-semibold">What this report does not do</h3>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[var(--color-text-secondary)]">
                <li>Marks made by hand change this project only. They do not change quantities and are not scored until checked.</li>
                {report.data && !report.data.joins_applied_to_quantities ? <li>Joins between drawings are shown for reference. They are not yet used to work out quantities in the app.</li> : null}
                <li>A status says how sure the reader is, not whether the drawing itself is right.</li>
              </ul>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}

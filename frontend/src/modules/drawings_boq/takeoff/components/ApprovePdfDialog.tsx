import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Badge, Button, Icon } from "../../../organizations/components/OrganizationUi";
import { useApprovePreview, useApproveReady } from "../hooks/useTakeoff";
import { REASON_LABEL, SIZE_FIELDS, failureLines, sizeState, typedFromInputs } from "../utils/approve";
import type { ApproveSummary } from "../utils/approve";
import type { ApproveReadyResult } from "../types/takeoff.types";
import { ReviewPanel } from "./ReviewPanel";
import { useQsProposed } from "../../hooks/useProposed";
import { proposedSize } from "../../utils/qsProposed";

interface ApprovePdfDialogProps {
  projectId: string;
  drawingId: string;
  filename: string;
  onClose: () => void;
}

const HELD_ORDER = ["ASSUMED", "VALUE_MISSING", "WARNING", "CHECK_WARNS", "ERROR", "NOT_MEASURABLE", "FLOOR_SOURCE_UNDECIDED", "ADDED_FROM_SECOND_SHEET"];

export function PreviewBlock({ data }: { data: ApproveReadyResult }) {
  const { t } = useTranslation();
  const skipped = data.skipped_by_reason ?? {};
  const wouldAccept = data.would_accept ?? 0;
  const drafts = data.draft_total ?? 0;
  const nothingToDo = wouldAccept === 0 && drafts === 0;
  return (
    <div className="space-y-1.5 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3" data-testid="approve-preview">
      <p className="font-semibold text-[var(--color-text-primary)]">
        {t("takeoff.approve.ready", { defaultValue: "{{n}} items will be accepted and confirmed.", n: wouldAccept })}
      </p>
      {drafts > 0 ? (
        <p>{t("takeoff.approve.drafts", { defaultValue: "{{n}} measurements already made from accepted items are still draft and will be confirmed too.", n: drafts })}</p>
      ) : null}
      {(data.confirmed_total ?? 0) > 0 ? (
        <p>{t("takeoff.approve.alreadyConfirmed", { defaultValue: "{{n}} measurements are confirmed already.", n: data.confirmed_total })}</p>
      ) : null}
      {data.floors_pending > 0 ? (
        <p className="text-[var(--color-warning)]">
          {t("takeoff.approve.floorsPending", { defaultValue: "{{n}} floor(s) were read from two sheets. The floor's own sheet is used first, then the count above can grow.", n: data.floors_pending })}
        </p>
      ) : null}
      {HELD_ORDER.filter((code) => (skipped[code] ?? 0) > 0).map((code) => (
        <p key={code} data-testid={`held-${code}`}>
          {t("takeoff.approve.held", { defaultValue: "{{n}} held back: {{why}}.", n: skipped[code], why: t(`takeoff.approve.reason.${code}`, REASON_LABEL[code] ?? code) })}
        </p>
      ))}
      {nothingToDo ? (
        <p className="font-semibold text-[var(--color-warning)]" data-testid="approve-nothing">
          {t("takeoff.approve.nothing", "Nothing is ready. Open the PDF's elements and press Read sheets first, or review the items on the Measure page.")}
        </p>
      ) : null}
    </div>
  );
}

export function ResultBlock({ result }: { result: ApproveSummary }) {
  const { t } = useTranslation();
  const failures = failureLines(result);
  return (
    <div className="space-y-2" data-testid="approve-result">
    <p className="text-[13px] font-semibold text-[var(--color-text-primary)]">
      {t("takeoff.approve.done", { defaultValue: "{{a}} items accepted and {{c}} measurements confirmed.", a: result.accepted, c: result.confirmed })}
    </p>
    {result.confirmed_total > 0 ? (
      <p className="text-[var(--color-success)]">
        {t("takeoff.approve.readyToRun", { defaultValue: "{{n}} confirmed measurements in this PDF. Select it in the Calculation run section and start the calculation.", n: result.confirmed_total })}
      </p>
    ) : (
      <p className="text-[var(--color-warning)]">{t("takeoff.approve.noneConfirmed", "No measurement is confirmed yet, so the calculation cannot use this PDF.")}</p>
    )}
    {result.floors_chosen > 0 ? (
      <p>{t("takeoff.approve.floorsDone", { defaultValue: "The floor's own sheet was used for {{n}} floor(s).", n: result.floors_chosen })}</p>
    ) : null}
    {failures.length > 0 ? (
      <div data-testid="approve-failures">
        <p className="font-semibold text-[var(--color-text-primary)]">{t("takeoff.approve.notAccepted", "Not accepted:")}</p>
        <ul className="list-disc pl-5">
          {failures.map((f) => <li key={`${f.code}|${f.message}`}>{f.count} × {f.message || f.code}</li>)}
        </ul>
      </div>
    ) : null}
    {result.confirm_failed.length > 0 ? (
      <p className="text-[var(--color-warning)]">
        {t("takeoff.approve.notConfirmed", { defaultValue: "{{n}} measurements could not be confirmed. First reason: {{why}}", n: result.confirm_failed.length, why: result.confirm_failed[0]?.message ?? result.confirm_failed[0]?.code ?? "" })}
      </p>
    ) : null}
    {result.remaining > 0 || result.stopped ? (
      <p className="text-[var(--color-warning)]">{t("takeoff.approve.stopped", { defaultValue: "{{n}} items are still waiting. Press Approve again, or finish them on the Measure page.", n: result.remaining })}</p>
    ) : null}
    {Object.entries(result.skipped_by_reason).filter(([, n]) => n > 0).length > 0 ? (
      <p>{t("takeoff.approve.heldAfter", { defaultValue: "{{n}} items were held back for you to check on the Measure page.", n: Object.values(result.skipped_by_reason).reduce((a, b) => a + b, 0) })}</p>
    ) : null}
    </div>
  );
}

export function ApprovePdfDialog({ projectId, drawingId, filename, onClose }: ApprovePdfDialogProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [assumed, setAssumed] = useState(false);
  const [warned, setWarned] = useState(false);
  const [added, setAdded] = useState(false);
  const [sizes, setSizes] = useState<Record<string, string>>({});
  const [applied, setApplied] = useState<Record<string, number>>({});
  const [progress, setProgress] = useState<ApproveSummary | null>(null);
  const [result, setResult] = useState<ApproveSummary | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const { typed, bad } = useMemo(() => typedFromInputs(sizes), [sizes]);

  const preview = useApprovePreview(drawingId, { accept_assumed: assumed, accept_warned: warned, accept_added: added, typed: applied }, result === null);
  const approve = useApproveReady(drawingId);
  const { data: proposedSet } = useQsProposed();

  useEffect(() => {
    closeRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !approve.isPending) {
        event.preventDefault();
        onClose();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, approve.isPending]);

  const data = preview.data;
  const skipped = data?.skipped_by_reason ?? {};
  const nothingToDo = data !== undefined && (data.would_accept ?? 0) === 0 && (data.draft_total ?? 0) === 0;
  const missingCount = skipped.VALUE_MISSING ?? 0;
  const showSizes = missingCount > 0 || Object.keys(applied).length > 0 || Object.values(sizes).some((v) => v.trim());

  function start() {
    setResult(null);
    approve.mutate(
      { body: { accept_assumed: assumed, accept_warned: warned, accept_added: added, confirm: true, typed }, onProgress: setProgress },
      { onSuccess: (sum) => setResult(sum) },
    );
  }

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-[var(--color-trace-navy)]/70 p-3 backdrop-blur-[2px]">
      <div role="dialog" aria-modal="true" aria-label={filename}
        className="flex max-h-[92vh] w-full max-w-[760px] flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[0_24px_70px_rgba(8,13,24,0.35)]">
        <div className="flex items-start justify-between gap-3 border-b border-[var(--color-border)] px-5 py-4">
          <div className="min-w-0">
            <h2 className="font-[Archivo] text-[16px] font-bold text-[var(--color-text-primary)]">
              {t("takeoff.approve.title", "Approve the items of this PDF for the calculation")}
            </h2>
            <p className="truncate text-[11.5px] text-[var(--color-text-muted)]">{filename}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} disabled={approve.isPending} aria-label="Close dialog"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]">
            <Icon name="x" size={16} />
          </button>
        </div>

        <div className="space-y-4 overflow-y-auto px-5 py-4 text-[12.5px] text-[var(--color-text-secondary)]">
          <p>
            {t("takeoff.approve.intro",
              "This uses each floor's own sheet where a floor was read from two sheets, accepts the items that are ready, and confirms them as measurements. The calculation run then counts this PDF. Items held back stay on the Measure page for you to check.")}
          </p>

          {result === null ? (
            <>
              {preview.isLoading ? (
                <p data-testid="approve-loading">{t("takeoff.approve.counting", "Counting what is ready…")}</p>
              ) : preview.isError ? (
                <p className="text-[var(--color-danger)]">{t("takeoff.approve.previewFailed", "Could not count the items just now. Try again.")}</p>
              ) : data ? (
                <PreviewBlock data={data} />
              ) : null}

              <ReviewPanel drawingId={drawingId} />

              <div className="space-y-2">
                <label className="flex items-start gap-2">
                  <input type="checkbox" checked={assumed} disabled={approve.isPending} onChange={(e) => setAssumed(e.target.checked)} />
                  <span>
                    {t("takeoff.approve.acceptAssumed", "Also approve items whose size is assumed")}
                    {(skipped.ASSUMED ?? 0) > 0 ? <Badge tone="gold">{skipped.ASSUMED}</Badge> : null}
                    <span className="block text-[11px] text-[var(--color-text-muted)]">
                      {t("takeoff.approve.acceptAssumedHint", "They stay marked as assumed, with a range, in the bill and in the elements list.")}
                    </span>
                  </span>
                </label>
                <label className="flex items-start gap-2">
                  <input type="checkbox" checked={warned} disabled={approve.isPending} onChange={(e) => setWarned(e.target.checked)} />
                  <span>
                    {t("takeoff.approve.acceptWarned", "Also approve items that carry a warning")}
                    {(skipped.WARNING ?? 0) + (skipped.CHECK_WARNS ?? 0) > 0 ? <Badge tone="gold">{(skipped.WARNING ?? 0) + (skipped.CHECK_WARNS ?? 0)}</Badge> : null}
                  </span>
                </label>
                {(skipped.ADDED_FROM_SECOND_SHEET ?? 0) > 0 || added ? (
                  <label className="flex items-start gap-2" data-testid="approve-added">
                    <input type="checkbox" checked={added} disabled={approve.isPending} onChange={(e) => setAdded(e.target.checked)} />
                    <span>
                      {t("takeoff.approve.acceptAdded", "Also approve items only the second sheet shows")}
                      {(skipped.ADDED_FROM_SECOND_SHEET ?? 0) > 0 ? <Badge tone="gold">{skipped.ADDED_FROM_SECOND_SHEET}</Badge> : null}
                      <span className="block text-[11px] text-[var(--color-text-muted)]">
                        {t("takeoff.approve.acceptAddedHint", "Walls, beams, rooms or openings that the floor's own sheet does not show. The other sheet is drawn small and can show lines that are not walls, so check them on the sheet first.")}
                      </span>
                    </span>
                  </label>
                ) : null}
              </div>

              {showSizes ? (
                <fieldset className="space-y-2 rounded-[10px] border border-[var(--color-border)] p-3" disabled={approve.isPending}>
                  <legend className="px-1 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                    {t("takeoff.approve.sizesTitle", "Sizes the drawing does not print")}
                  </legend>
                  <p className="text-[11.5px]">
                    {t("takeoff.approve.sizesHint", "Used only where this drawing prints no size. Write 3050, 3.05 m, 10 ft, 10'6 or 9 in. They are recorded as typed.")}
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {SIZE_FIELDS.map((field) => {
                      const state = sizeState(sizes[field.key] ?? "");
                      return (
                        <label key={field.key} className="block">
                          <span className="text-[11px] font-semibold text-[var(--color-text-primary)]">{t(`takeoff.approve.size.${field.key}`, field.label)}</span>
                          <input value={sizes[field.key] ?? ""} inputMode="text" aria-label={field.label}
                            onChange={(e) => setSizes((s) => ({ ...s, [field.key]: e.target.value }))}
                            onBlur={() => setApplied(typed)}
                            className="mt-1 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px]" />
                          {proposedSize(field.key, proposedSet) && state.kind === "empty" ? (
                            <button type="button" data-testid={`workbook-size-${field.key}`} title={proposedSize(field.key, proposedSet)?.evidence}
                              onClick={() => {
                                const next = { ...sizes, [field.key]: proposedSize(field.key, proposedSet)?.text ?? "" };
                                setSizes(next);
                                setApplied(typedFromInputs(next).typed);
                              }}
                              className="mt-0.5 block text-left text-[10.5px] font-semibold text-[var(--color-trace-gold-dark)] underline">
                              {t("takeoff.approve.useWorkbookSize", { defaultValue: "Use the QS workbook size: {{size}}", size: proposedSize(field.key, proposedSet)?.text })}
                            </button>
                          ) : null}
                          <span className={`block text-[10.5px] ${state.kind === "bad" ? "text-[var(--color-danger)]" : "text-[var(--color-text-muted)]"}`}>
                            {state.kind === "ok" ? `= ${state.mm} mm` : state.kind === "bad" ? t("takeoff.approve.sizeBad", "Not a size I can read") : " "}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </fieldset>
              ) : null}

              {approve.isPending && progress ? (
                <p data-testid="approve-progress" className="font-semibold text-[var(--color-text-primary)]">
                  {t("takeoff.approve.progress", { defaultValue: "Approving… {{a}} accepted, {{c}} confirmed, {{r}} to go.", a: progress.accepted, c: progress.confirmed, r: progress.remaining })}
                </p>
              ) : null}
              {approve.isError ? (
                <p className="text-[var(--color-danger)]">{t("takeoff.approve.failed", "The approval stopped. What was done is kept. Try again.")}</p>
              ) : null}
            </>
          ) : (
            <ResultBlock result={result} />
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--color-border)] px-5 py-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/app/takeoff/${projectId}/${drawingId}`)} disabled={approve.isPending}>
            {t("takeoff.approve.measure", "Review on the Measure page")}
          </Button>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={onClose} disabled={approve.isPending}>
              {result ? t("takeoff.approve.close", "Close") : t("takeoff.approve.cancel", "Cancel")}
            </Button>
            {result === null || result.remaining > 0 ? (
              <Button variant="primary" size="sm" onClick={start} disabled={approve.isPending || preview.isLoading || nothingToDo || bad.length > 0}>
                <Icon name="check" size={14} />
                {approve.isPending ? t("takeoff.approve.working", "Approving…") : t("takeoff.approve.go", "Approve and confirm")}
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

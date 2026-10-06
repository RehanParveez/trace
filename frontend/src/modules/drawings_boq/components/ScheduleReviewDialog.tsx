import { useState } from "react";
import { Badge, Button, ErrorState, LoadingState, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import {useAddScheduleRow, useArchiveScheduleImport, useBulkReviewScheduleRows, useConfirmScheduleImport, useProjectLevels, useRejectScheduleImport, useRematchScheduleImport, useScheduleImportDetail, useSpaces,
} from "../hooks/useSpacesSchedules";
import { importTone, isImportEditable } from "../utils/drawings-boq.utils";
import type { Drawing } from "../types/drawings-boq.types";
import type { ConfirmImportResponse, RowDecision } from "../types/drawings-boq.types";
import { ConfirmDialog } from "./ConfirmDialog";
import { ReasonDialog } from "./ReasonDialog";
import { ScheduleRowsTable } from "./ScheduleRowsTable";
import { useTranslation } from "react-i18next";

interface ScheduleReviewDialogProps {
  projectId: string;
  importId: string;
  drawings: Drawing[];
  canImport: boolean;
  canManageSpaces: boolean;
  onClose: () => void;
}

type Dlg = "confirm" | "reject" | "archive" | null;

export function ScheduleReviewDialog({ projectId, importId, drawings, canImport, onClose }: ScheduleReviewDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const detail = useScheduleImportDetail(importId);
  const imp = detail.data;
  const levels = useProjectLevels(drawings);
  const spacesQuery = useSpaces(projectId, { current_only: true });
  const addRow = useAddScheduleRow(importId);
  const bulk = useBulkReviewScheduleRows(importId);
  const confirm = useConfirmScheduleImport(projectId, importId);
  const reject = useRejectScheduleImport(projectId, importId);
  const archive = useArchiveScheduleImport(projectId, importId);
  const rematch = useRematchScheduleImport(importId);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const [dlg, setDlg] = useState<Dlg>(null);
  const [dlgError, setDlgError] = useState<string | null>(null);
  const [rejectPending, setRejectPending] = useState(false);
  const [result, setResult] = useState<ConfirmImportResponse | null>(null);

  const rows = imp?.rows ?? [];
  const editable = !!imp && canImport && isImportEditable(imp.status);
  const isFinish = imp?.schedule_kind === "FINISH";
  const summary = imp?.summary;
  const pending = summary?.pending ?? 0;

  function toggle(id: string) { setSelected((c) => { const n = new Set(c); if (n.has(id)) n.delete(id); else n.add(id); return n; }); }
  function toggleAll(checked: boolean) { setSelected(checked ? new Set(rows.map((r) => r.id)) : new Set()); }

  function runBulk(decision: RowDecision) {
    setNotice(null);
    bulk.mutate({ rowIds: [...selected], decision }, {
      onSuccess: (r) => {
        setSelected(new Set());
        if (r.failed.length > 0) {
          const byId = new Map(rows.map((x) => [x.id, x.row_no]));
          setNotice(r.failed.map((f) => `${t("schedules.row", "Row")} ${byId.get(f.row_id) ?? "?"}: ${f.message}`).join("\n"));
        }
        showToast({ tone: r.failed.length ? "info" : "success", title: t("schedules.bulkDone", "{{n}} row(s) updated", { n: r.updated }) });
      },
      onError: (e) => setNotice(getApiErrorMessage(e, t("schedules.bulkError", "Couldn't update the selected rows."))),
    });
  }

  function addBlank() {
    setNotice(null);
    addRow.mutate({}, { onError: (e) => setNotice(getApiErrorMessage(e, t("schedules.addError", "Couldn't add a row."))) });
  }

  function doConfirm() {
    setDlgError(null);
    confirm.mutate(rejectPending && pending > 0, {
      onSuccess: (r) => { setResult(r); setDlg(null); setSelected(new Set()); },
      onError: (e) => setDlgError(getApiErrorMessage(e, t("schedules.confirmError", "Couldn't confirm this schedule."))),
    });
  }

  function doReject(note: string) {
    setDlgError(null);
    reject.mutate(note || null, {
      onSuccess: () => { setDlg(null); showToast({ tone: "success", title: t("schedules.rejected", "Schedule rejected") }); },
      onError: (e) => setDlgError(getApiErrorMessage(e, t("schedules.rejectError", "Couldn't reject this schedule."))),
    });
  }

  function doArchive() {
    setDlgError(null);
    archive.mutate(undefined, {
      onSuccess: () => { setDlg(null); showToast({ tone: "success", title: t("schedules.archived", "Schedule archived"), description: t("schedules.archivedDesc", "Finishes it created were removed. Re-run the calculation.") }); },
      onError: (e) => setDlgError(getApiErrorMessage(e, t("schedules.archiveError", "Couldn't archive this schedule."))),
    });
  }

  function doRematch() {
    setNotice(null);
    rematch.mutate(undefined, {
      onSuccess: (r) => showToast({ tone: "info", title: t("schedules.rematched", "{{n}} row(s) re-matched to the model", { n: r.rows_changed }), description: r.rerun_recommended ? t("schedules.rerun", "Re-run the calculation to apply this.") : undefined }),
      onError: (e) => setNotice(getApiErrorMessage(e, t("schedules.rematchError", "Couldn't re-match this schedule."))),
    });
  }

  return (
    <Modal title={imp?.file_name ?? t("schedules.manualName", "Manual schedule")} description={imp ? `${imp.schedule_kind} · ${imp.source}` : undefined} onClose={onClose} wide>
      {detail.isLoading ? (
        <LoadingState label={t("schedules.loadingDetail", "Loading schedule…")} />
      ) : detail.isError || !imp || !summary ? (
        <ErrorState title={t("schedules.detailError", "Couldn't load this schedule")} onRetry={() => void detail.refetch()} />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={importTone(imp.status)}>{imp.status}</Badge>
            <Badge tone="gold">{t("schedules.sum.pending", "{{n}} pending", { n: summary.pending })}</Badge>
            <Badge tone="green">{t("schedules.sum.confirmed", "{{n}} confirmed", { n: summary.confirmed })}</Badge>
            <Badge tone="red">{t("schedules.sum.rejected", "{{n}} rejected", { n: summary.rejected })}</Badge>
            {!isFinish ? <Badge tone="blue">{t("schedules.sum.matched", "{{n}} matched in model", { n: summary.model_matched })}</Badge> : null}
            {isFinish ? <Badge tone="blue">{t("schedules.sum.linked", "{{n}} linked to rooms", { n: summary.finish_rows_linked })}</Badge> : null}
            {isFinish && summary.finish_rows_unlinked > 0 ? <Badge tone="gold">{t("schedules.sum.unlinked", "{{n}} without a room", { n: summary.finish_rows_unlinked })}</Badge> : null}
          </div>
          {imp.notes ? <p className="text-[12px] italic text-[var(--color-text-muted)]">{imp.notes}</p> : null}

          {summary.count_mismatches.length > 0 ? (
            <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-warning-bg)] px-3 py-2.5 text-[12px] text-[var(--color-warning)]">
              <div className="mb-1 font-semibold">{t("schedules.mismatch", "Schedule counts differ from the model")}</div>
              <ul className="space-y-0.5">{summary.count_mismatches.map((m) => <li key={m.row_id}>{m.mark ?? "—"}: {t("schedules.mismatchRow", "schedule says {{s}}, model has {{m}}", { s: Number(m.schedule_quantity), m: m.model_count })}</li>)}</ul>
            </div>
          ) : null}

          {result ? (
            <div className="space-y-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
              <div className="font-semibold text-[var(--color-text-primary)]">{t("schedules.result.title", "Schedule confirmed")}</div>
              <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-[12px]">
                <span>{t("schedules.result.created", "finishes created")}: {result.finishes_created}</span>
                <span>{t("schedules.result.updated", "finishes updated")}: {result.finishes_updated}</span>
                <span>{t("schedules.result.ledger", "ledger lines")}: {result.ledger_lines}</span>
                <span>{t("schedules.result.model", "matched to model")}: {result.model_matched_rows}</span>
                {result.unlinked_finish_rows > 0 ? <span>{t("schedules.result.unlinked", "finish rows without a room")}: {result.unlinked_finish_rows}</span> : null}
              </div>
              {result.finish_conflicts.length > 0 ? (
                <ul className="list-disc pl-5 text-[var(--color-warning)]">{result.finish_conflicts.map((c) => <li key={c.row_id}>{c.surface} {c.work_item_code}: {c.reason}</li>)}</ul>
              ) : null}
              {result.rerun_recommended ? <div className="font-semibold text-[var(--color-warning)]">{t("schedules.result.rerun", "Re-run the calculation so these changes reach the BOQ.")}</div> : null}
            </div>
          ) : null}

          {notice ? <pre className="whitespace-pre-wrap rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 font-sans text-[12px] text-[var(--color-danger)]">{notice}</pre> : null}

          {canImport ? (
            <div className="flex flex-wrap items-center gap-2 border-y border-[var(--color-border)] py-3">
              {editable ? (
                <>
                  <Button variant="ghost" size="sm" disabled={addRow.isPending} onClick={addBlank}>{t("schedules.addRow", "Add row")}</Button>
                  <Button variant="secondary" size="sm" disabled={selected.size === 0 || bulk.isPending} onClick={() => runBulk("CONFIRMED")}>{t("schedules.acceptSelected", "Accept selected")} ({selected.size})</Button>
                  <Button variant="ghost" size="sm" disabled={selected.size === 0 || bulk.isPending} onClick={() => runBulk("REJECTED")}>{t("schedules.rejectSelected", "Reject selected")}</Button>
                  <div className="ml-auto flex gap-2">
                    <Button variant="ghost" size="sm" disabled={rematch.isPending} onClick={doRematch}>{t("schedules.rematch", "Re-match to model")}</Button>
                    <Button variant="ghost" size="sm" onClick={() => { setDlgError(null); setDlg("reject"); }}>{t("schedules.rejectImport", "Reject schedule")}</Button>
                    <Button variant="primary" size="sm" disabled={rows.length === 0} onClick={() => { setDlgError(null); setRejectPending(false); setDlg("confirm"); }}>{t("schedules.confirmImport", "Confirm schedule")}</Button>
                  </div>
                </>
              ) : imp.status === "CONFIRMED" ? (
                <div className="ml-auto flex gap-2">
                  <Button variant="ghost" size="sm" disabled={rematch.isPending} onClick={doRematch}>{t("schedules.rematch", "Re-match to model")}</Button>
                  <Button variant="ghost" size="sm" onClick={() => { setDlgError(null); setDlg("archive"); }}>{t("schedules.archive", "Archive")}</Button>
                </div>
              ) : null}
            </div>
          ) : null}

          {rows.length === 0 ? (
            <p className="py-6 text-center text-[12.5px] text-[var(--color-text-muted)]">{t("schedules.noRows", "This schedule has no rows yet.")}</p>
          ) : (
            <ScheduleRowsTable importId={importId} rows={rows} editable={editable} isFinishSchedule={isFinish} spaces={spacesQuery.data ?? []} levels={levels}
              selected={selected} onToggle={toggle} onToggleAll={toggleAll} onNotice={setNotice} />
          )}
        </div>
      )}

      {dlg === "confirm" ? (
        <ConfirmDialog title={t("schedules.confirmTitle", "Confirm schedule")} description={t("schedules.confirmDesc", "Confirmed rows count toward the BOQ. Finish rows set room finishes.")}
          confirmLabel={confirm.isPending ? t("common.saving", "Saving…") : t("schedules.confirmImport", "Confirm schedule")} pending={confirm.isPending} error={dlgError} onConfirm={doConfirm} onClose={() => setDlg(null)}>
          {pending > 0 ? (
            <label className="flex items-start gap-2 text-[12.5px] text-[var(--color-text-secondary)]">
              <input type="checkbox" className="mt-0.5" checked={rejectPending} onChange={(e) => setRejectPending(e.target.checked)} />
              {t("schedules.rejectRest", "Reject the {{n}} row(s) still pending. Otherwise confirming is blocked until they're reviewed.", { n: pending })}
            </label>
          ) : null}
        </ConfirmDialog>
      ) : null}
      {dlg === "reject" ? (
        <ReasonDialog title={t("schedules.rejectTitle", "Reject schedule")} label={t("schedules.rejectNote", "Note (optional)")} required={false}
          confirmLabel={reject.isPending ? t("common.saving", "Saving…") : t("schedules.rejectImport", "Reject schedule")} pending={reject.isPending} error={dlgError} onConfirm={doReject} onClose={() => setDlg(null)} />
      ) : null}
      {dlg === "archive" ? (
        <ConfirmDialog title={t("schedules.archiveTitle", "Archive schedule")} confirmLabel={archive.isPending ? t("common.saving", "Saving…") : t("schedules.archive", "Archive")} pending={archive.isPending} error={dlgError} onConfirm={doArchive} onClose={() => setDlg(null)}>
          <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("schedules.archiveBody", "Room finishes created from this schedule are switched off. Re-run the calculation afterwards.")}</p>
        </ConfirmDialog>
      ) : null}
    </Modal>
  );
}


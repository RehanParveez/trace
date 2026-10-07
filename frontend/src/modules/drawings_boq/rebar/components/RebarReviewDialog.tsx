import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, ErrorState, LoadingState, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useProjectLevels } from "../../hooks/useSpacesSchedules";
import {
  useArchiveRebarImport, useBulkReviewRebarRows, useConfirmRebarImport, useRebarImportDetail, useRebarShapes, useRejectRebarImport,
} from "../hooks/useRebar";
import { importTone, isImportEditable } from "../../utils/drawings-boq.utils";
import { hasRoleFamily, rebarRowBlocker } from "../utils/rebar.utils";
import type { Drawing, RebarConfirmResponse, RowDecision, ScheduleImportResponse } from "../../types/drawings-boq.types";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { RebarRowsTable } from "./RebarRowsTable";

interface RebarReviewDialogProps {
  projectId: string;
  imp: ScheduleImportResponse;
  drawings: Drawing[];
  canImport: boolean;
  onClose: () => void;
}

type Dlg = "confirm" | "reject" | "archive" | null;

export function RebarReviewDialog({ projectId, imp, drawings, canImport, onClose }: RebarReviewDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const detail = useRebarImportDetail(imp.id);
  const shapesQuery = useRebarShapes();
  const levels = useProjectLevels(drawings);
  const bulk = useBulkReviewRebarRows(projectId, imp.id);
  const confirm = useConfirmRebarImport(projectId, imp.id);
  const reject = useRejectRebarImport(projectId, imp.id);
  const archive = useArchiveRebarImport(projectId, imp.id);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const [dlg, setDlg] = useState<Dlg>(null);
  const [dlgError, setDlgError] = useState<string | null>(null);
  const [rejectPending, setRejectPending] = useState(false);
  const [result, setResult] = useState<RebarConfirmResponse | null>(null);

  const rows = detail.data?.rows ?? [];
  const shapes = shapesQuery.data ?? [];
  const editable = canImport && isImportEditable(imp.status);
  const counts = {
    pending: rows.filter((r) => r.review_status === "PENDING").length,
    confirmed: rows.filter((r) => r.review_status === "CONFIRMED").length,
    rejected: rows.filter((r) => r.review_status === "REJECTED").length,
    blocked: rows.filter((r) => r.review_status === "PENDING" && rebarRowBlocker(r, shapes)).length,
    noType: rows.filter((r) => r.review_status !== "REJECTED" && !r.matched_element_id && !hasRoleFamily(r.role)).length,
  };

  function toggle(id: string) { setSelected((c) => { const n = new Set(c); if (n.has(id)) n.delete(id); else n.add(id); return n; }); }
  function toggleAll(checked: boolean) { setSelected(checked ? new Set(rows.map((r) => r.id)) : new Set()); }

  function runBulk(decision: RowDecision) {
    setNotice(null);
    bulk.mutate({ rowIds: [...selected], decision }, {
      onSuccess: (r) => {
        setSelected(new Set());
        if (r.failed.length > 0) {
          const byId = new Map(rows.map((x) => [x.id, x.row_no]));
          setNotice(r.failed.map((f) => `${t("rebar.row", "Row")} ${byId.get(f.row_id) ?? "?"}: ${f.message}`).join("\n"));
        }
        showToast({ tone: r.failed.length ? "info" : "success", title: t("rebar.bulkDone", "{{n}} row(s) updated", { n: r.updated }) });
      },
      onError: (e) => setNotice(getApiErrorMessage(e, t("rebar.bulkError", "Couldn't update the selected rows."))),
    });
  }

  function doConfirm() {
    setDlgError(null);
    confirm.mutate(rejectPending && counts.pending > 0, {
      onSuccess: (r) => { setResult(r); setDlg(null); setSelected(new Set()); },
      onError: (e) => setDlgError(getApiErrorMessage(e, t("rebar.confirmError", "Couldn't confirm this bar schedule."))),
    });
  }

  function doReject() {
    setDlgError(null);
    reject.mutate(undefined, {
      onSuccess: () => { setDlg(null); showToast({ tone: "success", title: t("rebar.rejected", "Bar schedule rejected") }); },
      onError: (e) => setDlgError(getApiErrorMessage(e, t("rebar.rejectError", "Couldn't reject this bar schedule."))),
    });
  }

  function doArchive() {
    setDlgError(null);
    archive.mutate(undefined, {
      onSuccess: () => {
        setDlg(null);
        showToast({ tone: "success", title: t("rebar.archived", "Bar schedule archived"), description: t("rebar.rerun", "Re-run the calculation so the steel in the BOQ is updated.") });
      },
      onError: (e) => setDlgError(getApiErrorMessage(e, t("rebar.archiveError", "Couldn't archive this bar schedule."))),
    });
  }

  return (
    <Modal title={imp.file_name ?? t("rebar.untitled", "Bar schedule")} description={`BBS · ${imp.source}`} onClose={onClose} wide>
      {detail.isLoading ? (
        <LoadingState label={t("rebar.loadingDetail", "Loading bar schedule…")} />
      ) : detail.isError || !detail.data ? (
        <ErrorState title={t("rebar.detailError", "Couldn't load this bar schedule")} onRetry={() => void detail.refetch()} />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={importTone(imp.status)}>{imp.status}</Badge>
            <Badge tone="gold">{t("rebar.sum.pending", "{{n}} pending", { n: counts.pending })}</Badge>
            <Badge tone="green">{t("rebar.sum.confirmed", "{{n}} confirmed", { n: counts.confirmed })}</Badge>
            <Badge tone="red">{t("rebar.sum.rejected", "{{n}} rejected", { n: counts.rejected })}</Badge>
            <Badge tone="blue">{t("rebar.sum.matched", "{{n}} matched to model", { n: detail.data.matched_count })}</Badge>
            {counts.blocked > 0 ? <Badge tone="gold">{t("rebar.sum.blocked", "{{n}} need fixing before accept", { n: counts.blocked })}</Badge> : null}
          </div>
          {imp.notes ? <p className="text-[12px] italic text-[var(--color-text-muted)]">{imp.notes}</p> : null}

          {counts.noType > 0 && editable ? (
            <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-warning-bg)] px-3 py-2.5 text-[12px] text-[var(--color-warning)]">
              {t("rebar.noTypeWarning", "{{n}} row(s) have no member type and no model match. Set the type so the steel estimate for that member is switched off; otherwise the same steel is counted twice.", { n: counts.noType })}
            </div>
          ) : null}

          {result ? (
            <div className="space-y-1 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
              <div className="font-semibold text-[var(--color-text-primary)]">{t("rebar.result.title", "Bar schedule confirmed")}</div>
              <div className="flex flex-wrap gap-x-6 font-mono text-[12px]">
                <span>{t("rebar.result.confirmed", "rows confirmed")}: {result.confirmed_count}</span>
                <span>{t("rebar.result.rejected", "rows rejected")}: {result.rejected_count}</span>
              </div>
              <div className="font-semibold text-[var(--color-warning)]">{t("rebar.result.rerun", "Re-run the calculation so this steel reaches the BOQ.")}</div>
            </div>
          ) : null}

          {notice ? <pre className="whitespace-pre-wrap rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 font-sans text-[12px] text-[var(--color-danger)]">{notice}</pre> : null}

          {canImport ? (
            <div className="flex flex-wrap items-center gap-2 border-y border-[var(--color-border)] py-3">
              {editable ? (
                <>
                  <Button variant="secondary" size="sm" disabled={selected.size === 0 || bulk.isPending} onClick={() => runBulk("CONFIRMED")}>{t("rebar.acceptSelected", "Accept selected")} ({selected.size})</Button>
                  <Button variant="ghost" size="sm" disabled={selected.size === 0 || bulk.isPending} onClick={() => runBulk("REJECTED")}>{t("rebar.rejectSelected", "Reject selected")}</Button>
                  <div className="ml-auto flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => { setDlgError(null); setDlg("reject"); }}>{t("rebar.rejectImport", "Reject schedule")}</Button>
                    <Button variant="primary" size="sm" disabled={rows.length === 0 || counts.confirmed === 0}
                      title={counts.confirmed === 0 ? t("rebar.needConfirmed", "Accept at least one row first.") : undefined}
                      onClick={() => { setDlgError(null); setRejectPending(false); setDlg("confirm"); }}>{t("rebar.confirmImport", "Confirm schedule")}</Button>
                  </div>
                </>
              ) : imp.status === "CONFIRMED" ? (
                <div className="ml-auto"><Button variant="ghost" size="sm" onClick={() => { setDlgError(null); setDlg("archive"); }}>{t("rebar.archive", "Archive")}</Button></div>
              ) : null}
            </div>
          ) : null}

          {rows.length === 0 ? (
            <p className="py-6 text-center text-[12.5px] text-[var(--color-text-muted)]">{t("rebar.noRows", "This bar schedule has no rows.")}</p>
          ) : (
            <RebarRowsTable projectId={projectId} importId={imp.id} rows={rows} shapes={shapes} levels={levels} editable={editable}
              selected={selected} onToggle={toggle} onToggleAll={toggleAll} onNotice={setNotice} />
          )}
        </div>
      )}

      {dlg === "confirm" ? (
        <ConfirmDialog title={t("rebar.confirmTitle", "Confirm bar schedule")}
          description={t("rebar.confirmDesc", "Confirmed rows become bar marks on the next calculation run, and switch off the steel estimate for the members they cover.")}
          confirmLabel={confirm.isPending ? t("common.saving", "Saving…") : t("rebar.confirmImport", "Confirm schedule")} pending={confirm.isPending} error={dlgError}
          onConfirm={doConfirm} onClose={() => setDlg(null)}>
          {counts.pending > 0 ? (
            <label className="flex items-start gap-2 text-[12.5px] text-[var(--color-text-secondary)]">
              <input type="checkbox" className="mt-0.5" checked={rejectPending} onChange={(e) => setRejectPending(e.target.checked)} />
              {t("rebar.rejectRest", "Reject the {{n}} row(s) still pending. Otherwise confirming is blocked until they're reviewed.", { n: counts.pending })}
            </label>
          ) : null}
        </ConfirmDialog>
      ) : null}
      {dlg === "reject" ? (
        <ConfirmDialog title={t("rebar.rejectTitle", "Reject bar schedule")} confirmLabel={reject.isPending ? t("common.saving", "Saving…") : t("rebar.rejectImport", "Reject schedule")}
          pending={reject.isPending} error={dlgError} onConfirm={doReject} onClose={() => setDlg(null)}>
          <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("rebar.rejectBody", "None of its rows will be used. You can import the file again later.")}</p>
        </ConfirmDialog>
      ) : null}
      {dlg === "archive" ? (
        <ConfirmDialog title={t("rebar.archiveTitle", "Archive bar schedule")} confirmLabel={archive.isPending ? t("common.saving", "Saving…") : t("rebar.archive", "Archive")}
          pending={archive.isPending} error={dlgError} onConfirm={doArchive} onClose={() => setDlg(null)}>
          <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("rebar.archiveBody", "Its bar marks drop out of the next calculation run, and steel estimates return for the members it covered.")}</p>
        </ConfirmDialog>
      ) : null}
    </Modal>
  );
}

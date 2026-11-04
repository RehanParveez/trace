import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, LoadingState, Modal, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { FINDINGS_PAGE_SIZE } from "../api/bbs.api";
import { useBbsAuditRun, useBbsFindings, useDecideFinding, useRunBbsAudit, useRunBbsCrossCheck } from "../hooks/useBbs";
import { CLASS_ORDER, REASON_MAX, canDecide, classTone, kgLabel, readDiff, reasonProblem, sortedClassCounts, statusTone, whereLabel } from "../utils/bbsAudit";
import type { BbsDocumentSummary, Finding, FindingDecision } from "../types/bbsAudit.types";
import { BbsDiffPanel } from "./BbsDiffPanel";
import { basisLabel, conventionLabel, crossLine, drawingLabel } from "../utils/bbsCrosscheck";

interface BbsFindingsDialogProps {
  projectId: string;
  document: BbsDocumentSummary;
  canEdit: boolean;
  onClose: () => void;
}

const th = "px-3 py-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const STATUSES = ["OPEN", "ACCEPTED", "REJECTED", "SIGNED"] as const;
const select = "rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px]";

export function BbsFindingsDialog({ document, canEdit, onClose }: BbsFindingsDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [klass, setKlass] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [openId, setOpenId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const run = useBbsAuditRun(document.id);
  const findings = useBbsFindings(document.id, { finding_class: klass, status, page });
  const runAudit = useRunBbsAudit(document.id);
  const runCross = useRunBbsCrossCheck(document.id);
  const decide = useDecideFinding(document.id);
  const diff = readDiff(run.data);
  const data = findings.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / FINDINGS_PAGE_SIZE)) : 1;

  function startAudit() {
    setError(null);
    runAudit.mutate(undefined, {
      onSuccess: () => { setPage(1); showToast({ tone: "success", title: t("bbs.audit.done", "Audit finished") }); },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.audit.error", "Couldn't run the audit."))),
    });
  }

  function startCross() {
    setError(null);
    runCross.mutate(undefined, {
      onSuccess: () => { setPage(1); showToast({ tone: "success", title: t("bbs.cross.done", "Cross-check finished") }); },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.cross.error", "Couldn't run the cross-check."))),
    });
  }

  function submit(f: Finding, next: FindingDecision) {
    const problem = reasonProblem(reason);
    if (problem) { setError(t("bbs.reasonNeeded", "Give the reason for this decision (up to {{n}} characters).", { n: REASON_MAX })); return; }
    setError(null);
    decide.mutate({ findingId: f.id, status: next, reason: reason.trim() }, {
      onSuccess: () => { setReason(""); setOpenId(null); },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.decideError", "Couldn't save this decision."))),
    });
  }

  return (
    <Modal title={t("bbs.findings.title", "Bar schedule audit · version {{v}}", { v: document.version })} description={document.file_name ?? undefined} onClose={onClose} wide>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {run.data ? sortedClassCounts(run.data.totals.by_class).map(([c, n]) => <Badge key={c} tone={classTone(c)}>{c} {n}</Badge>) : null}
          {run.data ? <span className="text-[11.5px] text-[var(--color-text-muted)]">{t("bbs.audit.level", "Level {{l}} · rules {{d}}", { l: run.data.level, d: run.data.rules_digest.slice(0, 8) })}</span> : null}
          {canEdit ? (
            <div className="ml-auto flex gap-2">
              <Button variant="primary" size="sm" disabled={runAudit.isPending || runCross.isPending} onClick={startAudit}>
                {runAudit.isPending ? t("bbs.audit.running", "Running…") : run.data ? t("bbs.audit.rerun", "Run the audit again") : t("bbs.audit.run", "Run the audit")}
              </Button>
              <Button variant="secondary" size="sm" disabled={runAudit.isPending || runCross.isPending} onClick={startCross}>
                {runCross.isPending ? t("bbs.cross.running", "Checking…") : t("bbs.cross.run", "Run the cross-check")}
              </Button>
            </div>
          ) : null}
        </div>

        {run.data ? (
          <p className="font-mono text-[12px] text-[var(--color-text-secondary)]">
            {t("bbs.audit.totals", "printed {{p}} kg · rows {{r}} kg · round-up of fractional bars {{f}} kg", {
              p: run.data.totals.printed_total_kg ?? "—", r: run.data.totals.rows_total_kg ?? "—", f: run.data.totals.fractional_round_up_kg ?? "—" })}
          </p>
        ) : null}
        {run.data?.totals.crosscheck ? <p className="font-mono text-[12px] text-[var(--color-text-secondary)]">{crossLine(run.data.totals)}</p> : null}
        {diff ? <BbsDiffPanel diff={diff} /> : null}
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex flex-wrap gap-2 border-y border-[var(--color-border)] py-3">
          <select aria-label={t("bbs.filter.class", "Class")} className={select} value={klass} onChange={(e) => { setKlass(e.target.value); setPage(1); }}>
            <option value="">{t("bbs.filter.allClasses", "All classes")}</option>
            {CLASS_ORDER.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select aria-label={t("bbs.filter.status", "Status")} className={select} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="">{t("bbs.filter.allStatuses", "All statuses")}</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {data ? <span className="ml-auto self-center text-[12px] text-[var(--color-text-muted)]">{t("bbs.findings.count", "{{n}} finding(s)", { n: data.total })}</span> : null}
        </div>

        {findings.isLoading ? (
          <LoadingState label={t("bbs.findings.loading", "Loading findings…")} />
        ) : findings.isError ? (
          <ErrorState title={t("bbs.findings.error", "Couldn't load the findings")} onRetry={() => void findings.refetch()} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState icon="info" title={run.data ? t("bbs.findings.none", "No findings match") : t("bbs.findings.notRun", "The audit has not been run")}
            description={run.data ? t("bbs.findings.noneDesc", "Change the filters to see more findings.") : t("bbs.findings.notRunDesc", "Run the audit to check the arithmetic of this schedule.")} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left">
              <thead><tr>
                <th className={th}>{t("bbs.col.code", "Check")}</th>
                <th className={th}>{t("bbs.col.class", "Class")}</th>
                <th className={th}>{t("bbs.col.where", "Where")}</th>
                <th className={th}>{t("bbs.col.bbs", "Schedule")}</th>
                <th className={th}>{t("bbs.col.trace", "Trace")}</th>
                <th className={`${th} text-right`}>{t("bbs.col.kg", "kg")}</th>
                <th className={th}>{t("bbs.col.status", "Status")}</th>
              </tr></thead>
              <tbody>
                {data.items.map((f) => (
                  <FindingRows key={f.id} f={f} open={openId === f.id} canEdit={canEdit && canDecide(f)} reason={reason} pending={decide.isPending}
                    onToggle={() => { setOpenId(openId === f.id ? null : f.id); setReason(f.reason ?? ""); setError(null); }}
                    onReason={setReason} onDecide={(next) => submit(f, next)} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && pages > 1 ? (
          <div className="flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t("bbs.prev", "Previous")}</Button>
            <span className="text-[12px] text-[var(--color-text-muted)]">{page} / {pages}</span>
            <Button variant="ghost" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>{t("bbs.next", "Next")}</Button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

interface FindingRowsProps {
  f: Finding;
  open: boolean;
  canEdit: boolean;
  reason: string;
  pending: boolean;
  onToggle: () => void;
  onReason: (value: string) => void;
  onDecide: (next: FindingDecision) => void;
}

function FindingRows({ f, open, canEdit, reason, pending, onToggle, onReason, onDecide }: FindingRowsProps) {
  const { t } = useTranslation();
  return (
    <>
      <tr className="cursor-pointer border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]" onClick={onToggle}>
        <td className="px-3 py-2 font-mono text-[12px]">{f.code}</td>
        <td className="px-3 py-2"><Badge tone={classTone(f.finding_class)}>{f.finding_class}</Badge></td>
        <td className="px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">{whereLabel(f.bbs_ref)}</td>
        <td className="px-3 py-2 font-mono text-[12px]">{f.bbs_value ?? "—"}</td>
        <td className="px-3 py-2 font-mono text-[12px]">{f.trace_value ?? "—"}</td>
        <td className="px-3 py-2 text-right font-mono text-[12px]">{kgLabel(f.diff_kg)}</td>
        <td className="px-3 py-2"><Badge tone={statusTone(f.status)}>{f.status}</Badge></td>
      </tr>
      {open ? (
        <tr className="bg-[var(--color-surface-muted)]">
          <td colSpan={7} className="space-y-2 px-4 py-3">
            <div className="text-[12px] text-[var(--color-text-secondary)]">{f.rule}</div>
            {f.question ? <div className="text-[12px] font-semibold text-[var(--color-warning)]">{f.question}</div> : null}
            {f.effect_basis || f.drawing_ref || f.convention ? (
              <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11.5px] text-[var(--color-text-muted)]">
                {f.effect_basis ? <span>{basisLabel(f)}</span> : null}
                {f.drawing_ref ? <span>{drawingLabel(f.drawing_ref)}</span> : null}
                {f.convention ? <span>{conventionLabel(f.convention)}</span> : null}
              </div>
            ) : null}
            {f.reason ? <div className="text-[12px] italic text-[var(--color-text-muted)]">{t("bbs.reasonWas", "Reason given")}: {f.reason}</div> : null}
            {canEdit ? (
              <div className="flex flex-wrap items-start gap-2" onClick={(e) => e.stopPropagation()}>
                <textarea aria-label={t("bbs.reason", "Reason")} className="min-h-[56px] min-w-[260px] flex-1 rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] p-2 text-[12px]"
                  placeholder={t("bbs.reasonPlaceholder", "Why? (required)")} maxLength={REASON_MAX} value={reason} onChange={(e) => onReason(e.target.value)} />
                <Button variant="secondary" size="sm" disabled={pending} onClick={() => onDecide("ACCEPTED")}>{t("bbs.accept", "Accept")}</Button>
                <Button variant="ghost" size="sm" disabled={pending} onClick={() => onDecide("REJECTED")}>{t("bbs.reject", "Reject")}</Button>
                {f.status !== "OPEN" ? <Button variant="ghost" size="sm" disabled={pending} onClick={() => onDecide("OPEN")}>{t("bbs.reopen", "Reopen")}</Button> : null}
              </div>
            ) : null}
          </td>
        </tr>
      ) : null}
    </>
  );
}

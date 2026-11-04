import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, ErrorState, LoadingState, Modal, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { bbsReportApi } from "../api/bbsReport.api";
import { useBbsAuditRun, useRunBbsCrossCheck } from "../hooks/useBbs";
import { useReportQuestions, useReportSummary } from "../hooks/useBbsReport";
import { copyText, exportName, saveBlob, totalsLine } from "../utils/bbsReport";
import { crossLine } from "../utils/bbsCrosscheck";
import type { BbsDocumentSummary } from "../types/bbsAudit.types";
import type { ReportFilters } from "../types/bbsReport.types";
import { AuditSummary } from "./AuditSummary";
import { FindingList } from "./FindingList";
import { QuestionsPanel } from "./QuestionsPanel";
import { SheetTable } from "./SheetTable";
import { VersionDiff } from "./VersionDiff";

type Tab = "summary" | "findings" | "questions" | "changes";

interface BbsAuditScreenProps {
  projectId: string;
  document: BbsDocumentSummary;
  canEdit: boolean;
  onClose: () => void;
}

export function BbsAuditScreen({ document, canEdit, onClose }: BbsAuditScreenProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [tab, setTab] = useState<Tab>("summary");
  const [filters, setFilters] = useState<ReportFilters>({ page: 1 });
  const [copied, setCopied] = useState<number | "all" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const summary = useReportSummary(document.id);
  const questions = useReportQuestions(document.id);
  const run = useBbsAuditRun(document.id);
  const cross = useRunBbsCrossCheck(document.id);
  const s = summary.data;

  function startCross() {
    setError(null);
    cross.mutate(undefined, {
      onSuccess: () => { setFilters({ ...filters, page: 1 }); showToast({ tone: "success", title: t("bbs.cross.done", "Cross-check finished") }); },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.cross.error", "Couldn't run the cross-check."))),
    });
  }

  async function exportXlsx() {
    setError(null);
    setBusy(true);
    try {
      saveBlob(await bbsReportApi.xlsx(document.id), exportName(document.version, "xlsx"));
    } catch (e) {
      setError(getApiErrorMessage(e, t("bbs.export.error", "Couldn't make the export.")));
    } finally {
      setBusy(false);
    }
  }

  async function copySummary() {
    setError(null);
    setBusy(true);
    try {
      const ok = await copyText(await bbsReportApi.markdown(document.id));
      showToast({ tone: ok ? "success" : "error", title: ok ? t("bbs.export.copied", "Summary copied as markdown") : t("bbs.export.copyFailed", "The browser did not allow copying") });
    } catch (e) {
      setError(getApiErrorMessage(e, t("bbs.export.error", "Couldn't make the export.")));
    } finally {
      setBusy(false);
    }
  }

  async function copyQuestions(which: number | "all") {
    const list = questions.data;
    if (!list) return;
    const text = which === "all" ? list.text : list.items.find((q) => q.no === which)?.text ?? "";
    if (text && await copyText(text)) {
      setCopied(which);
      setTimeout(() => setCopied(null), 1500);
    }
  }

  const tabs: Array<[Tab, string]> = [
    ["summary", t("bbs.tab.summary", "Summary")],
    ["findings", t("bbs.tab.findings", "Findings")],
    ["questions", t("bbs.tab.questions", "Questions {{n}}", { n: s?.open_questions ?? 0 })],
    ["changes", t("bbs.tab.changes", "Changes")],
  ];

  return (
    <Modal title={t("bbs.screen.title", "Audit of bar schedule version {{v}}", { v: document.version })} description={document.file_name ?? undefined} onClose={onClose} wide>
      <div className="space-y-4" data-testid="bbs-audit-screen">
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" className="flex gap-1">
            {tabs.map(([id, text]) => (
              <Button key={id} variant={tab === id ? "primary" : "ghost"} size="sm" onClick={() => setTab(id)}>{text}</Button>
            ))}
          </div>
          <div className="ml-auto flex flex-wrap gap-2">
            {canEdit ? <Button variant="secondary" size="sm" disabled={cross.isPending} onClick={startCross}>{cross.isPending ? t("bbs.cross.running", "Checking…") : s?.has_run ? t("bbs.cross.rerun", "Run the cross-check again") : t("bbs.cross.run", "Run the cross-check")}</Button> : null}
            <Button variant="ghost" size="sm" disabled={busy || !s?.has_run} onClick={() => void copySummary()}>{t("bbs.export.md", "Copy summary")}</Button>
            <Button variant="ghost" size="sm" disabled={busy || !s?.has_run} onClick={() => void exportXlsx()}>{t("bbs.export.xlsx", "Download xlsx")}</Button>
          </div>
        </div>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        {summary.isLoading ? <LoadingState label={t("bbs.report.loading", "Loading the audit…")} /> : summary.isError || !s ? (
          <ErrorState title={t("bbs.report.error", "Couldn't load the audit")} onRetry={() => void summary.refetch()} />
        ) : tab === "summary" ? (
          <div className="space-y-4">
            <p className="font-mono text-[12.5px] text-[var(--color-text-primary)]">{totalsLine(s)}</p>
            <AuditSummary summary={s} />
            {run.data?.totals.crosscheck ? <p className="font-mono text-[11.5px] text-[var(--color-text-muted)]">{crossLine(run.data.totals)}</p> : null}
            <SheetTable sheets={s.sheets} unassigned={s.unassigned} selected={filters.sheet ?? null}
              onSelect={(idx) => { setFilters({ ...filters, sheet: idx, page: 1 }); if (idx !== null) setTab("findings"); }} />
          </div>
        ) : tab === "findings" ? (
          <FindingList documentId={document.id} canEdit={canEdit} sheets={s.sheets} filters={filters} onFilters={setFilters} />
        ) : tab === "questions" ? (
          questions.isLoading ? <LoadingState label={t("bbs.questions.loading", "Loading the questions…")} /> : (
            <QuestionsPanel items={questions.data?.items ?? []} copied={copied} onCopy={(w) => void copyQuestions(w)} />
          )
        ) : (
          <VersionDiff run={run.data} version={document.version} />
        )}
      </div>
    </Modal>
  );
}

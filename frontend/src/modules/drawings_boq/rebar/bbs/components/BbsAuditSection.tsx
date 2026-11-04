import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, ErrorState, LoadingState, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { useBbsDocuments, useUploadBbs } from "../hooks/useBbs";
import { BBS_FILE_MAX_BYTES } from "../utils/bbsAudit";
import type { BbsDocumentSummary } from "../types/bbsAudit.types";
import { BbsFindingsDialog } from "./BbsFindingsDialog";
import { BbsMatchDialog } from "./BbsMatchDialog";
import { BbsExpectDialog } from "./BbsExpectDialog";
import { BbsAuditScreen } from "./BbsAuditScreen";

interface BbsAuditSectionProps {
  projectId: string;
  canImport: boolean;
}

const th = "px-3 py-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function BbsAuditSection({ projectId, canImport }: BbsAuditSectionProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const query = useBbsDocuments(projectId);
  const upload = useUploadBbs(projectId);
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<BbsDocumentSummary | null>(null);
  const [matching, setMatching] = useState<BbsDocumentSummary | null>(null);
  const [expecting, setExpecting] = useState<BbsDocumentSummary | null>(null);
  const [reviewing, setReviewing] = useState<BbsDocumentSummary | null>(null);
  const docs = query.data ?? [];

  function onPick(file: File | undefined) {
    if (!file) return;
    setError(null);
    if (!file.name.toLowerCase().endsWith(".pdf")) { setError(t("bbs.notPdf", "Choose the bar bending schedule as a PDF.")); return; }
    if (file.size > BBS_FILE_MAX_BYTES) { setError(t("bbs.tooBig", "The file is larger than 25 MB.")); return; }
    upload.mutate(file, {
      onSuccess: (r) => {
        showToast({ tone: "success", title: t("bbs.uploaded", "Version {{v}} uploaded", { v: r.document.version }),
          description: t("bbs.uploadedDesc", "{{rows}} rows on {{sheets}} sheets read.", { rows: r.document.row_count, sheets: r.document.sheet_count }) });
        setOpen(r.document);
      },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.uploadError", "Couldn't read this bar bending schedule."))),
    });
    if (input.current) input.current.value = "";
  }

  return (
    <section className="space-y-3 border-t border-[var(--color-border)] p-4" data-testid="bbs-audit-section">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{t("bbs.title", "Bar schedule audit")}</div>
          <div className="text-[12px] text-[var(--color-text-muted)]">{t("bbs.description", "Upload the QS's bar bending schedule PDF. Every version is kept, and the audit checks its arithmetic.")}</div>
        </div>
        {canImport ? (
          <div className="ml-auto">
            <input ref={input} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(e) => onPick(e.target.files?.[0])} />
            <Button variant="secondary" size="sm" disabled={upload.isPending} onClick={() => input.current?.click()}>
              {upload.isPending ? t("bbs.reading", "Reading…") : t("bbs.upload", "Upload schedule PDF")}
            </Button>
          </div>
        ) : null}
      </div>
      {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

      {query.isLoading ? (
        <LoadingState label={t("bbs.loading", "Loading versions…")} />
      ) : query.isError ? (
        <ErrorState title={t("bbs.loadError", "Couldn't load the schedule versions")} onRetry={() => void query.refetch()} />
      ) : docs.length === 0 ? (
        <p className="text-[12.5px] text-[var(--color-text-muted)]">{t("bbs.none", "No bar bending schedule has been uploaded.")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left">
            <thead><tr>
              <th className={th}>{t("bbs.col.version", "Version")}</th>
              <th className={th}>{t("bbs.col.file", "File")}</th>
              <th className={`${th} text-right`}>{t("bbs.col.rows", "Rows")}</th>
              <th className={`${th} text-right`}>{t("bbs.col.sheets", "Sheets")}</th>
              <th className={th}>{t("bbs.col.uploaded", "Uploaded")}</th>
              <th className={`${th} text-right`}>{t("bbs.col.actions", "Actions")}</th>
            </tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-t border-[var(--color-border)]">
                  <td className="px-3 py-2.5"><Badge tone={d.status === "ACTIVE" ? "green" : "blue"}>v{d.version}</Badge></td>
                  <td className="px-3 py-2.5 text-[12.5px] text-[var(--color-text-primary)]">{d.file_name ?? "—"}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-[12px]">{d.row_count}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-[12px]">{d.sheet_count}</td>
                  <td className="px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">{d.created_at.slice(0, 10)}</td>
                  <td className="px-3 py-2.5 text-right"><Button variant="ghost" size="sm" onClick={() => setReviewing(d)}>{t("bbs.review.open", "Review")}</Button>
                    <Button variant="ghost" size="sm" onClick={() => setOpen(d)}>{t("bbs.audit.open", "Audit")}</Button>
                    <Button variant="ghost" size="sm" onClick={() => setMatching(d)}>{t("bbs.match.open", "Match")}</Button>
                    <Button variant="ghost" size="sm" onClick={() => setExpecting(d)}>{t("bbs.expect.open", "Expected")}</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open ? <BbsFindingsDialog projectId={projectId} document={open} canEdit={canImport} onClose={() => setOpen(null)} /> : null}
      {matching ? <BbsMatchDialog projectId={projectId} document={matching} canEdit={canImport} onClose={() => setMatching(null)} /> : null}
      {expecting ? <BbsExpectDialog projectId={projectId} document={expecting} canEdit={canImport} onClose={() => setExpecting(null)} /> : null}
      {reviewing ? <BbsAuditScreen projectId={projectId} document={reviewing} canEdit={canImport} onClose={() => setReviewing(null)} /> : null}
    </section>
  );
}

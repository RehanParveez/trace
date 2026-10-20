import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, LoadingState, PageHeader, Panel, PanelHeader, StatCard, TableShell } from "../../../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../../../identity";
import { PRICING_PERMISSIONS } from "../../permissions";
import { formatDate, RATE_BOOKS_PATH } from "../../utils/pricing.utils";
import { ScheduleUploadDialog } from "../components/ScheduleUploadDialog";
import { useRateImports } from "../hooks/useSchedules";
import type { ImportStatus } from "../types/schedules.types";
import { IMPORT_STATUS_LABEL, formatBytes, importStatusTone, rateImportPath } from "../utils/schedules.utils";

const STATUSES: ImportStatus[] = ["REVIEW", "UPLOADED", "PARSING", "PUBLISHED", "FAILED"];

export function RateImportsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(PRICING_PERMISSIONS.DRAWING_READ);
  const canManage = permissions.includes(PRICING_PERMISSIONS.RATEBOOK_MANAGE);
  const [status, setStatus] = useState<ImportStatus | "">("");
  const [uploading, setUploading] = useState(false);

  const query = useRateImports(status || null);
  const all = useRateImports(null);

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("schedules.unavailable", "Schedule imports unavailable")} description={t("pricing.noPermission", "You don't have permission to view this.")} />;
  }
  if (query.isLoading) return <LoadingState label={t("schedules.loading", "Loading schedule imports…")} />;
  if (query.isError) return <ErrorState title={t("schedules.loadError", "We couldn't load schedule imports")} onRetry={() => void query.refetch()} />;

  const inReview = all.imports.filter((i) => i.status === "REVIEW").length;
  const loaded = all.imports.filter((i) => i.status === "PUBLISHED").length;
  const failed = all.imports.filter((i) => i.status === "FAILED").length;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={t("pricing.eyebrow", "PRICING")}
        title={t("schedules.title", "Schedule imports")}
        description={t(
          "schedules.desc",
          "Load a schedule of rates (a PDF or CSV from a government schedule, a QS firm or a supplier) into a rate book. Each file is read, checked automatically, then reviewed and mapped to your work items before it becomes a draft rate book.",
        )}
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={() => navigate(RATE_BOOKS_PATH)}>{t("schedules.toBooks", "Rate books")}</Button>
            {canManage ? <Button variant="primary" size="sm" onClick={() => setUploading(true)}>{t("schedules.upload.open", "Upload schedule")}</Button> : null}
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label={t("schedules.statReview", "Waiting for review")} value={inReview} note={t("schedules.statReviewNote", "Read and checked")} icon="alert" tone={inReview > 0 ? "gold" : "blue"} />
        <StatCard label={t("schedules.statLoaded", "Loaded into books")} value={loaded} note={t("schedules.statLoadedNote", "Became draft rate books")} icon="check" tone="green" />
        <StatCard label={t("schedules.statFailed", "Could not be read")} value={failed} note={t("schedules.statFailedNote", "Try another layout or page range")} icon="alert" tone={failed > 0 ? "gold" : "blue"} />
      </div>

      <Panel>
        <PanelHeader eyebrow={t("schedules.eyebrow", "IMPORTS")} title={t("schedules.listTitle", "Uploaded schedules")} />
        <div className="flex flex-wrap gap-3 border-b border-[var(--color-border)] p-4">
          <label className="flex items-center gap-2 text-[12px] text-[var(--color-text-secondary)]">
            {t("schedules.status", "Status")}
            <select
              className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
              value={status}
              onChange={(e) => setStatus(e.target.value as ImportStatus | "")}
            >
              <option value="">{t("schedules.statusAll", "Any status")}</option>
              {STATUSES.map((s) => <option key={s} value={s}>{t(`schedules.status.${s}`, IMPORT_STATUS_LABEL[s])}</option>)}
            </select>
          </label>
        </div>
        {query.imports.length === 0 ? (
          <EmptyState
            icon="budget"
            title={t("schedules.emptyTitle", "No schedules uploaded yet")}
            description={t("schedules.emptyDesc", "Upload a PDF or CSV of rates to start. You review every flagged row before anything becomes a rate.")}
            action={canManage ? <Button variant="primary" onClick={() => setUploading(true)}>{t("schedules.upload.open", "Upload schedule")}</Button> : undefined}
          />
        ) : (
          <TableShell>
            <table className="w-full min-w-[760px] text-left text-[13px]">
              <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-4 py-2.5">{t("schedules.col.file", "File")}</th>
                  <th className="px-4 py-2.5">{t("schedules.col.status", "Status")}</th>
                  <th className="px-4 py-2.5 text-right">{t("schedules.col.rows", "Rows")}</th>
                  <th className="px-4 py-2.5 text-right">{t("schedules.col.review", "To review")}</th>
                  <th className="px-4 py-2.5">{t("schedules.col.uploaded", "Uploaded")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {query.imports.map((imp) => (
                  <tr key={imp.id} className="cursor-pointer hover:bg-[var(--color-surface-muted)]" onClick={() => navigate(rateImportPath(imp.id))}>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-[var(--color-text-primary)]">{imp.book_name || imp.filename}</div>
                      <div className="text-[11.5px] text-[var(--color-text-muted)]">{imp.filename} · {imp.source_kind} · {formatBytes(imp.file_size)}{imp.edition ? ` · ${imp.edition}` : ""}</div>
                    </td>
                    <td className="px-4 py-3"><Badge tone={importStatusTone(imp.status)}>{t(`schedules.status.${imp.status}`, IMPORT_STATUS_LABEL[imp.status])}</Badge></td>
                    <td className="px-4 py-3 text-right">{imp.row_count || "—"}</td>
                    <td className="px-4 py-3 text-right">{imp.status === "REVIEW" ? imp.counts.to_review ?? "—" : "—"}</td>
                    <td className="px-4 py-3">{formatDate(imp.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
        {query.hasNextPage ? (
          <div className="flex justify-center border-t border-[var(--color-border)] p-3">
            <Button variant="secondary" size="sm" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>{t("common.loadMore", "Load more")}</Button>
          </div>
        ) : null}
      </Panel>

      {uploading ? <ScheduleUploadDialog onClose={() => setUploading(false)} /> : null}
    </div>
  );
}

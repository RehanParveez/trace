import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, Icon, LoadingState, Panel, PanelHeader, TableShell } from "../../../organizations/components/OrganizationUi";
import { useRebarImports } from "../hooks/useRebar";
import { importTone } from "../../utils/drawings-boq.utils";
import type { Drawing, ScheduleImportResponse } from "../../types/drawings-boq.types";
import { RebarImportDialog } from "./RebarImportDialog";
import { RebarReviewDialog } from "./RebarReviewDialog";

interface RebarImportsPanelProps {
  projectId: string;
  drawings: Drawing[];
  canImport: boolean;
}

const th = "px-4 py-3 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const STATUSES = ["", "PENDING_REVIEW", "CONFIRMED", "REJECTED", "ARCHIVED"] as const;

export function RebarImportsPanel({ projectId, drawings, canImport }: RebarImportsPanelProps) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<string>("");
  const query = useRebarImports(projectId, status || undefined);
  const [importing, setImporting] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [open, setOpen] = useState<ScheduleImportResponse | null>(null);
  const rows = query.data ?? [];

  // Keep the dialog on the latest copy of the import, and keep it open even if a status filter hides it after confirm.
  useEffect(() => {
    if (!openId) { setOpen(null); return; }
    const found = query.data?.find((r) => r.id === openId);
    if (found) setOpen(found);
  }, [openId, query.data]);

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("rebar.eyebrow", "Reinforcement")}
        title={t("rebar.title", "Bar bending schedules")}
        description={t("rebar.description", "Import the structural bar schedule, check each row, then confirm. Confirmed bars replace the steel estimate for the members they cover on the next calculation run.")}
        action={canImport ? <Button variant="primary" size="sm" onClick={() => setImporting(true)}><Icon name="plus" size={13} />{t("rebar.importButton", "Import bar schedule")}</Button> : null}
      />
      <div className="flex flex-wrap gap-2 border-b border-[var(--color-border)] p-4">
        {STATUSES.map((s) => (
          <button key={s || "all"} type="button" onClick={() => setStatus(s)}
            className={`rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${status === s ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]" : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"}`}>
            {s ? s.replace("_", " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase()) : t("rebar.all", "All")}
          </button>
        ))}
      </div>

      {query.isLoading ? (
        <LoadingState label={t("rebar.loading", "Loading bar schedules…")} />
      ) : query.isError ? (
        <ErrorState title={t("rebar.loadError", "Couldn't load bar schedules")} onRetry={() => void query.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState icon="info" title={t("rebar.emptyTitle", "No bar schedules")}
          description={t("rebar.emptyDesc", "Without a bar schedule, steel is estimated from concrete volume and marked for review.")}
          action={canImport ? <Button variant="primary" size="sm" onClick={() => setImporting(true)}>{t("rebar.importButton", "Import bar schedule")}</Button> : undefined} />
      ) : (
        <TableShell>
          <table className="w-full min-w-[720px] text-left">
            <thead className="bg-[var(--color-surface-muted)]"><tr>
              <th className={th}>{t("rebar.colFile", "File")}</th>
              <th className={th}>{t("rebar.colStatus", "Status")}</th>
              <th className={`${th} text-right`}>{t("rebar.colRows", "Rows")}</th>
              <th className={`${th} text-right`}>{t("rebar.colConfirmed", "Confirmed")}</th>
              <th className={th}>{t("rebar.colImported", "Imported")}</th>
              <th className={`${th} text-right`}>{t("rebar.colActions", "Actions")}</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-3.5">
                    <button type="button" className="text-left" onClick={() => setOpenId(r.id)}>
                      <span className="block truncate text-[13.5px] font-semibold text-[var(--color-text-primary)]">{r.file_name ?? t("rebar.untitled", "Bar schedule")}</span>
                      <span className="text-[11.5px] text-[var(--color-text-muted)]">{r.source}</span>
                    </button>
                  </td>
                  <td className="px-4 py-3.5"><Badge tone={importTone(r.status)}>{r.status}</Badge></td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">{r.row_count}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">{r.confirmed_count}</td>
                  <td className="px-4 py-3.5 text-[12px] text-[var(--color-text-secondary)]">{r.created_at.slice(0, 10)}</td>
                  <td className="px-4 py-3.5 text-right">
                    <Button variant="ghost" size="sm" onClick={() => setOpenId(r.id)}>
                      {r.status === "PENDING_REVIEW" && canImport ? t("rebar.review", "Review") : t("common.open", "Open")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}

      {importing ? (
        <RebarImportDialog projectId={projectId} drawings={drawings} onClose={() => setImporting(false)}
          onCreated={(imp) => { setStatus(""); setOpenId(imp.schedule_import_id); }} />
      ) : null}
      {open ? <RebarReviewDialog projectId={projectId} imp={open} drawings={drawings} canImport={canImport} onClose={() => setOpenId(null)} /> : null}
    </Panel>
  );
}

import { useState } from "react";
import { Badge, Button, EmptyState, ErrorState, Icon, LoadingState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import { useScheduleImports } from "../hooks/useSpacesSchedules";
import { importTone } from "../utils/drawings-boq.utils";
import type { Drawing } from "../types/drawings-boq.types";
import { ScheduleImportDialog } from "./ScheduleImportDialog";
import { ScheduleReviewDialog } from "./ScheduleReviewDialog";
import { useTranslation } from "react-i18next";

interface ScheduleImportsPanelProps {
  projectId: string;
  drawings: Drawing[];
  canImport: boolean;
  canManageSpaces: boolean;
}

const th = "px-4 py-3 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const STATUSES = ["", "PENDING_REVIEW", "CONFIRMED", "REJECTED", "ARCHIVED"] as const;

export function ScheduleImportsPanel({ projectId, drawings, canImport, canManageSpaces }: ScheduleImportsPanelProps) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<string>("");
  const query = useScheduleImports(projectId, status || undefined);
  const [importing, setImporting] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const rows = query.data ?? [];

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("schedules.eyebrow", "Schedules")}
        title={t("schedules.title", "Door, window and finish schedules")}
        description={t("schedules.description", "Import a schedule, review each row, then confirm. Confirmed finish rows set room finishes; the rest become ledger lines.")}
        action={canImport ? <Button variant="primary" size="sm" onClick={() => setImporting(true)}><Icon name="plus" size={13} />{t("schedules.import.button", "Import schedule")}</Button> : null}
      />
      <div className="flex flex-wrap gap-2 border-b border-[var(--color-border)] p-4">
        {STATUSES.map((s) => (
          <button key={s || "all"} type="button" onClick={() => setStatus(s)}
            className={`rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${status === s ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]" : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"}`}>
            {s ? s.replace("_", " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase()) : t("schedules.all", "All")}
          </button>
        ))}
      </div>

      {query.isLoading ? (
        <LoadingState label={t("schedules.loading", "Loading schedules…")} />
      ) : query.isError ? (
        <ErrorState title={t("schedules.loadError", "Couldn't load schedules")} onRetry={() => void query.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState icon="info" title={t("schedules.emptyTitle", "No schedules")} description={t("schedules.emptyDesc", "Import a CSV, Excel or PDF schedule to start.")}
          action={canImport ? <Button variant="primary" size="sm" onClick={() => setImporting(true)}>{t("schedules.import.button", "Import schedule")}</Button> : undefined} />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]"><tr>
              <th className={th}>{t("schedules.colSource", "Source")}</th><th className={th}>{t("schedules.colKind", "Type")}</th><th className={th}>{t("schedules.colStatus", "Status")}</th>
              <th className={`${th} text-right`}>{t("schedules.colRows", "Rows")}</th><th className={`${th} text-right`}>{t("schedules.colConfirmed", "Confirmed")}</th>
              <th className={th}>{t("schedules.colCreated", "Imported")}</th><th className={`${th} text-right`}>{t("schedules.colActions", "Actions")}</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-3.5">
                    <button type="button" className="text-left" onClick={() => setOpenId(r.id)}>
                      <span className="block truncate text-[13.5px] font-semibold text-[var(--color-text-primary)]">{r.file_name ?? t("schedules.manualName", "Manual schedule")}</span>
                      <span className="text-[11.5px] text-[var(--color-text-muted)]">{r.source}</span>
                    </button>
                  </td>
                  <td className="px-4 py-3.5 text-[12.5px]">{r.schedule_kind}</td>
                  <td className="px-4 py-3.5"><Badge tone={importTone(r.status)}>{r.status}</Badge></td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">{r.row_count}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">{r.confirmed_count}</td>
                  <td className="px-4 py-3.5 text-[12px] text-[var(--color-text-secondary)]">{r.created_at.slice(0, 10)}</td>
                  <td className="px-4 py-3.5 text-right"><Button variant="ghost" size="sm" onClick={() => setOpenId(r.id)}>{r.status === "PENDING_REVIEW" && canImport ? t("schedules.review", "Review") : t("common.open", "Open")}</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}

      {importing ? <ScheduleImportDialog projectId={projectId} drawings={drawings} onClose={() => setImporting(false)} onCreated={(imp) => setOpenId(imp.id)} /> : null}
      {openId ? <ScheduleReviewDialog projectId={projectId} importId={openId} drawings={drawings} canImport={canImport} canManageSpaces={canManageSpaces} onClose={() => setOpenId(null)} /> : null}
    </Panel>
  );
}
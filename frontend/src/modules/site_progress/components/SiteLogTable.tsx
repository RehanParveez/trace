import { Button, EmptyState, Icon, Panel, PanelHeader, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import type { SiteLogEntry } from "../types/site-progress.types";
import { formatLogDate } from "../utils/site-progress.utils";
import { useDeleteSiteLog } from "../hooks";
import { useTranslation } from "react-i18next";

interface SiteLogTableProps {
  logs: SiteLogEntry[];
  canCreate: boolean;
  canManage: boolean;
  onCreate: () => void;
}

export function SiteLogTable({ logs, canCreate, canManage, onCreate }: SiteLogTableProps) {
  const { t } = useTranslation();
  const deleteLog = useDeleteSiteLog();
  const { showToast } = useToast();

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("siteProgress.table.eyebrow")}
        title={t("siteProgress.table.title")}
        description={t("siteProgress.table.description")}
        action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />{t("siteProgress.table.new")}</Button> : null}
      />

      {logs.length === 0 ? (
        <EmptyState
          icon="site"
          title={t("siteProgress.table.emptyTitle")}
          description={t("siteProgress.table.emptyDesc")}
          action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>{t("siteProgress.table.new")}</Button> : undefined}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[680px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("siteProgress.table.colDate")}</th>
                <th className="px-4 py-3">{t("siteProgress.table.colWorkforce")}</th>
                <th className="px-4 py-3">{t("siteProgress.table.colWeather")}</th>
                <th className="px-4 py-3">{t("siteProgress.table.colBlockers")}</th>
                <th className="px-4 py-3">{t("siteProgress.table.colNotes")}</th>
                {canManage ? <th className="px-4 py-3 text-right">{t("siteProgress.table.colActions")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-3.5 text-[13px] font-semibold text-[var(--color-text-primary)]">{formatLogDate(log.log_date)}</td>
                  <td className="px-4 py-3.5 font-mono text-[12.5px] text-[var(--color-text-secondary)]">{log.workforce_count ?? "—"}</td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{log.weather ?? "—"}</td>
                  <td className="px-4 py-3.5 max-w-[220px] truncate text-[12.5px] text-[var(--color-text-secondary)]">{log.blockers ?? "—"}</td>
                  <td className="px-4 py-3.5 max-w-[260px] truncate text-[12.5px] text-[var(--color-text-secondary)]">{log.notes ?? "—"}</td>
                  {canManage ? (
                    <td className="px-4 py-3.5 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deleteLog.isPending}
                        onClick={() => {
                          if (window.confirm(t("siteProgress.table.deleteConfirm"))) {
                            deleteLog.mutate(log.id, {
                              onSuccess: () => showToast({ tone: "success", title: t("siteProgress.table.deleted") }),
                              onError: (error) =>
                                showToast({
                                  tone: "error",
                                  title: t("siteProgress.table.deleteError"),
                                  description: getApiErrorMessage(error, t("common.retry")),
                                }),
                            });
                          }
                        }}
                      >
                        {t("common.delete")}
                      </Button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
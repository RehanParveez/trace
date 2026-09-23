import { useState } from "react";
import {Button, EmptyState, LoadingState, Panel, PanelHeader, StatCard, TableShell,
} from "../../organizations/components/OrganizationUi";
import { useProjectRetentionSummary } from "../hooks";
import { RetentionReleaseForm } from "./RetentionReleaseForm";
import { formatRetentionMoney } from "../utils/retention.utils";
import { useTranslation } from "react-i18next";

export function ProjectRetentionPanel({ projectId, canManage }: { projectId: string; canManage: boolean }) {
  const { t } = useTranslation();
  const summaryQuery = useProjectRetentionSummary(projectId);
  const [formOpen, setFormOpen] = useState(false);
  const summary = summaryQuery.data;

  if (summaryQuery.isLoading) {
    return <LoadingState label={t("retention.loading")} />;
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label={t("retention.page.accessUnavailable")} value={summary ? formatRetentionMoney(summary.client_total_outstanding, summary.currency) : "—"} note={t("retention.stat.clientNote")} icon="budget" tone="gold" />
        <StatCard label={t("retention.stat.subcontractorOutstanding")} value={summary ? formatRetentionMoney(summary.subcontractor_total_outstanding, summary.currency) : "—"} note={t("retention.stat.subcontractorNote")} icon="procurement" tone="gold" />
      </div>

      <Panel>
        <PanelHeader eyebrow={t("retention.client.eyebrow")} title={t("retention.client.title")} description={t("retention.client.description")} action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>{t("retention.client.recordRelease")}</Button> : null} />
        {(summary?.client_lines ?? []).length === 0 ? (
          <EmptyState icon="budget" title={t("retention.client.emptyTitle")} description={t("retention.client.emptyDesc")} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("retention.client.colBoqVersion")}</th><th className="px-4 py-3 text-right">{t("retention.common.colHeld")}</th><th className="px-4 py-3 text-right">{t("retention.common.colReleased")}</th><th className="px-4 py-3 text-right">{t("retention.common.colOutstanding")}</th></tr></thead>
              <tbody>
                {(summary?.client_lines ?? []).map((line) => (
                  <tr key={line.boq_version_id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{line.boq_version_label}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{formatRetentionMoney(line.retention_held, summary!.currency)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{formatRetentionMoney(line.retention_released, summary!.currency)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatRetentionMoney(line.retention_outstanding, summary!.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      <Panel>
        <PanelHeader eyebrow={t("retention.subcontractor.eyebrow")} title={t("retention.subcontractor.title")} description={t("retention.subcontractor.description")}/>
        {(summary?.subcontractor_lines ?? []).length === 0 ? (
          <EmptyState icon="procurement" title={t("retention.subcontractor.emptyTitle")} description={t("retention.subcontractor.emptyDesc")} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("retention.subcontractor.colSubcontractor")}</th><th className="px-4 py-3 text-right">{t("retention.common.colHeld")}</th><th className="px-4 py-3 text-right">{t("retention.common.colReleased")}</th><th className="px-4 py-3 text-right">{t("retention.common.colOutstanding")}</th></tr></thead>
              <tbody>
                {(summary?.subcontractor_lines ?? []).map((line) => (
                  <tr key={line.agreement_id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{line.subcontractor_name}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{formatRetentionMoney(line.retention_held, summary!.currency)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-secondary)]">{formatRetentionMoney(line.retention_released, summary!.currency)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatRetentionMoney(line.retention_outstanding, summary!.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      {formOpen ? <RetentionReleaseForm projectId={projectId} onClose={() => setFormOpen(false)} /> : null}
    </div>
  );
}
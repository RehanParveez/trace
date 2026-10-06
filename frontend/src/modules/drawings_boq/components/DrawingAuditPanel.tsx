import { useTranslation } from "react-i18next";
import {Badge, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, TableShell,
} from "../../organizations/components/OrganizationUi";
import { useDrawingAudit } from "../hooks";
import { formatDateTime, formatQuantity } from "../utils/drawings-boq.utils";

interface DrawingAuditPanelProps {
  drawingId: string;
  drawing?: {
    format?: string;
    status?: string;
    original_filename?: string;
  };
}

const severityTone = (s: string): "red" | "gold" | "slate" =>
  s === "error" ? "red" : s === "warning" ? "gold" : "slate";

const severityRank = (s: string) =>
  s === "error" ? 0 : s === "warning" ? 1 : 2;

export function DrawingAuditPanel({ drawingId, drawing }: DrawingAuditPanelProps) {
  const { t } = useTranslation();
  const query = useDrawingAudit(drawingId);
  const audit = query.data;

  if (drawing?.format && drawing.format !== "IFC") {
    return null;
  }

  if (query.isLoading) {
    return (
      <Panel>
        <LoadingState label={t("drawings.audit.loading")} />
      </Panel>
    );
  }

  if (query.isError) {
    return (
      <Panel>
        <ErrorState
          title={t("drawings.audit.errorTitle")}
          onRetry={() => void query.refetch()}
        />
      </Panel>
    );
  }

  if (!audit) {
    return (
      <Panel>
        <EmptyState
          icon="info"
          title={t("drawings.audit.noneTitle", "No audit yet")}
          description={t(
            "drawings.audit.noneDesc",
            "This drawing has no readiness audit.",
          )}
        />
      </Panel>
    );
  }

  const sortedIssues = [...(audit.issues ?? [])].sort(
    (a, b) =>
      severityRank(String(a.severity)) - severityRank(String(b.severity)) ||
      (b.count ?? 0) - (a.count ?? 0),
  );

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("drawings.audit.eyebrow")}
        title={t("drawings.audit.title")}
        description={
          drawing?.original_filename ??
          t("drawings.audit.description")
        }
        action={
          <Badge
            tone={
              Number(audit.overall_score) >= 80
                ? "green"
                : Number(audit.overall_score) >= 50
                  ? "gold"
                  : "red"
            }
          >
            {`${formatQuantity(audit.overall_score)}%`}
          </Badge>
        }
      />

      <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
        <Metric
          label={t("drawings.audit.elements")}
          value={formatQuantity(audit.element_count)}
        />
        <Metric
          label={t("drawings.audit.missingMaterial")}
          value={formatQuantity(audit.missing_material_count)}
        />
        <Metric
          label={t("drawings.audit.zeroQuantity")}
          value={formatQuantity(audit.zero_quantity_count)}
        />
        <Metric
          label={t("drawings.audit.unclassifiedProxy")}
          value={formatQuantity(audit.unclassified_proxy_count)}
        />
        <Metric
          label={t("drawings.audit.blocking", "Blocking errors")}
          value={formatQuantity(
            (audit.extra_stats as any)?.blocking_error_count ?? 0,
          )}
        />
      </div>

      <div className="border-t border-[var(--color-border)] px-5 py-3">
        <div className="flex flex-wrap items-center gap-2">
          {audit.created_at ? (
            <span className="text-[11px] text-[var(--color-text-muted)]">
              {t("drawings.audit.audited", {
                date: formatDateTime(audit.created_at),
              })}
            </span>
          ) : null}
        </div>
      </div>

      {sortedIssues.length > 0 ? (
        <div className="border-t border-[var(--color-border)]">
          <TableShell>
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                  <th className="px-4 py-3">
                    {t("drawings.audit.colSeverity", "Severity")}
                  </th>
                  <th className="px-4 py-3">
                    {t("drawings.audit.colCode", "Code")}
                  </th>
                  <th className="px-4 py-3">
                    {t("drawings.audit.colMessage", "Message")}
                  </th>
                  <th className="px-4 py-3 text-right">
                    {t("drawings.audit.colCount", "Count")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedIssues.map((issue, index) => (
                  <tr
                    key={`${issue.code ?? index}-${index}`}
                    className="border-t border-[var(--color-border)]"
                  >
                    <td className="px-4 py-3">
                      <Badge tone={severityTone(String(issue.severity))}>
                        {issue.severity}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px]">
                      {issue.code}
                    </td>
                    <td className="px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
                      {issue.message}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[12.5px]">
                      {issue.count ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        </div>
      ) : (
        <div className="border-t border-[var(--color-border)] px-5 py-4 text-[12px] text-[var(--color-text-secondary)]">
          {t("drawings.audit.noIssues")}
        </div>
      )}
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
      <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
        {label}
      </div>
      <div className="mt-1 font-mono text-[17px] font-semibold text-[var(--color-text-primary)]">
        {value}
      </div>
    </div>
  );
}
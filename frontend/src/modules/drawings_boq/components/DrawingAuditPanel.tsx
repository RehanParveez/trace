import {Badge, ErrorState, LoadingState, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import { useDrawingAudit } from "../hooks";
import { formatDateTime, formatQuantity,
} from "../utils/drawings-boq.utils";

interface DrawingAuditPanelProps {
  drawingId: string;
}

export function DrawingAuditPanel({
  drawingId,
}: DrawingAuditPanelProps) {
  const query =
    useDrawingAudit(drawingId);

  if (query.isLoading) {
    return (
      <Panel>
        <LoadingState label="Loading model audit…" />
      </Panel>
    );
  }

  if (query.isError || !query.data) {
    return (
      <Panel>
        <ErrorState
          title="Model audit is not available"
          onRetry={() =>
            void query.refetch()
          }
        />
      </Panel>
    );
  }

  const audit = query.data;

  return (
    <Panel>
      <PanelHeader
        eyebrow="MODEL READINESS"
        title="Drawing audit"
        description="Readiness checks produced by the backend drawing intelligence pipeline."
      />

      <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <Metric
          label="Overall score"
          value={`${formatQuantity(audit.overall_score)}%`}
        />

        <Metric
          label="Elements"
          value={formatQuantity(
            audit.element_count,
          )}
        />

        <Metric
          label="Missing material"
          value={formatQuantity(
            audit.missing_material_count,
          )}
        />

        <Metric
          label="Zero quantity"
          value={formatQuantity(
            audit.zero_quantity_count,
          )}
        />
      </div>

      <div className="border-t border-[var(--color-border)] px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="slate">
            Unclassified proxy:{" "}
            {audit.unclassified_proxy_count}
          </Badge>

          {audit.created_at ? (
            <span className="text-[11px] text-[var(--color-text-muted)]">
              Audited {formatDateTime(
                audit.created_at,
              )}
            </span>
          ) : null}
        </div>
      </div>

      {audit.issues.length > 0 ? (
        <div className="border-t border-[var(--color-border)] p-5">
          <div className="mb-3 text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            Issues
          </div>

          <div className="space-y-2">
            {audit.issues.map(
              (issue, index) => (
                <pre
                  key={index}
                  className="overflow-x-auto rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-[11px] text-[var(--color-text-secondary)]"
                >
                  {typeof issue === "string"
                    ? issue
                    : JSON.stringify(
                        issue,
                        null,
                        2,
                      )}
                </pre>
              ),
            )}
          </div>
        </div>
      ) : (
        <div className="border-t border-[var(--color-border)] px-5 py-4 text-[12px] text-[var(--color-text-secondary)]">
          No audit issues were reported.
        </div>
      )}
    </Panel>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
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

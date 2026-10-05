import { useState } from "react";
import {Badge, Button, ErrorState, LoadingState, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import {useBuildBOQFromCalculationRun, useCalculationRun, useCalculationRunDeductions, useCalculationRunLedger, useCalculationRunSolids, useCalculationRunStages, useStartCalculationRun,
} from "../hooks";
import {formatCalculationRunStatus, formatQuantity, getCalculationRunTone,
} from "../utils/drawings-boq.utils";
import type {CalculationRun,
} from "../types/drawings-boq.types";

interface CalculationRunPanelProps {
  projectId: string;
  drawingIds: string[];
  activeRunId?: string | null;
  onRunCreated?: (
    run: CalculationRun,
  ) => void;
  onBOQBuilt?: () => void;
}

type View =
  | "overview"
  | "solids"
  | "ledger"
  | "deductions";

export function CalculationRunPanel({
  projectId,
  drawingIds,
  activeRunId,
  onRunCreated,
  onBOQBuilt,
}: CalculationRunPanelProps) {
  const [runId, setRunId] =
    useState<string | null>(
      activeRunId ?? null,
    );

  const [view, setView] = useState<View>("overview");
  const [ruleSetCode, setRuleSetCode] = useState("");
  const [conventionCode, setConventionCode] = useState("");
  const startRun = useStartCalculationRun(projectId);
  const { showToast } = useToast();
  const runQuery = useCalculationRun(runId ?? undefined);
  const stagesQuery = useCalculationRunStages(runId ?? undefined);
  const buildBOQ =useBuildBOQFromCalculationRun(projectId);
  const run = runQuery.data;

  function start() {
    startRun.mutate(
      {
        drawing_ids:
          drawingIds.length > 0
            ? drawingIds
            : undefined,
        rule_set_code:
          ruleSetCode.trim() || null,
        convention_code:
          conventionCode.trim() || null,
      },
      {
        onSuccess: (createdRun) => {
          setRunId(createdRun.id);
          onRunCreated?.(createdRun);

          showToast({
            tone: "success",
            title:
              "Calculation run started",
          });
        },
      },
    );
  }

  function build() {
    if (!runId) {
      return;
    }
    buildBOQ.mutate(runId, {
      onSuccess: () => {
        showToast({
          tone: "success",
          title:
            "BOQ generated from calculation run",
        });
        onBOQBuilt?.();
      },
    });
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="QUANTITY ENGINE"
        title="Calculation run"
        description="Run the measurement engine against selected drawing revisions before promoting quantities into a BOQ."
        action={
          <Button
            variant="primary"
            size="sm"
            disabled={
              startRun.isPending ||
              drawingIds.length === 0
            }
            onClick={start}
          >
            {startRun.isPending
              ? "Starting…"
              : "Start calculation"}
          </Button>
        }
      />

      <div className="grid gap-3 border-b border-[var(--color-border)] p-5 md:grid-cols-2">
        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            Rule set code
          </span>

          <input
            value={ruleSetCode}
            onChange={(event) =>
              setRuleSetCode(
                event.target.value,
              )
            }
            placeholder="PUNJAB_CSR"
            className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]"
          />
        </label>

        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            Measurement convention
          </span>

          <input
            value={conventionCode}
            onChange={(event) =>
              setConventionCode(
                event.target.value,
              )
            }
            placeholder="Optional"
            className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]"
          />
        </label>
      </div>

      {!runId ? (
        <div className="p-5 text-[12px] text-[var(--color-text-secondary)]">
          Select parsed drawing revisions and start a calculation run.
        </div>
      ) : null}

      {runQuery.isLoading ? (
        <LoadingState label="Loading calculation run…" />
      ) : runQuery.isError ? (
        <ErrorState
          title="Couldn't load calculation run"
          onRetry={() =>
            void runQuery.refetch()
          }
        />
      ) : run ? (
        <>
          <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              label="Status"
              value={formatCalculationRunStatus(
                run.status,
              )}
              tone={getCalculationRunTone(
                run.status,
              )}
            />

            <Metric
              label="Progress"
              value={`${run.progress_pct}%`}
              tone="blue"
            />

            <Metric
              label="Engine"
              value={run.engine_version}
              tone="slate"
            />

            <Metric
              label="Run"
              value={run.id.slice(0, 8)}
              tone="slate"
            />
          </div>

          {run.error_message ? (
            <div className="mx-5 mb-5 rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] p-3 text-[12px] text-[#c24a3a]">
              {run.error_message}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2 border-y border-[var(--color-border)] p-4">
            {(
              [
                ["overview", "Overview"],
                ["solids", "Solids"],
                ["ledger", "Quantity ledger"],
                ["deductions", "Deductions"],
              ] as Array<
                [View, string]
              >
            ).map(
              ([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() =>
                    setView(key)
                  }
                  className={`rounded-[7px] border px-3 py-1.5 text-[11px] font-semibold ${
                    view === key
                      ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)]"
                  }`}
                >
                  {label}
                </button>
              ),
            )}

            {run.status === "COMPLETED" ||
            run.status === "PROMOTED" ? (
              <Button
                variant="primary"
                size="sm"
                disabled={buildBOQ.isPending}
                onClick={build}
              >
                {buildBOQ.isPending
                  ? "Building…"
                  : "Build BOQ"}
              </Button>
            ) : null}
          </div>

          {view === "overview" ? (
            <RunOverview
              run={run}
              stages={
                stagesQuery.data ?? []
              }
            />
          ) : null}

          {view === "solids" ? (
            <RunSolids runId={run.id} />
          ) : null}

          {view === "ledger" ? (
            <RunLedger runId={run.id} />
          ) : null}

          {view === "deductions" ? (
            <RunDeductions
              runId={run.id}
            />
          ) : null}
        </>
      ) : null}
    </Panel>
  );
}

function RunOverview({
  run,
  stages,
}: {
  run: CalculationRun;
  stages: Array<{
    id: string;
    stage: string;
    status: string;
    attempt: number;
    started_at?: string | null;
    finished_at?: string | null;
    counts: Record<string, unknown>;
    error?: string | null;
  }>;
}) {
  return (
    <div className="space-y-3 p-5">
      {stages.length === 0 ? (
        <div className="text-[12px] text-[var(--color-text-muted)]">
          No stage records have been produced yet.
        </div>
      ) : (
        stages.map((stage) => (
          <div
            key={stage.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-[8px] border border-[var(--color-border)] p-3"
          >
            <div>
              <div className="text-[12.5px] font-semibold text-[var(--color-text-primary)]">
                {stage.stage}
              </div>

              <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">
                Attempt {stage.attempt}
              </div>
            </div>

            <LocalBadge tone="slate">
              {stage.status}
            </LocalBadge>
          </div>
        ))
      )}

      {Object.keys(run.stats ?? {})
        .length > 0 ? (
        <pre className="overflow-x-auto rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[11px] text-[var(--color-text-secondary)]">
          {JSON.stringify(
            run.stats,
            null,
            2,
          )}
        </pre>
      ) : null}
    </div>
  );
}

function RunSolids({
  runId,
}: {
  runId: string;
}) {
  const [after, setAfter] =
    useState<string | null>(null);

  const query =
    useCalculationRunSolids(
      runId,
      {
        limit: 100,
        after,
      },
    );
  if (query.isLoading) {
    return (
      <LoadingState label="Loading quantity solids…" />
    );
  }
  if (query.isError) {
    return (
      <ErrorState
        title="Couldn't load solids"
        onRetry={() =>
          void query.refetch()
        }
      />
    );
  }

  const rows =
    query.data?.items ?? [];

  return (
    <DataTable
      headers={[
        "Role",
        "Component",
        "Geometry",
        "Volume m³",
        "Area m²",
        "Length m",
        "Status",
      ]}
      rows={rows.map((row) => [
        row.role,
        row.component_type,
        row.geometry_kind,
        formatQuantity(
          row.gross_volume_m3 ?? "",
        ),
        formatQuantity(
          row.gross_area_m2 ?? "",
        ),
        formatQuantity(
          row.gross_length_m ?? "",
        ),
        row.status,
      ])}
      nextCursor={
        query.data?.nextCursor ?? null
      }
      onNext={() =>
        setAfter(
          query.data?.nextCursor ?? null,
        )
      }
    />
  );
}

function RunLedger({
  runId,
}: {
  runId: string;
}) {
  const [after, setAfter] =
    useState<string | null>(null);

  const query =
    useCalculationRunLedger(
      runId,
      {
        limit: 100,
        after,
      },
    );

  if (query.isLoading) {
    return (
      <LoadingState label="Loading quantity ledger…" />
    );
  }

  if (query.isError) {
    return (
      <ErrorState
        title="Couldn't load quantity ledger"
        onRetry={() =>
          void query.refetch()
        }
      />
    );
  }

  const rows =
    query.data?.items ?? [];

  return (
    <DataTable
      headers={[
        "Work item",
        "Quantity",
        "Unit",
        "Source",
        "Confidence",
        "Formula",
      ]}
      rows={rows.map((row) => [
        row.work_item_code,
        formatQuantity(
          row.quantity_net,
        ),
        row.unit,
        row.source_kind,
        formatQuantity(
          row.confidence,
        ),
        row.formula_code,
      ])}
      nextCursor={
        query.data?.nextCursor ?? null
      }
      onNext={() =>
        setAfter(
          query.data?.nextCursor ?? null,
        )
      }
    />
  );
}

function RunDeductions({
  runId,
}: {
  runId: string;
}) {
  const [after, setAfter] =
    useState<string | null>(null);

  const query =
    useCalculationRunDeductions(
      runId,
      {
        limit: 100,
        after,
      },
    );

  if (query.isLoading) {
    return (
      <LoadingState label="Loading deductions…" />
    );
  }
  if (query.isError) {
    return (
      <ErrorState
        title="Couldn't load deductions"
        onRetry={() =>
          void query.refetch()
        }
      />
    );
  }

  const rows =
    query.data?.items ?? [];

  return (
    <DataTable
      headers={[
        "Type",
        "Quantity",
        "Unit",
        "Rule",
        "From solid",
        "To solid",
        "Explanation",
      ]}
      rows={rows.map((row) => [
        row.deduction_type,
        formatQuantity(
          row.quantity,
        ),
        row.unit,
        row.rule_code,
        row.from_solid_id.slice(0, 8),
        row.to_solid_id
          ? row.to_solid_id.slice(0, 8)
          : "—",
        row.explanation ?? "—",
      ])}
      nextCursor={
        query.data?.nextCursor ?? null
      }
      onNext={() =>
        setAfter(
          query.data?.nextCursor ?? null,
        )
      }
    />
  );
}

function DataTable({
  headers,
  rows,
  nextCursor,
  onNext,
}: {
  headers: string[];
  rows: string[][];
  nextCursor: string | null;
  onNext: () => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-left">
        <thead className="bg-[var(--color-surface-muted)]">
          <tr>
            {headers.map((header) => (
              <th
                key={header}
                className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={headers.length}
                className="px-4 py-8 text-center text-[12px] text-[var(--color-text-muted)]"
              >
                No rows found.
              </td>
            </tr>
          ) : (
            rows.map(
              (row, index) => (
                <tr
                  key={index}
                  className="border-t border-[var(--color-border)]"
                >
                  {row.map(
                    (value, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="px-4 py-3 text-[11.5px] text-[var(--color-text-secondary)]"
                      >
                        {value}
                      </td>
                    ),
                  )}
                </tr>
              ),
            )
          )}
        </tbody>
      </table>

      {nextCursor ? (
        <div className="border-t border-[var(--color-border)] p-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={onNext}
          >
            Load more
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone:
    | "green"
    | "gold"
    | "red"
    | "slate"
    | "blue";
}) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
      <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
        {label}
      </div>

      <div className="mt-2">
        <Badge tone={tone}>
          {value}
        </Badge>
      </div>
    </div>
  );
}

function LocalBadge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone:
    | "green"
    | "gold"
    | "red"
    | "slate"
    | "blue";
}) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold ${
        tone === "green"
          ? "bg-[var(--color-success-bg)] text-[var(--color-success)]"
          : tone === "gold"
            ? "bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
            : tone === "red"
              ? "bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
              : tone === "blue"
                ? "bg-[var(--color-info-bg)] text-[var(--color-info)]"
                : "bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]"
      }`}
    >
      {children}
    </span>
  );
}

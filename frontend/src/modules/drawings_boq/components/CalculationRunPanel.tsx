import { useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, ErrorState, LoadingState, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import {useBuildBOQFromCalculationRun, useCalculationRun, useCalculationRunDeductions, useCalculationRunLedger, useCalculationRunSolids, useCalculationRunStages, useStartCalculationRun,
} from "../hooks";
import {formatCalculationRunStatus, formatQuantity, getCalculationRunTone,
} from "../utils/drawings-boq.utils";
import type { CalculationRun } from "../types/drawings-boq.types";
import type {LedgerRowResponse, QuantitySolidResponse, DeductionResponse,
} from "../types/drawings-boq.types";
import { RunStatsSummary } from "./RunStatsSummary";
import { RebarMarksPanel } from "./RebarMarksPanel";
import {CalcUsagePanel, ElementImpactButton, RunFailureNotice, RunMetricsPanel, RunModeBadge, RunOptionsFields, RunStartNotice, classifyStartError, formatDurationMs, formatMb, useScaleT,
} from "../recalculation";
import type { RunOptions, StartRunError } from "../recalculation";

interface CalculationRunPanelProps {
  projectId: string;
  drawingIds: string[];
  activeRunId?: string | null;
  onRunCreated?: (run: CalculationRun) => void;
  onBOQBuilt?: () => void;
}

type View =
  | "overview"
  | "solids"
  | "ledger"
  | "deductions"
  | "rebar"
  | "metrics";

export function CalculationRunPanel({
  projectId,
  drawingIds,
  activeRunId,
  onRunCreated,
  onBOQBuilt,
}: CalculationRunPanelProps) {
  const { t } = useTranslation();

  const [runId, setRunId] =
    useState<string | null>(
      activeRunId ?? null,
    );

  const [view, setView] =
    useState<View>("overview");
  const [ruleSetCode, setRuleSetCode] =
    useState("");
  const [options, setOptions] =
    useState<RunOptions>({
      force_full: false,
      verify: false,
    });
  const [startError, setStartError] =
    useState<StartRunError | null>(null);
  const ts = useScaleT();
  const startRun =
    useStartCalculationRun(projectId);
  const { showToast } = useToast();
  const runQuery =
    useCalculationRun(
      runId ?? undefined,
    );
  const stagesQuery =
    useCalculationRunStages(
      runId ?? undefined,
    );
  const buildBOQ =
    useBuildBOQFromCalculationRun(
      projectId,
    );
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
        convention_code: null,
        force_full: options.force_full,
        verify: options.force_full ? false : options.verify,
      },
      {
        onError: (error) => {
          setStartError(
            classifyStartError(
              error,
              ts(
                "scale.start.failed",
                "The calculation could not be started.",
              ),
            ),
          );
        },
        onSuccess: ({ run: createdRun, reused }) => {
          setStartError(null);
          setRunId(createdRun.id);
          onRunCreated?.(createdRun);

        showToast({
          tone: "success",
          title: reused
            ? t("boq.calculationRun.toastReused") 
            : t("boq.calculationRun.toastStarted"),
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
          title: t(
            "boq.calculationRun.toastBOQGenerated",
          ),
        });

        onBOQBuilt?.();
      },
    });
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t(
          "boq.calculationRun.eyebrow",
        )}
        title={t(
          "boq.calculationRun.title",
        )}
        description={t(
          "boq.calculationRun.description",
        )}
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
              ? t(
                  "boq.calculationRun.starting",
                )
              : t(
                  "boq.calculationRun.startCalculation",
                )}
          </Button>
        }
      />

      <div className="grid gap-3 border-b border-[var(--color-border)] p-5 md:grid-cols-2">
        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            {t(
              "boq.calculationRun.ruleSetCode",
            )}
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

      
      </div>

      <div className="space-y-3 border-b border-[var(--color-border)] p-5">
        <RunOptionsFields
          value={options}
          onChange={setOptions}
          disabled={startRun.isPending}
        />

        {startError ? (
          <RunStartNotice
            error={startError}
            retrying={startRun.isPending}
            onRetry={start}
            onDismiss={() =>
              setStartError(null)
            }
          />
        ) : null}

        <CalcUsagePanel compact />
      </div>

      {!runId ? (
        <div className="p-5 text-[12px] text-[var(--color-text-secondary)]">
          {t(
            "boq.calculationRun.selectDrawingRevisions",
          )}
        </div>
      ) : null}

      {runQuery.isLoading ? (
        <LoadingState
          label={t(
            "boq.calculationRun.loading",
          )}
        />
      ) : runQuery.isError ? (
        <ErrorState
          title={t(
            "boq.calculationRun.loadError",
          )}
          onRetry={() =>
            void runQuery.refetch()
          }
        />
      ) : run ? (
        <>
          <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              label={t(
                "boq.calculationRun.metricStatus",
              )}
              value={formatCalculationRunStatus(
                run.status,
              )}
              tone={getCalculationRunTone(
                run.status,
              )}
            />

            <Metric
              label={t(
                "boq.calculationRun.metricProgress",
              )}
              value={`${run.progress_pct}%`}
              tone="blue"
            />

            <Metric
              label={t(
                "boq.calculationRun.metricEngine",
              )}
              value={run.engine_version}
              tone="slate"
            />

            <Metric
              label={t(
                "boq.calculationRun.metricRun",
              )}
              value={run.id.slice(0, 8)}
              tone="slate"
                        />
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 pb-4 text-[11.5px] text-[var(--color-text-muted)]">
            <RunModeBadge
              mode={run.mode}
            />

            {run.baseline_run_id ? (
              <span>
                {ts(
                  "scale.run.baseline",
                  "Built on run {{id}}",
                  {
                    id: run.baseline_run_id.slice(
                      0,
                      8,
                    ),
                  },
                )}
              </span>
            ) : null}

            {run.attempts && run.attempts > 1 ? (
              <span>
                {ts(
                  "scale.run.attempts",
                  "Attempt {{count}}",
                  {
                    count: run.attempts,
                  },
                )}
              </span>
            ) : null}

            {run.force_full ? (
              <span>
                {ts(
                  "scale.run.forcedFull",
                  "Recalculated everything on request",
                )}
              </span>
            ) : null}
          </div>

          {run.status === "FAILED" ? (
            <RunFailureNotice
              runId={run.id}
              errorCode={run.error_code}
              errorMessage={run.error_message}
              attempts={run.attempts}
              retrying={startRun.isPending}
              onRetry={
                drawingIds.length > 0
                  ? start
                  : undefined
              }
            />
          ) : run.error_message ? (
            <div className="mx-5 mb-5 rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] p-3 text-[12px] text-[#c24a3a]">
              {run.error_message}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2 border-y border-[var(--color-border)] p-4">
            {(
              [
                [
                  "overview",
                  t(
                    "boq.calculationRun.tabOverview",
                  ),
                ],
                [
                  "solids",
                  t(
                    "boq.calculationRun.tabSolids",
                  ),
                ],
                [
                  "ledger",
                  t(
                    "boq.calculationRun.tabLedger",
                  ),
                ],
                [
                  "deductions",
                  t(
                    "boq.calculationRun.tabDeductions",
                  ),
                ],
                [
                  "rebar",
                   t(
                    "boq.calculationRun.tabRebar", "Rebar"
                   ),
                 ],
                [
                  "metrics",
                  ts(
                    "scale.tab.performance",
                    "Performance",
                  ),
                ],
              ] as Array<[View, string]>
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
                  ? t(
                      "boq.calculationRun.building",
                    )
                  : t(
                      "boq.calculationRun.buildBOQ",
                    )}
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
            <RunSolids
              runId={run.id}
            />
          ) : null}

          {view === "ledger" ? (
            <RunLedger
              runId={run.id}
            />
          ) : null}

          {view === "deductions" ? (
            <RunDeductions
              runId={run.id}
          />
          ) : null}

          {view === "metrics" ? (
            <RunMetricsPanel
              runId={run.id}
              status={run.status}
            />
          ) : null}

          {view === "rebar" ?
           <RebarMarksPanel
             runId={run.id}
           />
           : null}
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
    id?: string;
    stage: string;
    status: string;
    attempt: number;
    started_at?: string | null;
    finished_at?: string | null;
    counts: Record<string, unknown>;
    error?: string | null;
    duration_ms?: number | null;
    peak_rss_mb?: number | null;
  }>;
}) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3 p-5">
      {stages.length === 0 ? (
        <div className="text-[12px] text-[var(--color-text-muted)]">
          {t(
            "boq.calculationRun.noStageRecords",
          )}
        </div>
      ) : (
        stages.map((stage) => (
          <div
            key={`${stage.stage}-${stage.attempt}`}
            className="flex flex-wrap items-center justify-between gap-3 rounded-[8px] border border-[var(--color-border)] p-3"
          >
            <div>
              <div className="text-[12.5px] font-semibold text-[var(--color-text-primary)]">
                {stage.stage}
              </div>

              <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">
                {t(
                  "boq.calculationRun.attempt",
                  {
                    count: stage.attempt,
                  },
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {stage.duration_ms != null ? (
                <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
                  {formatDurationMs(
                    stage.duration_ms,
                  )}
                  {stage.peak_rss_mb != null
                    ? ` · ${formatMb(stage.peak_rss_mb)}`
                    : ""}
                </span>
              ) : null}

              <LocalBadge tone="slate">
                {stage.status}
              </LocalBadge>
            </div>
          </div>
        ))
      )}

      <RunStatsSummary stats={run.stats} />
      {Object.keys(run.stats ?? {}).length > 0 ? (
        <details>
          <summary className="cursor-pointer text-[11.5px] text-[var(--color-text-muted)]">Raw stats</summary>
          <pre className="mt-2 overflow-x-auto rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[11px] text-[var(--color-text-secondary)]">
            {JSON.stringify(run.stats, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

function RunSolids({
  runId,
}: {
    runId: string;
}) {
  const { t } = useTranslation();
  const ts = useScaleT();

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
      <LoadingState
        label={t(
          "boq.calculationRun.solidsLoading",
        )}
      />
    );
  }

  if (query.isError) {
    return (
      <ErrorState
        title={t(
          "boq.calculationRun.solidsLoadError",
        )}
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
        t(
          "boq.calculationRun.colRole",
        ),
        t(
          "boq.calculationRun.colComponent",
        ),
        t(
          "boq.calculationRun.colGeometry",
        ),
        t(
          "boq.calculationRun.colVolumeM3",
        ),
        t(
          "boq.calculationRun.colAreaM2",
        ),
        t(
          "boq.calculationRun.colLengthM",
        ),
        t(
          "boq.calculationRun.colStatus",
        ),
        ts("scale.impact.open", "Impact"),
      ]}
      rows={rows.map((row: QuantitySolidResponse) => [
       row.role,
       row.component_type,
       row.geometry_kind,
       formatQuantity(row.gross_volume_m3 ?? ""),
       formatQuantity(row.gross_area_m2 ?? ""),
       formatQuantity(row.gross_length_m ?? ""),
       row.status,
       <ElementImpactButton
         key="impact"
         runId={runId}
         elementId={row.element_id}
       />,
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
  const { t } = useTranslation();
  const ts = useScaleT();

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
      <LoadingState
        label={t(
          "boq.calculationRun.ledgerLoading",
        )}
      />
    );
  }

  if (query.isError) {
    return (
      <ErrorState
        title={t(
          "boq.calculationRun.ledgerLoadError",
        )}
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
        t("boq.ledger.colWorkItem",),
        t("boq.ledger.colQuantity",),
        t("boq.ledger.colUnit",),
        t("boq.ledger.colSource",),
        t("boq.ledger.colConfidence",),
        t("boq.ledger.colFormula",),
        ts("scale.impact.open", "Impact"),
      ]}
      rows={rows.map((row: LedgerRowResponse) => [
       row.work_item_code,
       formatQuantity(row.quantity_net),
       row.unit,
       row.source_kind,
       formatQuantity(row.confidence),
       row.formula_code,
       <ElementImpactButton
         key="impact"
         runId={runId}
         elementId={row.element_id}
       />,
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
  const { t } = useTranslation();

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
      <LoadingState
        label={t(
          "boq.calculationRun.deductionsLoading",
        )}
      />
    );
  }

  if (query.isError) {
    return (
      <ErrorState
        title={t(
          "boq.calculationRun.deductionsLoadError",
        )}
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
        t(
          "boq.calculationRun.colType",
        ),
        t(
          "boq.calculationRun.colQuantity",
        ),
        t(
          "boq.calculationRun.colUnit",
        ),
        t(
          "boq.calculationRun.colRule",
        ),
        t(
          "boq.calculationRun.colFromSolid",
        ),
        t(
          "boq.calculationRun.colToSolid",
        ),
        t(
          "boq.calculationRun.colExplanation",
        ),
      ]}
      rows={rows.map((row: DeductionResponse) => [
       row.deduction_type,
       formatQuantity(row.quantity),
       row.unit,
       row.rule_code,
       row.from_solid_id.slice(0, 8),
       row.to_solid_id ? row.to_solid_id.slice(0, 8) : "—",
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
  rows: React.ReactNode[][];
  nextCursor: string | null;
  onNext: () => void;
}) {
  const { t } = useTranslation();

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
                {t(
                  "boq.calculationRun.noRowsFound",
                )}
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
                    (
                      value,
                      cellIndex,
                    ) => (
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
            {t(
              "boq.calculationRun.loadMore",
            )}
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
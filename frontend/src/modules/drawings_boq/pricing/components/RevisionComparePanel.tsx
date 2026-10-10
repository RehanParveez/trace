import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {Button, EmptyState, ErrorState, Field, inputClass, LoadingState, Panel, PanelHeader, StatCard, Toggle, useToast,
} from "../../../organizations/components/OrganizationUi";
import { getApiErrorCode, getApiErrorMessage } from "../../../identity";
import { useBOQVersions, useExportAdvancedBOQ } from "../../hooks";
import { ExportJobCard } from "../../recalculation";
import type { ExportJob } from "../../recalculation";
import type { BOQVersion } from "../../types/drawings-boq.types";
import { formatCurrency, formatDateTime } from "../../utils/drawings-boq.utils";
import { useVersionDiff } from "../hooks";
import { deltaClass, formatPercent, formatSigned } from "../utils/pricing.utils";
import { RevisionDiffTable } from "./RevisionDiffTable";

interface RevisionComparePanelProps {
  projectId: string;
  versionId: string;
  canExport: boolean;
}

const versionName = (v: BOQVersion) => `${v.label} · ${formatDateTime(v.created_at)}`;

async function blobErrorMessage(error: unknown, fallback: string): Promise<string> {
  const data = (error as { response?: { data?: unknown } })?.response?.data;
  if (data instanceof Blob) {
    try {
      const body = JSON.parse(await data.text());
      return body?.error?.message ?? body?.detail ?? fallback;
    } catch {
      return fallback;
    }
  }
  return getApiErrorMessage(error, fallback);
}

export function RevisionComparePanel({ projectId, versionId, canExport }: RevisionComparePanelProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const versionsQuery = useBOQVersions(projectId);

  const current = (versionsQuery.data ?? []).find((v) => v.id === versionId);
  const others = useMemo(
    () => (versionsQuery.data ?? []).filter((v) => v.id !== versionId).sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [versionsQuery.data, versionId],
  );

  const [baseId, setBaseId] = useState("");
  const [showUnchanged, setShowUnchanged] = useState(false);
  const [job, setJob] = useState<ExportJob | null>(null);

  useEffect(() => {
    if (others.length === 0) {
      setBaseId("");
      return;
    }
    if (!others.some((v) => v.id === baseId)) {
      const earlier = current ? others.find((v) => v.created_at < current.created_at) : undefined;
      setBaseId((earlier ?? others[0]).id);
    }
  }, [others, current, baseId]);

  const base = others.find((v) => v.id === baseId);
  const diff = useVersionDiff(baseId || undefined, versionId, { include_unchanged: showUnchanged, include_elements: true });
  const exportMutation = useExportAdvancedBOQ(versionId, current?.label ?? "BOQ");

  const approvedOrIssued = current?.lifecycle === "APPROVED" || current?.lifecycle === "ISSUED";
  const canDownload = canExport && approvedOrIssued && Boolean(current?.snapshot_id) && Boolean(base?.snapshot_id);

  function download() {
    if (!base?.snapshot_id) return;
    exportMutation.mutate(
      { kind: "REVISION_COMPARISON", format: "xlsx", snapshotId: null, compareSnapshotId: base.snapshot_id },
      {
        onSuccess: (outcome) => {
          if (outcome.kind === "job") {
            setJob(outcome.job);
            showToast({
              tone: "success",
              title: t("scale.export.queued", "Export is being prepared"),
              description: t("scale.export.queuedDesc", "Large exports are prepared in the background. It will appear below when it is ready."),
            });
            return;
          }
          setJob(null);
          showToast({ tone: "success", title: t("pricing.compare.exported", "Comparison workbook generated") });
        },
        onError: async (e) =>
          showToast({
            tone: "error",
            title: t("pricing.compare.exportFailed", "Export failed"),
            description: await blobErrorMessage(e, t("pricing.compare.exportFailedDesc", "The comparison could not be generated.")),
          }),
      },
    );
  }

  const summary = diff.data?.summary;

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("pricing.compare.eyebrow", "REVISIONS")}
        title={t("pricing.compare.title", "Compare with another BOQ version")}
        description={t(
          "pricing.compare.desc",
          "See what a drawing revision changed: lines added or removed, quantity and rate movements, the effect on the total, and which model elements account for each change.",
        )}
        action={
          canExport ? (
            <Button variant="secondary" size="sm" onClick={download} disabled={!canDownload || exportMutation.isPending}>
              {exportMutation.isPending ? t("pricing.compare.generating", "Generating…") : t("pricing.compare.download", "Download Excel")}
            </Button>
          ) : null
      }
      />

      {job ? (
        <div className="border-b border-[var(--color-border)] p-5">
          <ExportJobCard
            job={job}
            kindLabel={t("boq.advancedExport.revisionComparison", "Revision comparison")}
            onRequestAgain={download}
            onDismiss={() => setJob(null)}
          />
        </div>
      ) : null}

      {versionsQuery.isLoading ? (
        <LoadingState label={t("pricing.compare.loading", "Loading versions…")} />
      ) : others.length === 0 ? (
        <EmptyState
          icon="refresh"
          title={t("pricing.compare.noOthersTitle", "Nothing to compare yet")}
          description={t("pricing.compare.noOthersDesc", "Upload a revised drawing and build a second BOQ version, then compare them here.")}
        />
      ) : (
        <>
          <div className="grid gap-4 border-b border-[var(--color-border)] p-5 sm:grid-cols-[1fr_auto] sm:items-end">
            <Field label={t("pricing.compare.base", "Compare against")} hint={current ? t("pricing.compare.baseHint", "Changes are shown from the version you pick to “{{label}}”.", { label: current.label }) : undefined}>
              <select className={inputClass} value={baseId} onChange={(e) => setBaseId(e.target.value)}>
                {others.map((v) => (
                  <option key={v.id} value={v.id}>{versionName(v)}</option>
                ))}
              </select>
            </Field>
            <label className="flex items-center gap-2 pb-2 text-[12.5px] text-[var(--color-text-secondary)]">
              <Toggle checked={showUnchanged} onChange={() => setShowUnchanged((v) => !v)} label={t("pricing.compare.showUnchanged", "Include unchanged lines")} />
              {t("pricing.compare.showUnchanged", "Include unchanged lines")}
            </label>
          </div>

          {canExport && !canDownload ? (
            <div className="border-b border-[var(--color-border)] px-5 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
              {!approvedOrIssued
                ? t("pricing.compare.needApproved", "The Excel comparison is available once this version is approved or issued.")
                : t("pricing.compare.needSnapshots", "Both versions need an approval snapshot before they can be exported.")}
            </div>
          ) : null}

          {diff.isLoading ? (
            <LoadingState label={t("pricing.compare.comparing", "Comparing…")} />
          ) : diff.isError || !diff.data || !summary ? (
            <div className="p-5">
              <ErrorState
                title={t("pricing.compare.error", "We couldn't compare these versions")}
                description={
                  getApiErrorCode(diff.error) === "DIFF_PROJECT_MISMATCH"
                    ? t("pricing.compare.mismatch", "Only versions of the same project can be compared.")
                    : getApiErrorMessage(diff.error, t("pricing.compare.errorDesc", "The request failed. Check your connection and try again."))
                }
                onRetry={() => void diff.refetch()}
              />
            </div>
          ) : (
            <>
              <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label={t("pricing.compare.statTotal", "Total change")}
                  value={formatSigned(summary.total_delta, 2)}
                  note={summary.total_delta_pct !== null ? t("pricing.compare.statTotalNote", "{{pct}}% on {{was}}", { pct: formatSigned(summary.total_delta_pct, 1), was: formatCurrency(summary.total_a) }) : formatCurrency(summary.total_b)}
                  icon="trend"
                  tone={Number(summary.total_delta) > 0 ? "red" : Number(summary.total_delta) < 0 ? "green" : "blue"}
                />
                <StatCard label={t("pricing.compare.statAdded", "Added")} value={summary.ADDED} note={t("pricing.compare.statAddedNote", "New lines")} icon="plus" tone="green" />
                <StatCard label={t("pricing.compare.statRemoved", "Removed")} value={summary.REMOVED} note={t("pricing.compare.statRemovedNote", "Lines no longer present")} icon="x" tone="red" />
                <StatCard label={t("pricing.compare.statChanged", "Changed")} value={summary.CHANGED} note={t("pricing.compare.statChangedNote", "Quantity, unit or rate moved")} icon="edit" tone="gold" />
              </div>
              <div className="flex flex-wrap gap-x-8 gap-y-1 px-5 pb-4 text-[12.5px] text-[var(--color-text-secondary)]">
                <span>
                  {t("pricing.compare.totals", "Total: {{a}} → {{b}}", { a: formatCurrency(summary.total_a), b: formatCurrency(summary.total_b) })}{" "}
                  <span className={deltaClass(summary.total_delta)}>({formatPercent(summary.total_delta_pct, 1)})</span>
                </span>
                {summary.unpriced_a > 0 || summary.unpriced_b > 0 ? (
                  <span className="text-[var(--color-warning)]">
                    {t("pricing.compare.unpriced", "Unpriced lines: {{a}} before, {{b}} now. Totals leave them out.", { a: summary.unpriced_a, b: summary.unpriced_b })}
                  </span>
                ) : null}
              </div>
              <RevisionDiffTable lines={diff.data.lines} />
            </>
          )}
        </>
      )}
    </Panel>
  );
}

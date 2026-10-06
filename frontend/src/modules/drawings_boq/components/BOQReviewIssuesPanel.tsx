import { useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge,Button, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import {useReviewIssues, useUpdateReviewIssue,
} from "../hooks";
import type { ReviewStatus } from "../types/drawings-boq.types";
import { ReasonDialog } from "./ReasonDialog";

interface BOQReviewIssuesPanelProps {
  projectId: string;
  versionId?: string;
  canResolve: boolean;
  onSelectItem?: (boqItemId: string) => void;
}

const severityTone = (s: string): "red" | "gold" | "slate" =>
  s === "error" ? "red" : s === "warning" ? "gold" : "slate";

const statusTone = (s: string): "gold" | "green" | "slate" =>
  s === "OPEN" ? "gold" : s === "RESOLVED" ? "green" : "slate";

export function BOQReviewIssuesPanel({
  projectId,
  versionId,
  canResolve,
  onSelectItem,
}: BOQReviewIssuesPanelProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();

  const [status, setStatus] = useState<ReviewStatus | "">("OPEN");
  const query = useReviewIssues(projectId, versionId, status || undefined);
  const openQuery = useReviewIssues(projectId, versionId, "OPEN");
  const update = useUpdateReviewIssue(projectId, versionId, status || undefined);

  const [acting, setActing] = useState<{
    issueId: string;
    code: string;
    status: "RESOLVED" | "WAIVED";
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const issues = query.data ?? [];
  const openIssues = openQuery.data ?? [];

  const blockingApproval = openIssues.filter((i) => i.blocks === "APPROVAL").length;
  const blockingIssue = openIssues.filter((i) => i.blocks === "ISSUE").length;

  function confirm(note: string) {
    if (!acting) return;
    setError(null);

    update.mutate(
      {
        issueId: acting.issueId,
        payload: {
          status: acting.status,
          note: note || null,
        },
      },
      {
        onSuccess: () => {
          showToast({
            tone: "success",
            title:
              acting.status === "WAIVED"
                ? t("boq.reviewIssues.waivedToast")
                : t("boq.reviewIssues.resolvedToast"),
          });
          setActing(null);
        },
        onError: () => {
          setError(
            t("boq.reviewIssues.updateError", "Couldn't update this issue."),
          );
        },
      },
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.reviewIssues.eyebrow")}
        title={t("boq.reviewIssues.title")}
        description={t("boq.reviewIssues.description")}
        action={
          <div className="flex flex-wrap gap-2">
            {blockingApproval > 0 && (
              <Badge tone="red">
                {t("boq.reviewIssues.blocksApproval", "{{n}} block approval", {
                  n: blockingApproval,
                })}
              </Badge>
            )}
            {blockingIssue > 0 && (
              <Badge tone="gold">
                {t("boq.reviewIssues.blocksIssue", "{{n}} block issue", {
                  n: blockingIssue,
                })}
              </Badge>
            )}
          </div>
        }
      />

      <div className="flex gap-2 border-b border-[var(--color-border)] p-4">
        {(["OPEN", "RESOLVED", "WAIVED", ""] as const).map((value) => (
          <button
            key={value || "ALL"}
            type="button"
            onClick={() => setStatus(value)}
            className={`rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${
              status === value
                ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"
            }`}
          >
            {value
              ? t(`boq.reviewIssues.status.${value.toLowerCase()}`)
              : t("boq.reviewIssues.status.all", "All")}
          </button>
        ))}
      </div>

      {query.isLoading ? (
        <LoadingState label={t("boq.reviewIssues.loading")} />
      ) : query.isError ? (
        <ErrorState
          title={t("boq.reviewIssues.loadError")}
          onRetry={() => void query.refetch()}
        />
      ) : issues.length === 0 ? (
        <EmptyState
          icon="info"
          title={t("boq.reviewIssues.emptyTitle", "No issues")}
          description={t("boq.reviewIssues.emptyDesc", "Nothing needs attention here.")}
        />
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {issues.map((issue) => (
            <div key={issue.id} className="space-y-3 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={severityTone(issue.severity)}>
                  {issue.severity}
                </Badge>
                <span className="font-mono text-[12px] font-semibold text-[var(--color-text-primary)]">
                  {issue.code}
                </span>
                {issue.blocks !== "NONE" && (
                  <Badge tone="red">
                    {t("boq.reviewIssues.blocks", { value: issue.blocks })}
                  </Badge>
                )}
                <Badge tone={statusTone(issue.status)}>{issue.status}</Badge>
              </div>

              <div className="text-[13px] text-[var(--color-text-primary)]">
                {issue.message}
              </div>

              {issue.suggested_fix && (
                <div className="rounded-[7px] bg-[var(--color-surface-muted)] p-3 text-[11.5px] text-[var(--color-text-secondary)]">
                  {t("boq.reviewIssues.suggestedFix")} {issue.suggested_fix}
                </div>
              )}

              {issue.resolution_note && (
                <p className="text-[12px] italic text-[var(--color-text-muted)]">
                  {issue.resolution_note}
                </p>
              )}

              <div className="flex flex-wrap gap-2 pt-1">
                {issue.boq_item_id && onSelectItem && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onSelectItem(issue.boq_item_id as string)}
                  >
                    {t("boq.reviewIssues.goToItem", "Go to item")}
                  </Button>
                )}

                {canResolve && issue.status === "OPEN" && (
                  <>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setError(null);
                        setActing({
                          issueId: issue.id,
                          code: issue.code,
                          status: "RESOLVED",
                        });
                      }}
                    >
                      {t("boq.reviewIssues.resolve")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setError(null);
                        setActing({
                          issueId: issue.id,
                          code: issue.code,
                          status: "WAIVED",
                        });
                      }}
                    >
                      {t("boq.reviewIssues.waive")}
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {acting && (
        <ReasonDialog
          title={
            acting.status === "WAIVED"
              ? t("boq.reviewIssues.waiveTitle", "Waive issue")
              : t("boq.reviewIssues.resolveTitle", "Resolve issue")
          }
          description={acting.code}
          label={
            acting.status === "WAIVED"
              ? t("boq.reviewIssues.waiveReason", "Reason for waiving")
              : t("boq.reviewIssues.resolveNote", "Note (optional)")
          }
          required={acting.status === "WAIVED"}
          confirmLabel={
            update.isPending
              ? t("common.saving", "Saving…")
              : acting.status === "WAIVED"
                ? t("boq.reviewIssues.waive")
                : t("boq.reviewIssues.resolve")
          }
          pending={update.isPending}
          error={error}
          onConfirm={confirm}
          onClose={() => setActing(null)}
        />
      )}
    </Panel>
  );
}
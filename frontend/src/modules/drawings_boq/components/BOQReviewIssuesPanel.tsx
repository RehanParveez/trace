import { useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, ErrorState, LoadingState, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import {useReviewIssues, useUpdateReviewIssue,
} from "../hooks";
import type { ReviewStatus } from "../types/drawings-boq.types";

interface BOQReviewIssuesPanelProps {
  projectId: string;
  versionId?: string;
  canResolve: boolean;
}

export function BOQReviewIssuesPanel({
  projectId,
  versionId,
  canResolve,
}: BOQReviewIssuesPanelProps) {

  const { t } = useTranslation();
  const [status, setStatus] = useState<ReviewStatus | undefined>("OPEN");
  const query = useReviewIssues(projectId, versionId, status);
  const update = useUpdateReviewIssue(projectId, versionId, status);
  const { showToast } = useToast();

  if (query.isLoading) {
    return (
      <Panel>
        <LoadingState label={t("boq.reviewIssues.loading")} />
      </Panel>
    );
  }

  if (query.isError) {
    return (
      <Panel>
        <ErrorState
          title={t("boq.reviewIssues.loadError")}
          onRetry={() => void query.refetch()}
        />
      </Panel>
    );
  }

  const issues = query.data ?? [];

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.reviewIssues.eyebrow")}
        title={t("boq.reviewIssues.title")}
        description={t("boq.reviewIssues.description")}
        action={
          <div className="flex gap-1">
            {(
              ["OPEN", "RESOLVED", "WAIVED"] as ReviewStatus[]
            ).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatus(value)}
                className={`rounded-[6px] px-2.5 py-1 text-[10px] font-semibold ${
                  status === value
                    ? "bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                    : "text-[var(--color-text-muted)]"
                }`}
              >
                {t(`boq.reviewIssues.status.${value.toLowerCase()}`)}
              </button>
            ))}
          </div>
        }
      />

      {issues.length === 0 ? (
        <div className="p-5 text-[12px] text-[var(--color-text-secondary)]">
          {t("boq.reviewIssues.empty", {
            status: status
              ? t(`boq.reviewIssues.status.${status.toLowerCase()}`)
              : "",
          })}
        </div>
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {issues.map((issue) => (
            <ReviewIssueRow
              key={issue.id}
              issue={issue}
              canResolve={canResolve}
              isUpdating={update.isPending}
              onResolve={() =>
                update.mutate(
                  {
                    issueId: issue.id,
                    payload: {
                      status: "RESOLVED",
                      note: t("boq.reviewIssues.resolveNote"),
                    },
                  },
                  {
                    onSuccess: () =>
                      showToast({
                        tone: "success",
                        title: t("boq.reviewIssues.resolvedToast"),
                      }),
                  },
                )
              }
              onWaive={() =>
                update.mutate(
                  {
                    issueId: issue.id,
                    payload: {
                      status: "WAIVED",
                      note: t("boq.reviewIssues.waiveNote"),
                    },
                  },
                  {
                    onSuccess: () =>
                      showToast({
                        tone: "success",
                        title: t("boq.reviewIssues.waivedToast"),
                      }),
                  },
                )
              }
            />
          ))}
        </div>
      )}
    </Panel>
  );
}

function ReviewIssueRow({
  issue,
  canResolve,
  isUpdating,
  onResolve,
  onWaive,
}: {
  issue: {
    id: string;
    code: string;
    severity: string;
    blocks: string;
    message: string;
    suggested_fix?: string | null;
    status: string;
  };
  canResolve: boolean;
  isUpdating: boolean;
  onResolve: () => void;
  onWaive: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="slate">{issue.code}</Badge>

        <Badge
          tone={
            issue.severity === "error"
              ? "red"
              : issue.severity === "warning"
                ? "gold"
                : "blue"
          }
        >
          {issue.severity}
        </Badge>

        {issue.blocks !== "NONE" ? (
          <Badge tone="red">
            {t("boq.reviewIssues.blocks", { value: issue.blocks })}
          </Badge>
        ) : null}

        <Badge tone="slate">{issue.status}</Badge>
      </div>

      <div className="text-[13px] font-semibold text-[var(--color-text-primary)]">
        {issue.message}
      </div>

      {issue.suggested_fix ? (
        <div className="rounded-[7px] bg-[var(--color-surface-muted)] p-3 text-[11.5px] text-[var(--color-text-secondary)]">
          {t("boq.reviewIssues.suggestedFix")} {issue.suggested_fix}
        </div>
      ) : null}

      {canResolve && issue.status === "OPEN" ? (
        <div className="flex gap-2">
          <Button
            variant="primary"
            size="sm"
            disabled={isUpdating}
            onClick={onResolve}
          >
            {t("boq.reviewIssues.resolve")}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            disabled={isUpdating}
            onClick={onWaive}
          >
            {t("boq.reviewIssues.waive")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
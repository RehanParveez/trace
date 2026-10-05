import { useState } from "react";
import {Badge, Button, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import {useApproveBOQVersion, useArchiveBOQVersion, useIssueBOQVersion, useReopenBOQVersion, useSubmitBOQForReview,
} from "../hooks";
import {formatBOQLifecycle, getBOQLifecycleTone,
} from "../utils/drawings-boq.utils";
import type { BOQVersion, TransitionRequest } from "../types/drawings-boq.types";
import type { UseMutationResult } from "@tanstack/react-query";

interface BOQLifecycleActionsProps {
  projectId: string;
  version: BOQVersion;
  canUpdate: boolean;
  canApprove: boolean;
  canIssue: boolean;
}

type BOQVersionMutation<TVars = unknown> = UseMutationResult<
  BOQVersion,
  Error,
  TVars,
  unknown
>;

export function BOQLifecycleActions({
  projectId,
  version,
  canUpdate,
  canApprove,
  canIssue,
}: BOQLifecycleActionsProps) {
  const { showToast } = useToast();
  const [note, setNote] = useState("");
  const submit = useSubmitBOQForReview(version.id, projectId);
  const reopen = useReopenBOQVersion(version.id, projectId);
  const approve = useApproveBOQVersion(version.id, projectId);
  const issue = useIssueBOQVersion(version.id, projectId);
  const archive = useArchiveBOQVersion(version.id, projectId);
  const lifecycle = version.lifecycle ?? "DRAFT";

  function run<TVars>(
    mutation: BOQVersionMutation<TVars>,
    payload?: TVars,
    successMessage?: string,
  ) {
    (mutation.mutate as (
      vars?: TVars,
      opts?: { onSuccess?: () => void },
    ) => void)(payload, {
      onSuccess: () => {
        if (successMessage) {
          showToast({
            tone: "success",
            title: successMessage,
          });
        }
      },
    });
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="BOQ WORKFLOW"
        title="Lifecycle"
        description="Control review, approval and issue state without changing the immutable calculation history."
        action={
          <Badge
            tone={getBOQLifecycleTone(lifecycle)}
          >
            {formatBOQLifecycle(lifecycle)}
          </Badge>
        }
      />

      <div className="space-y-4 p-5">
        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            Transition note
          </span>

          <textarea
            value={note}
            onChange={(event) =>
              setNote(event.target.value)
            }
            rows={3}
            placeholder="Optional approval or issue note"
            className="mt-1.5 w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]"
          />
        </label>

        <div className="flex flex-wrap gap-2">
          {canUpdate && lifecycle === "DRAFT" ? (
            <Button
              variant="primary"
              disabled={submit.isPending}
              onClick={() =>
                run(
                  submit,
                  undefined,
                  "BOQ submitted for review",
                )
              }
            >
              {submit.isPending
                ? "Submitting…"
                : "Submit for review"}
            </Button>
          ) : null}

          {canApprove && lifecycle === "UNDER_REVIEW" ? (
            <Button
              variant="primary"
              disabled={approve.isPending}
              onClick={() =>
                run(
                  approve,
                  {
                    note: note.trim() || null,
                  } as TransitionRequest,
                  "BOQ approved",
                )
              }
            >
              {approve.isPending
                ? "Approving…"
                : "Approve"}
            </Button>
          ) : null}

          {canIssue && lifecycle === "APPROVED" ? (
            <Button
              variant="primary"
              disabled={issue.isPending}
              onClick={() =>
                run(
                  issue,
                  {
                    note: note.trim() || null,
                  } as TransitionRequest,
                  "BOQ issued",
                )
              }
            >
              {issue.isPending
                ? "Issuing…"
                : "Issue BOQ"}
            </Button>
          ) : null}

          {canApprove && lifecycle === "APPROVED" ? (
            <Button
              variant="ghost"
              disabled={reopen.isPending}
              onClick={() =>
                run(
                  reopen,
                  undefined,
                  "BOQ reopened",
                )
              }
            >
              Reopen
            </Button>
          ) : null}

          {canIssue && lifecycle === "ISSUED" ? (
            <Button
              variant="ghost"
              disabled={archive.isPending}
              onClick={() =>
                run(
                  archive,
                  undefined,
                  "BOQ archived",
                )
              }
            >
              {archive.isPending
                ? "Archiving…"
                : "Archive"}
            </Button>
          ) : null}
        </div>
      </div>
    </Panel>
  );
}
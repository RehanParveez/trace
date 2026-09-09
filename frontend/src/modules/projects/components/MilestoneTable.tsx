import { useState } from "react";
import {Button, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {useDeleteMilestone, useUpdateMilestone,
} from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type {Milestone,
} from "../types/project.types";
import {formatProjectDate,
} from "../utils/project.utils";
import { MilestoneForm } from "./MilestoneForm";

interface MilestoneTableProps {
  projectId: string;
  milestones: Milestone[];
  canUpdate: boolean;
}

export function MilestoneTable({
  projectId,
  milestones,
  canUpdate,
}: MilestoneTableProps) {
  const [formOpen, setFormOpen] =
    useState(false);

  const [editingMilestone, setEditingMilestone] =
    useState<Milestone | undefined>();

  const deleteMilestone =
    useDeleteMilestone();

    const updateMilestone =
    useUpdateMilestone();

  function openCreate() {
    setEditingMilestone(undefined);
    setFormOpen(true);
  }

  function openEdit(
    milestone: Milestone,
  ) {
    setEditingMilestone(milestone);
    setFormOpen(true);
  }

  return (
    <>
      <Panel className="overflow-hidden">
        <PanelHeader
          eyebrow="DELIVERY TRACK"
          title="Milestones"
          description="Major delivery checkpoints tracked against this project's timeline."
          action={
            canUpdate ? (
              <Button variant="primary" onClick={openCreate}>
                Add milestone
              </Button>
            ) : undefined
          }
        />

        {milestones.length === 0 ? (
          <div className="p-6 text-[12px] text-[var(--color-text-secondary)]">
            No milestones have been configured
            for this project.
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {milestones.map(
              (milestone) => {
                const completed =
                  milestone.completed_at !==
                  null;

                return (
                  <div
                    key={milestone.id}
                    className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <div
                        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] ${
                          completed
                            ? "bg-[var(--color-success-bg)] text-[var(--color-success)]"
                            : "bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                        }`}
                      >
                        {completed
                          ? "✓"
                          : "•"}
                      </div>

                      <div className="min-w-0">
                        <div className="text-[14px] font-semibold text-[var(--color-text-primary)]">
                          {milestone.name}
                        </div>

                        {milestone.description ? (
                          <div className="mt-1 text-[12px] leading-4 text-[var(--color-text-secondary)]">
                            {
                              milestone.description
                            }
                          </div>
                        ) : null}

                        <div className="mt-1.5 text-[11px] text-[var(--color-text-muted)]">
                          Due:{" "}
                          {formatProjectDate(
                            milestone.due_date,
                          )}
                        </div>
                      </div>
                    </div>

                    {canUpdate ? (
                      <div className="flex shrink-0 gap-2">
                        <Button
                          variant="ghost"
                          disabled={updateMilestone.isPending}
                          onClick={() =>
                            updateMilestone.mutate({
                              projectId,
                              milestoneId: milestone.id,
                              payload: {
                                completed_at: completed
                                  ? null
                                  : new Date().toISOString().slice(0, 10),
                              },
                            })
                          }
                        >
                          {completed ? "Reopen" : "Complete"}
                        </Button>

                        <Button
                          variant="ghost"
                          onClick={() =>
                            openEdit(
                              milestone,
                            )
                          }
                        >
                          Edit
                        </Button>

                        <Button
                          variant="ghost"
                          disabled={
                            deleteMilestone.isPending
                          }
                          onClick={() => {
                            if (
                              !window.confirm(
                                `Delete "${milestone.name}"?`,
                              )
                            ) {
                              return;
                            }

                            deleteMilestone.mutate(
                              {
                                projectId,
                                milestoneId:
                                  milestone.id,
                              },
                              {
                                onError: (error) =>
                                  window.alert(getApiErrorMessage(error, "Couldn't delete this milestone.")),
                              },
                            );
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    ) : null}
                  </div>
                );
              },
            )}
          </div>
        )}
      </Panel>

      {formOpen ? (
        <MilestoneForm
          projectId={projectId}
          milestone={
            editingMilestone
          }
          onClose={() =>
            setFormOpen(false)
          }
        />
      ) : null}
    </>
  );
}
import { useState } from "react";
import {Button, Panel,
} from "../../organizations/components/OrganizationUi";
import {useDeleteMilestone,
} from "../hooks";
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
        <div className="flex items-center justify-between border-b border-[#e1d5bc] p-5 sm:p-6">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
              DELIVERY TRACK
            </div>

            <div className="mt-1 font-[Archivo] text-[17px] font-bold text-[#191410]">
              Milestones
            </div>
          </div>

          {canUpdate ? (
            <Button
              variant="primary"
              onClick={openCreate}
            >
              Add milestone
            </Button>
          ) : null}
        </div>

        {milestones.length === 0 ? (
          <div className="p-6 text-[11px] text-[#756957]">
            No milestones have been configured
            for this project.
          </div>
        ) : (
          <div className="divide-y divide-[#e1d5bc]">
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
                            ? "bg-[#e4f5ec] text-[#1e9d63]"
                            : "bg-[#fbefd9] text-[#b98626]"
                        }`}
                      >
                        {completed
                          ? "✓"
                          : "•"}
                      </div>

                      <div className="min-w-0">
                        <div className="text-[12px] font-semibold text-[#191410]">
                          {milestone.name}
                        </div>

                        {milestone.description ? (
                          <div className="mt-1 text-[10px] leading-4 text-[#756957]">
                            {
                              milestone.description
                            }
                          </div>
                        ) : null}

                        <div className="mt-1.5 text-[9px] text-[#a2957c]">
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
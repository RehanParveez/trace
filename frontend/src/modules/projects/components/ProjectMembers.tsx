import { useState } from "react";
import {Button, Panel,
} from "../../organizations/components/OrganizationUi";
import {useRemoveProjectMember,
} from "../hooks";
import type {ProjectMember,
} from "../types/project.types";
import {formatProjectMemberRole, getProjectMemberName,
} from "../utils/project.utils";
import { ProjectMemberDialog } from "./ProjectMemberDialog";

interface ProjectMembersProps {
  projectId: string;
  members: ProjectMember[];
  canUpdate: boolean;
}

export function ProjectMembers({
  projectId,
  members,
  canUpdate,
}: ProjectMembersProps) {
  const [dialogOpen, setDialogOpen] =
    useState(false);

  const removeMember =
    useRemoveProjectMember();

  return (
    <>
      <Panel className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-[#e1d5bc] p-5 sm:p-6">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
              PROJECT TEAM
            </div>

            <div className="mt-1 font-[Archivo] text-[17px] font-bold text-[#191410]">
              Assigned members
            </div>
          </div>

          {canUpdate ? (
            <Button
              variant="primary"
              onClick={() =>
                setDialogOpen(true)
              }
            >
              Add member
            </Button>
          ) : null}
        </div>

        {members.length === 0 ? (
          <div className="p-6 text-[11px] text-[#756957]">
            No members have been assigned to
            this project yet.
          </div>
        ) : (
          <div className="divide-y divide-[#e1d5bc]">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between gap-4 p-5"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[#fbefd9] text-[11px] font-bold text-[#9b6f1d]">
                    {getProjectMemberName(
                      member,
                    )
                      .charAt(0)
                      .toUpperCase()}
                  </div>

                  <div className="min-w-0">
                    <div className="truncate text-[11.5px] font-semibold text-[#191410]">
                      {getProjectMemberName(
                        member,
                      )}
                    </div>

                    <div className="mt-0.5 truncate text-[9.5px] text-[#756957]">
                      {member.user?.email ??
                        member.user_id}
                    </div>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <span className="rounded-full border border-[#e1d5bc] bg-white px-2.5 py-1 text-[9px] font-semibold text-[#6b6152]">
                    {formatProjectMemberRole(
                      member.role,
                    )}
                  </span>

                  {canUpdate ? (
                    <Button
                      variant="ghost"
                      disabled={
                        removeMember.isPending
                      }
                      onClick={() => {
                        const confirmed =
                          window.confirm(
                            "Remove this member from the project?",
                          );

                        if (!confirmed) {
                          return;
                        }

                        removeMember.mutate({
                          projectId,
                          userId:
                            member.user_id,
                        });
                      }}
                    >
                      Remove
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {dialogOpen ? (
        <ProjectMemberDialog
          projectId={projectId}
          onClose={() =>
            setDialogOpen(false)
          }
        />
      ) : null}
    </>
  );
}
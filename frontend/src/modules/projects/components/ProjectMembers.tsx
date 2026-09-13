import { useState } from "react";
import {Button, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {useRemoveProjectMember,
} from "../hooks";
import type {ProjectMember,
} from "../types/project.types";
import {formatProjectMemberRole, getProjectMemberName,
} from "../utils/project.utils";
import { ProjectMemberDialog } from "./ProjectMemberDialog";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  const [dialogOpen, setDialogOpen] =
    useState(false);

  const removeMember =
    useRemoveProjectMember();

  return (
    <>
      <Panel className="overflow-hidden">
        <PanelHeader
          eyebrow={t("projects.members.eyebrow")}
          title={t("projects.members.title")}
          description={t("projects.members.description")}
          action={
           canUpdate ? (
            <Button variant="primary" onClick={() => setDialogOpen(true)}>
             {t("projects.members.add")}
            </Button>
           ) : undefined
          }
        />

        {members.length === 0 ? (
          <div className="p-6 text-[12px] text-[var(--color-text-secondary)]">
            {t("projects.members.empty")}
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between gap-4 p-5"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-warning-bg)] text-[13px] font-bold text-[var(--color-warning)]">
                    {getProjectMemberName(
                      member,
                    )
                      .charAt(0)
                      .toUpperCase()}
                  </div>

                  <div className="min-w-0">
                    <div className="truncate text-[13.5px] font-semibold text-[var(--color-text-primary)]">
                      {getProjectMemberName(
                        member,
                      )}
                    </div>

                    <div className="mt-0.5 truncate text-[12px] text-[var(--color-text-secondary)]">
                      {member.user?.email ??
                        member.user_id}
                    </div>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <span className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1 text-[11px] font-semibold text-[var(--color-text-secondary)]">
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
                            t("projects.members.removeConfirm"),
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
                      {t("projects.members.remove")}
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
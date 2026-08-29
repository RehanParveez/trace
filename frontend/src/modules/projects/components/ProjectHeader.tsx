import {Badge, Button, Icon,
} from "../../organizations/components/OrganizationUi";
import type { Project } from "../types/project.types";
import {formatProjectDate,
} from "../utils/project.utils";
import { ProjectStatusBadge } from "./ProjectStatusBadge";

interface ProjectHeaderProps {
  project: Project;
  canUpdate: boolean;
  canDelete: boolean;
  onEdit: () => void;
  onDelete: () => void;
}

export function ProjectHeader({
  project,
  canUpdate,
  canDelete,
  onEdit,
  onDelete,
}: ProjectHeaderProps) {
  return (
    <div className="overflow-hidden rounded-[12px] border border-[#d9ceb9] bg-[#16283f] shadow-[0_12px_30px_rgba(35,29,20,0.08)]">
      <div className="relative p-6 sm:p-7">
        <div className="absolute left-6 top-0 h-0.5 w-16 rounded-b-full bg-[#d9a441]" />

        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone="gold">
                PROJECT
              </Badge>

              <ProjectStatusBadge
                status={project.status}
              />
            </div>

            <h1 className="font-[Archivo] text-[28px] font-bold tracking-[-0.025em] text-white sm:text-[34px]">
              {project.name}
            </h1>

            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-[#bfc8d3]">
              {project.code ? (
                <span>
                  Code:{" "}
                  <span className="font-mono text-[#e5c77d]">
                    {project.code}
                  </span>
                </span>
              ) : null}

              {project.location ? (
                <span>
                  {project.location}
                </span>
              ) : null}
            </div>

            {project.description ? (
              <p className="mt-4 max-w-2xl text-[11.5px] leading-5 text-[#c7ced7]">
                {project.description}
              </p>
            ) : null}
          </div>

          <div className="flex shrink-0 gap-2">
            {canUpdate ? (
              <Button
                variant="ghost"
                onClick={onEdit}
              >
                <Icon
                  name="settings"
                  size={12}
                />
                Edit project
              </Button>
            ) : null}

            {canDelete ? (
              <Button
                variant="ghost"
                onClick={onDelete}
              >
                Delete
              </Button>
            ) : null}
          </div>
        </div>

        <div className="mt-7 grid gap-px overflow-hidden rounded-[9px] border border-white/10 bg-white/10 sm:grid-cols-3">
          <div className="bg-[#1b3049] p-4">
            <div className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#8291a4]">
              Start date
            </div>
            <div className="mt-1.5 text-[11.5px] font-semibold text-white">
              {formatProjectDate(
                project.start_date,
              )}
            </div>
          </div>

          <div className="bg-[#1b3049] p-4">
            <div className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#8291a4]">
              Expected completion
            </div>
            <div className="mt-1.5 text-[11.5px] font-semibold text-white">
              {formatProjectDate(
                project.expected_end_date,
              )}
            </div>
          </div>

          <div className="bg-[#1b3049] p-4">
            <div className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#8291a4]">
              Actual completion
            </div>
            <div className="mt-1.5 text-[11.5px] font-semibold text-white">
              {formatProjectDate(
                project.actual_end_date,
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
import { Link } from "react-router-dom";
import {Badge, Icon, Panel, PanelHeader, ProgressBar,
} from "./OrganizationUi";
import {formatProjectStatus, getProjectStatusTone, useProjectMilestones,
} from "../../projects";
import type { Project, ProjectStatus } from "../../projects";

const STATUS_PRIORITY: Record<ProjectStatus, number> = {
  ACTIVE: 0,
  ON_HOLD: 1,
  PLANNING: 2,
  COMPLETED: 3,
  CANCELLED: 4,
};

interface DashboardProjectHealthProps {
  projects: Project[];
  clientNameById: Map<string, string>;
}

export function DashboardProjectHealth({
  projects,
  clientNameById,
}: DashboardProjectHealthProps) {
  const visibleProjects = [...projects]
    .filter((project) => project.status !== "CANCELLED")
    .sort((a, b) => STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status])
    .slice(0, 6);

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="PROJECT HEALTH"
        title="Active work"
        description="Delivery status across your current project portfolio."
      />

      {visibleProjects.length === 0 ? (
        <div className="px-5 py-10 text-center text-[13px] text-[var(--color-text-secondary)] sm:px-6">
          No active projects yet. Create a project to see it tracked here.
        </div>
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {visibleProjects.map((project) => (
            <DashboardProjectRow
              key={project.id}
              project={project}
              clientName={project.client_id ? clientNameById.get(project.client_id) : undefined}
            />
          ))}
        </div>
      )}

      <div className="border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-3 sm:px-6">
        <Link
          to="/app/projects"
          className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline"
        >
          View all projects
          <Icon name="arrow" size={12} />
        </Link>
      </div>
    </Panel>
  );
}

interface DashboardProjectRowProps {
  project: Project;
  clientName?: string;
}

function DashboardProjectRow({ project, clientName }: DashboardProjectRowProps) {
  const milestonesQuery = useProjectMilestones(project.id);
  const milestones = milestonesQuery.data ?? [];
  const completed = milestones.filter((milestone) => milestone.completed_at !== null).length;
  const total = milestones.length;
  const percentage = total === 0 ? null : Math.round((completed / total) * 100);

  return (
    <Link
      to={`/app/projects/${project.id}`}
      className="flex flex-col gap-3 px-5 py-4 transition hover:bg-[var(--color-surface-muted)] sm:flex-row sm:items-center sm:justify-between sm:px-6"
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="truncate font-[Archivo] text-[14.5px] font-bold text-[var(--color-text-primary)]">
            {project.name}
          </span>
          <Badge tone={getProjectStatusTone(project.status)}>{formatProjectStatus(project.status)}</Badge>
        </div>

        <div className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
          {clientName ?? "No client"}
          {project.location ? ` · ${project.location}` : ""}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 sm:w-[180px]">
        {percentage === null ? (
          <span className="text-[11.5px] text-[var(--color-text-muted)]">No milestones set</span>
        ) : (
          <div className="w-full">
            <div className="mb-1 flex items-center justify-between text-[11px] font-semibold text-[var(--color-text-secondary)]">
              <span>{completed}/{total} milestones</span>
              <span>{percentage}%</span>
            </div>
            <ProgressBar value={percentage} tone={percentage === 100 ? "green" : "gold"} size="sm" />
          </div>
        )}
      </div>
    </Link>
  );
}
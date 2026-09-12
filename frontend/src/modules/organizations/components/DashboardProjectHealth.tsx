import { Link } from "react-router-dom";
import {Badge, Icon, Panel, PanelHeader, ProgressBar,
} from "./OrganizationUi";
import {formatProjectStatus, getProjectStatusTone, useProjectMilestones,
} from "../../projects";
import type { Project, ProjectStatus } from "../../projects";
import { useSitePhotos } from "../../whatsapp";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  const visibleProjects = [...projects]
    .filter((project) => project.status !== "CANCELLED")
    .sort((a, b) => STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status])
    .slice(0, 6);

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow={t("dashboard.projectHealth.eyebrow")}
        title={t("dashboard.projectHealth.title")}
        description={t("dashboard.projectHealth.description")}
      />

      {visibleProjects.length === 0 ? (
        <div className="px-5 py-10 text-center text-[13px] text-[var(--color-text-secondary)] sm:px-6">
          {t("dashboard.projectHealth.empty")}
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
          {t("dashboard.projectHealth.viewAll")}
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
  const { t } = useTranslation();
  const milestonesQuery = useProjectMilestones(project.id);
  const milestones = milestonesQuery.data ?? [];
  const completed = milestones.filter((milestone) => milestone.completed_at !== null).length;
  const total = milestones.length;
  const percentage = total === 0 ? null : Math.round((completed / total) * 100);

  return (
    <Link
      to={`/app/projects/${project.id}`}
      className="flex flex-col gap-3 px-5 py-4 outline-none transition hover:bg-[var(--color-surface-muted)] focus-visible:bg-[var(--color-surface-muted)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--color-trace-gold)] sm:flex-row sm:items-center sm:justify-between sm:px-6"
    >
      <div className="flex min-w-0 items-center gap-3">
        <DashboardProjectThumbnail projectId={project.id} />

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="truncate font-[Archivo] text-[14.5px] font-bold text-[var(--color-text-primary)]">
              {project.name}
            </span>
            <Badge tone={getProjectStatusTone(project.status)}>{formatProjectStatus(project.status)}</Badge>
          </div>

          <div className="mt-1 text-[12px] text-[var(--color-text-secondary)]">
            {clientName ?? t("dashboard.projectHealth.noClient")}
            {project.location ? ` · ${project.location}` : ""}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 sm:w-[180px]">
        {percentage === null ? (
          <span className="text-[11.5px] text-[var(--color-text-muted)]">{t("dashboard.projectHealth.noMilestones")}</span>
        ) : (
          <div className="w-full">
            <div className="mb-1 flex items-center justify-between text-[11px] font-semibold text-[var(--color-text-secondary)]">
              <span>{t("dashboard.projectHealth.milestones", { completed, total })}</span>
              <span>{percentage}%</span>
            </div>
            <ProgressBar value={percentage} tone={percentage === 100 ? "green" : "gold"} size="sm" />
          </div>
        )}
      </div>
    </Link>
  );
}

function DashboardProjectThumbnail({ projectId }: { projectId: string }) {
  const photosQuery = useSitePhotos({ projectId, limit: 1 });
  const photo = (photosQuery.data ?? [])[0];

  if (!photo) {
    return (
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]">
        <Icon name="site" size={16} />
      </div>
    );
  }

  return (
    <img
      src={photo.photo_url}
      alt=""
      className="h-12 w-12 shrink-0 rounded-[9px] border border-[var(--color-border)] object-cover"
      loading="lazy"
    />
  );
}
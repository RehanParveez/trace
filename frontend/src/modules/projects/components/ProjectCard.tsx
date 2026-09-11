import {DropdownMenu, Icon, ProgressBar,
} from "../../organizations/components/OrganizationUi";
import type { MenuAction } from "../../organizations/components/OrganizationUi";
import { formatRelativeTime } from "../../organizations/utils/organization.utils";
import { useBOQVersions, useBOQSummary } from "../../drawings_boq";
import { AUDIT_PERMISSIONS, useEntityAuditLog } from "../../audit";
import { BUDGET_PERMISSIONS, formatBudgetAmount, useProjectBudget } from "../../budgets";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useProjectMilestones } from "../hooks";
import type { Project } from "../types/project.types";
import { ProjectStatusBadge } from "./ProjectStatusBadge";

interface ProjectCardProps {
  project: Project;
  clientName?: string;
  canUpdate: boolean;
  canDelete: boolean;
  onOpen: (project: Project) => void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => void;
}

export function ProjectCard({
  project,
  clientName,
  canUpdate,
  canDelete,
  onOpen,
  onEdit,
  onDelete,
}: ProjectCardProps) {
  const permissions = usePermissionKeys();

  const canViewBoq = permissions.includes(IDENTITY_PERMISSIONS.DRAWING_READ);
  const canViewActivity = permissions.includes(AUDIT_PERMISSIONS.AUDIT_LOG_READ);
  const canViewBudget = permissions.includes(BUDGET_PERMISSIONS.BUDGET_READ);

  const milestonesQuery = useProjectMilestones(project.id);
  const budgetQuery = useProjectBudget(canViewBudget ? project.id : undefined);
  const boqVersionsQuery = useBOQVersions(canViewBoq ? project.id : "");
  const latestVersionId = boqVersionsQuery.data?.[0]?.id;
  const boqSummaryQuery = useBOQSummary(latestVersionId);
  const activityQuery = useEntityAuditLog(
    "PROJECT",
    canViewActivity ? project.id : undefined,
  );

  const milestones = milestonesQuery.data ?? [];
  const completed = milestones.filter((milestone) => milestone.completed_at !== null).length;
  const total = milestones.length;
  const percentage = total === 0 ? null : Math.round((completed / total) * 100);

  const boqItemCount = boqSummaryQuery.data?.item_count ?? null;

  const latestActivity = activityQuery.data?.[0];
  const lastActivityLabel = !canViewActivity
    ? "—"
    : latestActivity
      ? formatRelativeTime(latestActivity.created_at)
      : "No activity yet";

  const actions: MenuAction[] = [];

  if (canUpdate) {
    actions.push({ label: "Edit project", icon: "edit", onSelect: () => onEdit(project) });
  }

  if (canDelete) {
    actions.push({ label: "Delete project", icon: "x", tone: "danger", onSelect: () => onDelete(project) });
  }

  return (
    <div className="relative rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition hover:border-[var(--color-border-strong)] hover:shadow-[0_8px_22px_rgba(90,70,40,0.06)]">
      {actions.length > 0 ? (
        <div className="absolute right-3 top-3 z-10">
          <DropdownMenu items={actions} />
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => onOpen(project)}
        className="block w-full rounded-[var(--radius-md)] text-left outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)] focus-visible:ring-offset-2"
      >
        <div className="pr-8">
          <div className="flex flex-wrap items-center gap-2">
            <span className="truncate font-[Archivo] text-[16px] font-bold text-[var(--color-text-primary)]">
              {project.name}
            </span>
            <ProjectStatusBadge status={project.status} />
          </div>

          <div className="mt-1 truncate text-[12px] text-[var(--color-text-secondary)]">
            {clientName ?? "No client"}
            {project.location ? ` · ${project.location}` : ""}
          </div>
        </div>

        <div className="mt-4 space-y-3 border-t border-[var(--color-border)] pt-4">
          <div>
            <div className="mb-1.5 flex items-center justify-between gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
                Progress
              </span>
              <span className="font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">
                {percentage === null ? "—" : `${percentage}%`}
              </span>
            </div>
            {percentage !== null ? (
              <ProgressBar value={percentage} tone={percentage === 100 ? "green" : "gold"} size="sm" />
            ) : (
              <div className="text-[11.5px] text-[var(--color-text-muted)]">No milestones set</div>
            )}
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
              Budget
            </span>
            <span className="font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">
              {!canViewBudget
                ? "—"
                : budgetQuery.data
                  ? formatBudgetAmount(budgetQuery.data.approved_amount, budgetQuery.data.currency)
                  : "Not set"}
            </span>
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
              BOQ items
            </span>
            <span className="font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">
              {boqItemCount === null ? "—" : boqItemCount}
            </span>
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
              Last activity
            </span>
            <span className="text-[12px] text-[var(--color-text-secondary)]">{lastActivityLabel}</span>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--color-trace-gold-dark)]">
          Open project
          <Icon name="arrow" size={12} />
        </div>
      </button>
    </div>
  );
}
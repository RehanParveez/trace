import {DropdownMenu, Icon, ProgressBar,
} from "../../organizations/components/OrganizationUi";
import type { MenuAction } from "../../organizations/components/OrganizationUi";
import { formatRelativeTime } from "../../organizations/utils/organization.utils";
import { formatBudgetAmount } from "../../budgets";
import type { Project } from "../types/project.types";
import { ProjectStatusBadge } from "./ProjectStatusBadge";
import { useTranslation } from "react-i18next";

interface ProjectCardMilestoneSummary {
  total: number;
  completed: number;
}

interface ProjectCardBudgetSummary {
  approvedAmount: number | string;
  currency: string;
}

interface ProjectCardActivitySummary {
  summary: string;
  createdAt: string;
}

interface ProjectCardProps {
  project: Project;
  clientName?: string;
  canUpdate: boolean;
  canDelete: boolean;
  milestoneSummary?: ProjectCardMilestoneSummary;
  boqItemCount?: number | null;
  budgetSummary?: ProjectCardBudgetSummary | null;
  lastActivity?: ProjectCardActivitySummary | null;
  onOpen: (project: Project) => void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => void;
}

export function ProjectCard({
  project,
  clientName,
  canUpdate,
  canDelete,
  milestoneSummary,
  boqItemCount,
  budgetSummary,
  lastActivity,
  onOpen,
  onEdit,
  onDelete,
}: ProjectCardProps) {
  const { t } = useTranslation();

  const hasMilestoneData = Boolean(milestoneSummary);
  const percentage =
    milestoneSummary && milestoneSummary.total > 0
      ? Math.round(
          (milestoneSummary.completed / milestoneSummary.total) * 100,
        )
      : null;

  const actions: MenuAction[] = [];

  if (canUpdate) {
    actions.push({
      label: t("projects.card.edit"),
      icon: "edit",
      onSelect: () => onEdit(project),
    });
  }

  if (canDelete) {
    actions.push({
      label: t("projects.card.delete"),
      icon: "x",
      tone: "danger",
      onSelect: () => onDelete(project),
    });
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
            {clientName ?? t("projects.card.noClient")}
            {project.location ? ` · ${project.location}` : ""}
          </div>
        </div>

        <div className="mt-4 space-y-3 border-t border-[var(--color-border)] pt-4">
          <div>
            <div className="mb-1.5 flex items-center justify-between gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
                {t("projects.card.progress")}
              </span>
              <span className="font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">
                {!hasMilestoneData || percentage === null
                  ? "—"
                  : `${percentage}%`}
              </span>
            </div>
            {hasMilestoneData && percentage !== null ? (
              <ProgressBar
                value={percentage}
                tone={percentage === 100 ? "green" : "gold"}
                size="sm"
              />
            ) : (
              <div className="text-[11.5px] text-[var(--color-text-muted)]">
                {hasMilestoneData
                  ? t("projects.card.noMilestones")
                  : "—"}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
              {t("projects.card.budget")}
            </span>
            <span className="font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">
              {budgetSummary === undefined
                ? "—"
                : budgetSummary === null
                  ? t("projects.card.notSet")
                  : formatBudgetAmount(
                      budgetSummary.approvedAmount,
                      budgetSummary.currency,
                    )}
            </span>
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
              {t("projects.card.boqItems")}
            </span>
            <span className="font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">
              {boqItemCount === undefined || boqItemCount === null
                ? "—"
                : boqItemCount}
            </span>
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
              {t("projects.card.lastActivity")}
            </span>
            <span className="text-[12px] text-[var(--color-text-secondary)]">
              {lastActivity === undefined
                ? "—"
                : lastActivity === null
                  ? t("projects.card.noActivity")
                  : formatRelativeTime(lastActivity.createdAt)}
            </span>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--color-trace-gold-dark)]">
          {t("projects.card.open")}
          <Icon name="arrow" size={12} />
        </div>
      </button>
    </div>
  );
}
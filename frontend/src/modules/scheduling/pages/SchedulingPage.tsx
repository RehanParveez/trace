import { useState } from "react";
import { Badge, Button, ErrorState, Field, inputClass, LoadingState, PageHeader, StatCard } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { SCHEDULING_PERMISSIONS } from "../permissions";
import { useProjectSchedule, useUpdateScheduleSettings } from "../hooks";
import { ScheduleTaskForm } from "../components/ScheduleTaskForm";
import { GanttChart } from "../components/GanttChart";
import { ScheduleTaskDetailDialog } from "../components/ScheduleTaskDetailDialog";
import { formatScheduleDate } from "../utils/scheduling.utils";
import type { ScheduleTaskComputed } from "../types/scheduling.types";
import { useTranslation } from "react-i18next";

export function SchedulingPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(SCHEDULING_PERMISSIONS.SCHEDULE_READ);
  const canManage = permissions.includes(SCHEDULING_PERMISSIONS.SCHEDULE_MANAGE);

  const projectsQuery = useProjects();
  const [projectId, setProjectId] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<ScheduleTaskComputed | null>(null);
  const updateSettings = useUpdateScheduleSettings(projectId);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";
  const scheduleQuery = useProjectSchedule(activeProjectId);
  const { t } = useTranslation();

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("scheduling.page.accessUnavailable")} description={t("scheduling.page.accessUnavailableDesc")} />;
  }
  if (projectsQuery.isLoading) return <LoadingState label={t("scheduling.page.loadingProjects")} />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title={t("scheduling.page.loadProjectsError")} onRetry={() => void projectsQuery.refetch()} />;

  const schedule = scheduleQuery.data;
  const criticalCount = schedule?.tasks.filter((t) => t.is_critical).length ?? 0;

  return (
    <div className="space-y-7">
     <PageHeader title={t("scheduling.page.title")} description={t("scheduling.page.description")} />

      {projects.length === 0 ? (
        <ErrorState title={t("scheduling.page.noProjects")} description={t("scheduling.page.noProjectsDesc")} />
      ) : (
        <>
          <Field label={t("scheduling.page.project")}>
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>

          {scheduleQuery.isLoading ? (
            <LoadingState label={t("scheduling.page.loading")} />
          ) : schedule ? (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard label={t("scheduling.stat.projectedFinish")} value={formatScheduleDate(schedule.natural_completion_date)} note={t("scheduling.stat.projectedFinishNote")} icon="check" tone="blue" />
                <StatCard
                  label={t("scheduling.stat.targetCompletion")}
                  value={schedule.target_completion_date ? formatScheduleDate(schedule.target_completion_date) : t("scheduling.stat.targetNotSet")}
                  note={
                    schedule.days_ahead_or_behind_target === null
                      ? t("scheduling.stat.setTarget")
                      : schedule.days_ahead_or_behind_target >= 0
                        ? t("scheduling.stat.daysBuffer", { count: schedule.days_ahead_or_behind_target })
                        : t("scheduling.stat.daysLate", { count: Math.abs(schedule.days_ahead_or_behind_target) })
                  }
                  icon="alert"
                  tone={schedule.days_ahead_or_behind_target === null ? "blue" : schedule.days_ahead_or_behind_target >= 0 ? "green" : "red"}
                />
                <StatCard label={t("scheduling.stat.criticalTasks")} value={criticalCount} note={t("scheduling.stat.criticalNote")} icon="site" tone={criticalCount > 0 ? "gold" : "green"} />
              </div>

              {canManage ? (
                <div className="flex flex-wrap items-end gap-3">
                  <Field label={t("scheduling.settings.targetDate")} hint={t("scheduling.settings.targetHint")}>
                    <input
                      type="date"
                      className={inputClass}
                      defaultValue={schedule.target_completion_date ?? ""}
                      onBlur={(e) => updateSettings.mutate(e.target.value || null)}
                    />
                  </Field>
                  <Button variant="primary" onClick={() => setFormOpen(true)}>{t("scheduling.settings.addTask")}</Button>
                </div>
              ) : null}

              {schedule.warnings.length > 0 ? (
                <div className="space-y-1.5 rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3.5 py-3">
                  {schedule.warnings.map((w, i) => <p key={i} className="text-[12px] text-[var(--color-warning)]">{w}</p>)}
                </div>
              ) : null}

              <GanttChart tasks={schedule.tasks} targetCompletionDate={schedule.target_completion_date} onSelectTask={setSelectedTask} />
            </>
          ) : null}

          {formOpen ? <ScheduleTaskForm projectId={activeProjectId} existingTasks={schedule?.tasks ?? []} onClose={() => setFormOpen(false)} /> : null}
          {selectedTask ? <ScheduleTaskDetailDialog projectId={activeProjectId} task={selectedTask} canManage={canManage} onClose={() => setSelectedTask(null)} /> : null}
        </>
      )}
    </div>
  );
}
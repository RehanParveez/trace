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

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Schedule unavailable" description="You don't have permission to view the project schedule." />;
  }
  if (projectsQuery.isLoading) return <LoadingState label="Loading projects…" />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;

  const schedule = scheduleQuery.data;
  const criticalCount = schedule?.tasks.filter((t) => t.is_critical).length ?? 0;

  return (
    <div className="space-y-7">
      <PageHeader title="Schedule" description="Task timeline with dependencies and the critical path — the chain of tasks that determines your finish date." />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first." />
      ) : (
        <>
          <Field label="Project">
            <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>

          {scheduleQuery.isLoading ? (
            <LoadingState label="Loading schedule…" />
          ) : schedule ? (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard label="Projected finish" value={formatScheduleDate(schedule.natural_completion_date)} note="Based on the current critical path" icon="check" tone="blue" />
                <StatCard
                  label="Target completion"
                  value={schedule.target_completion_date ? formatScheduleDate(schedule.target_completion_date) : "Not set"}
                  note={
                    schedule.days_ahead_or_behind_target === null ? "Set a target to compare"
                    : schedule.days_ahead_or_behind_target >= 0 ? `${schedule.days_ahead_or_behind_target} day(s) of buffer`
                    : `${Math.abs(schedule.days_ahead_or_behind_target)} day(s) projected late`
                  }
                  icon="alert"
                  tone={schedule.days_ahead_or_behind_target === null ? "blue" : schedule.days_ahead_or_behind_target >= 0 ? "green" : "red"}
                />
                <StatCard label="Critical tasks" value={criticalCount} note="Any delay here delays the finish date" icon="site" tone={criticalCount > 0 ? "gold" : "green"} />
              </div>

              {canManage ? (
                <div className="flex flex-wrap items-end gap-3">
                  <Field label="Target completion date" hint="Optional — compares your promised date against the critical path">
                    <input
                      type="date"
                      className={inputClass}
                      defaultValue={schedule.target_completion_date ?? ""}
                      onBlur={(e) => updateSettings.mutate(e.target.value || null)}
                    />
                  </Field>
                  <Button variant="primary" onClick={() => setFormOpen(true)}>Add task</Button>
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
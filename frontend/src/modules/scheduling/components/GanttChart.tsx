import { Badge, Icon } from "../../organizations/components/OrganizationUi";
import type { ScheduleTaskComputed } from "../types/scheduling.types";
import { daysBetween, formatScheduleDate } from "../utils/scheduling.utils";

const DAY_WIDTH_PX = 12;
const ROW_HEIGHT_PX = 40;

interface GanttChartProps {
  tasks: ScheduleTaskComputed[];
  targetCompletionDate: string | null;
  onSelectTask: (task: ScheduleTaskComputed) => void;
}

export function GanttChart({ tasks, targetCompletionDate, onSelectTask }: GanttChartProps) {
  const computable = tasks.filter((t) => t.is_computable && t.earliest_start && t.earliest_finish);

  if (computable.length === 0) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-8 text-center text-[13px] text-[var(--color-text-secondary)]">
        No tasks have a computable date yet — add at least one root task with a planned start date to see the timeline.
      </div>
    );
  }

  const allDates = computable.flatMap((t) => [t.earliest_start as string, t.earliest_finish as string]);
  if (targetCompletionDate) allDates.push(targetCompletionDate);
  const rangeStart = allDates.reduce((min, d) => (d < min ? d : min), allDates[0]);
  const rangeEnd = allDates.reduce((max, d) => (d > max ? d : max), allDates[0]);
  const totalDays = Math.max(daysBetween(rangeStart, rangeEnd) + 1, 1);
  const chartWidth = totalDays * DAY_WIDTH_PX;

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="flex min-w-max">
        <div className="sticky left-0 z-10 w-[220px] shrink-0 border-r border-[var(--color-border)] bg-[var(--color-surface)]">
          <div className="flex h-9 items-center border-b border-[var(--color-border)] px-3 text-[11px] font-bold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">
            Task
          </div>
          {tasks.map((task) => (
            <button
              key={task.id}
              type="button"
              onClick={() => onSelectTask(task)}
              style={{ height: ROW_HEIGHT_PX }}
              className="flex w-full items-center gap-1.5 border-b border-[var(--color-border)] px-3 text-left text-[12.5px] font-medium text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-muted)]"
            >
              {task.is_milestone_marker ? <Icon name="check" size={11} className="shrink-0 text-[var(--color-trace-gold-dark)]" /> : null}
              <span className="truncate">{task.name}</span>
            </button>
          ))}
        </div>

        <div className="relative" style={{ width: chartWidth }}>
          <div className="flex h-9 items-center border-b border-[var(--color-border)] px-2 text-[11px] text-[var(--color-text-muted)]">
            {formatScheduleDate(rangeStart)} — {formatScheduleDate(rangeEnd)}
          </div>

          {targetCompletionDate ? (
            <div
              className="absolute top-9 bottom-0 z-10 w-px bg-[var(--color-danger)]"
              style={{ left: daysBetween(rangeStart, targetCompletionDate) * DAY_WIDTH_PX }}
              title={`Target completion: ${formatScheduleDate(targetCompletionDate)}`}
            />
          ) : null}

          {tasks.map((task) => {
            if (!task.is_computable || !task.earliest_start || !task.earliest_finish) {
              return (
                <div key={task.id} style={{ height: ROW_HEIGHT_PX }} className="flex items-center border-b border-[var(--color-border)] px-2">
                  <Badge tone="slate">Not yet schedulable</Badge>
                </div>
              );
            }

            const left = daysBetween(rangeStart, task.earliest_start) * DAY_WIDTH_PX;
            const width = Math.max((daysBetween(task.earliest_start, task.earliest_finish) + 1) * DAY_WIDTH_PX, DAY_WIDTH_PX);
            const floatWidth = task.total_float_days && task.total_float_days > 0 ? task.total_float_days * DAY_WIDTH_PX : 0;

            return (
              <div key={task.id} style={{ height: ROW_HEIGHT_PX }} className="relative border-b border-[var(--color-border)]">
                <div
                  onClick={() => onSelectTask(task)}
                  title={`${task.name} · ${formatScheduleDate(task.earliest_start)} – ${formatScheduleDate(task.earliest_finish)}${task.is_critical ? " · Critical path" : ""}`}
                  className={`absolute top-2 flex cursor-pointer items-center rounded-[5px] px-2 text-[10.5px] font-semibold text-white transition hover:brightness-110 ${
                    task.status === "COMPLETE"
                      ? "bg-[var(--color-success)]"
                      : task.is_critical
                        ? "bg-[var(--color-danger)]"
                        : "bg-[var(--color-trace-gold-dark)]"
                  }`}
                  style={{ left, width, height: ROW_HEIGHT_PX - 16 }}
                >
                  {Number(task.percent_complete) > 0 ? (
                    <div
                      className="absolute inset-y-0 left-0 rounded-l-[5px] bg-black/20"
                      style={{ width: `${Math.min(Number(task.percent_complete), 100)}%` }}
                    />
                  ) : null}
                  <span className="relative truncate">{task.is_milestone_marker ? "◆" : `${Math.round(Number(task.percent_complete))}%`}</span>
                </div>
                {floatWidth > 0 ? (
                  <div
                    className="absolute top-4 h-2 rounded-[3px] bg-[var(--color-border)]"
                    style={{ left: left + width, width: floatWidth }}
                    title={`${task.total_float_days} day(s) of float`}
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
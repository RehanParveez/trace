import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateTask } from "../hooks";
import type { ScheduleTaskComputed } from "../types/scheduling.types";

export function ScheduleTaskForm({ projectId, existingTasks, onClose }: {
  projectId: string; existingTasks: ScheduleTaskComputed[]; onClose: () => void;
}) {
  const createTask = useCreateTask(projectId);
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState("1");
  const [startDate, setStartDate] = useState("");
  const [isMilestone, setIsMilestone] = useState(false);
  const [predecessorIds, setPredecessorIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const hasPredecessors = predecessorIds.length > 0;

  function togglePredecessor(id: string) {
    setPredecessorIds((cur) => (cur.includes(id) ? cur.filter((p) => p !== id) : [...cur, id]));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createTask.mutate(
      {
        name: name.trim(), description: description.trim() || null,
        planned_start_date: hasPredecessors ? null : (startDate || null),
        planned_duration_days: isMilestone ? 0 : Number(duration),
        is_milestone_marker: isMilestone, predecessor_task_ids: predecessorIds,
      },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "Task added to schedule" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't add this task.")),
      },
    );
  }

  return (
    <Modal title="Add schedule task" description="A task with predecessors is scheduled automatically once they finish. A task with no predecessors needs its own start date." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Task name"><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Excavation, Foundation pour" /></Field>
        <Field label="Description"><textarea className={`${inputClass} resize-y`} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>

        <label className="flex items-center gap-2.5">
          <input type="checkbox" checked={isMilestone} onChange={(e) => setIsMilestone(e.target.checked)} className="h-4 w-4 accent-[var(--color-trace-gold)]" />
          <span className="text-[13px] text-[var(--color-text-primary)]">This is a zero-duration milestone marker (a key date, not a task with duration)</span>
        </label>

        {!isMilestone ? (
          <Field label="Duration (days)"><input type="number" min="1" required className={inputClass} value={duration} onChange={(e) => setDuration(e.target.value)} /></Field>
        ) : null}

        <div>
          <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.04em] text-[var(--color-text-secondary)]">Depends on (predecessors)</div>
          {existingTasks.length === 0 ? (
            <p className="text-[12.5px] text-[var(--color-text-muted)]">No other tasks yet — this will be a root task with its own start date.</p>
          ) : (
            <div className="max-h-40 space-y-1.5 overflow-y-auto rounded-[8px] border border-[var(--color-border)] p-2">
              {existingTasks.map((task) => (
                <label key={task.id} className="flex items-center gap-2.5 rounded-[6px] px-2 py-1.5 hover:bg-[var(--color-surface-muted)]">
                  <input type="checkbox" checked={predecessorIds.includes(task.id)} onChange={() => togglePredecessor(task.id)} className="h-4 w-4 accent-[var(--color-trace-gold)]" />
                  <span className="text-[13px] text-[var(--color-text-primary)]">{task.name}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {!hasPredecessors ? (
          <Field label="Planned start date" hint="Required since this task has no predecessors"><input type="date" required className={inputClass} value={startDate} onChange={(e) => setStartDate(e.target.value)} /></Field>
        ) : (
          <p className="rounded-[8px] border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] px-3 py-2 text-[12px] text-[var(--color-info)]">Start date will be calculated automatically once the selected predecessor(s) finish.</p>
        )}

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createTask.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createTask.isPending || !name.trim() || (!hasPredecessors && !startDate)}>{createTask.isPending ? "Adding…" : "Add task"}</Button>
        </div>
      </form>
    </Modal>
  );
}
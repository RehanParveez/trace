import { useState } from "react";
import { Badge, Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useDeleteTask, useUpdateTask } from "../hooks";
import type { ScheduleTaskComputed } from "../types/scheduling.types";
import { formatScheduleDate } from "../utils/scheduling.utils";

export function ScheduleTaskDetailDialog({ projectId, task, canManage, onClose }: {
  projectId: string; task: ScheduleTaskComputed; canManage: boolean; onClose: () => void;
}) {
  const updateTask = useUpdateTask(projectId);
  const deleteTask = useDeleteTask(projectId);
  const { showToast } = useToast();
  const [percentComplete, setPercentComplete] = useState(String(task.percent_complete));
  const [actualStart, setActualStart] = useState(task.actual_start_date ?? "");
  const [actualEnd, setActualEnd] = useState(task.actual_end_date ?? "");
  const [error, setError] = useState<string | null>(null);

  function saveProgress() {
    setError(null);
    updateTask.mutate(
      { taskId: task.id, payload: { percent_complete: Number(percentComplete), actual_start_date: actualStart || null, actual_end_date: actualEnd || null } },
      { onSuccess: () => showToast({ tone: "success", title: "Progress updated" }), onError: (e) => setError(getApiErrorMessage(e, "Couldn't update this task.")) },
    );
  }

  return (
    <Modal title={task.name} description={task.description ?? undefined} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge tone={task.status === "COMPLETE" ? "green" : task.status === "IN_PROGRESS" ? "blue" : "slate"}>{task.status.replace("_", " ")}</Badge>
          {task.is_critical ? <Badge tone="red">On critical path</Badge> : null}
          {task.total_float_days !== null && task.total_float_days > 0 ? <Badge tone="slate">{task.total_float_days} day(s) float</Badge> : null}
        </div>

        <div className="grid grid-cols-2 gap-3 text-[12.5px]">
          <div><span className="text-[var(--color-text-muted)]">Earliest start</span><div className="font-semibold text-[var(--color-text-primary)]">{formatScheduleDate(task.earliest_start)}</div></div>
          <div><span className="text-[var(--color-text-muted)]">Earliest finish</span><div className="font-semibold text-[var(--color-text-primary)]">{formatScheduleDate(task.earliest_finish)}</div></div>
          <div><span className="text-[var(--color-text-muted)]">Latest start</span><div className="font-semibold text-[var(--color-text-primary)]">{formatScheduleDate(task.latest_start)}</div></div>
          <div><span className="text-[var(--color-text-muted)]">Latest finish</span><div className="font-semibold text-[var(--color-text-primary)]">{formatScheduleDate(task.latest_finish)}</div></div>
        </div>

        {canManage ? (
          <div className="space-y-3 border-t border-[var(--color-border)] pt-4">
            <Field label="Percent complete"><input type="number" min="0" max="100" className={inputClass} value={percentComplete} onChange={(e) => setPercentComplete(e.target.value)} /></Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Actual start"><input type="date" className={inputClass} value={actualStart} onChange={(e) => setActualStart(e.target.value)} /></Field>
              <Field label="Actual finish"><input type="date" className={inputClass} value={actualEnd} onChange={(e) => setActualEnd(e.target.value)} /></Field>
            </div>
            {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
            <div className="flex justify-between gap-2">
              <Button variant="danger" size="sm" disabled={deleteTask.isPending} onClick={() => { if (window.confirm(`Remove "${task.name}" from the schedule?`)) deleteTask.mutate(task.id, { onSuccess: onClose }); }}>Remove task</Button>
              <Button variant="primary" disabled={updateTask.isPending} onClick={saveProgress}>{updateTask.isPending ? "Saving…" : "Save progress"}</Button>
            </div>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
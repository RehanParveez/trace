import { useState } from "react";
import type { FormEvent } from "react";
import {
  Button, Field, inputClass, Modal,
} from "../../organizations/components/OrganizationUi";
import {
  useCreateMilestone, useUpdateMilestone,
} from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type { Milestone } from "../types/project.types";

interface MilestoneFormProps {
  projectId: string;
  milestone?: Milestone;
  onClose: () => void;
}

export function MilestoneForm({
  projectId,
  milestone,
  onClose,
}: MilestoneFormProps) {
  const createMilestone = useCreateMilestone();
  const updateMilestone = useUpdateMilestone();

  const [name, setName] = useState(milestone?.name ?? "");
  const [description, setDescription] = useState(milestone?.description ?? "");
  const [dueDate, setDueDate] = useState(milestone?.due_date ?? "");
  const [completed, setCompleted] = useState(Boolean(milestone?.completed_at));
  const [error, setError] = useState<string | null>(null);

  const editing = Boolean(milestone);
  const isSubmitting = createMilestone.isPending || updateMilestone.isPending;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (editing && milestone) {
      updateMilestone.mutate(
        {
          projectId,
          milestoneId: milestone.id,
          payload: {
            name: name.trim(),
            description: description.trim() || null,
            due_date: dueDate || null,
            completed_at: completed
              ? (milestone.completed_at ?? new Date().toISOString().slice(0, 10))
              : null,
          },
        },
        {
          onSuccess: onClose,
          onError: (mutationError) =>
            setError(getApiErrorMessage(mutationError, "Couldn't save this milestone. Please try again.")),
        },
      );

      return;
    }

    createMilestone.mutate(
      {
        projectId,
        payload: {
          name: name.trim(),
          description: description.trim() || null,
          due_date: dueDate || null,
        },
      },
      {
        onSuccess: onClose,
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, "Couldn't add this milestone. Please try again.")),
      },
    );
  }

  return (
    <Modal
      title={editing ? "Edit milestone" : "Add milestone"}
      description="Delivery checkpoint tracked against this project's timeline."
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-5">
        <Field label="Milestone name">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            placeholder="Foundation complete"
            className={inputClass}
          />
        </Field>

        <Field label="Description">
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            placeholder="Milestone details"
            className={`${inputClass} resize-y`}
          />
        </Field>

        <Field label="Due date">
          <input
            type="date"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
            className={inputClass}
          />
        </Field>

        {editing ? (
          <label className="flex items-center gap-2.5">
            <input
              type="checkbox"
              checked={completed}
              onChange={(event) => setCompleted(event.target.checked)}
              className="h-4 w-4 accent-[var(--color-trace-gold)]"
            />
            <span className="text-[13px] text-[var(--color-text-primary)]">Mark as completed</span>
          </label>
        ) : null}

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>

          <Button type="submit" variant="primary" disabled={isSubmitting || !name.trim()}>
            {isSubmitting ? "Saving…" : editing ? "Save changes" : "Add milestone"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
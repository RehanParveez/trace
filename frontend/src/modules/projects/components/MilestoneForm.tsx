import { useState } from "react";
import type { FormEvent } from "react";
import {
  Button, Field, inputClass, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import {
  useCreateMilestone, useUpdateMilestone,
} from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type { Milestone } from "../types/project.types";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  const createMilestone = useCreateMilestone();
  const updateMilestone = useUpdateMilestone();
  const { showToast } = useToast();

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
          onSuccess: () => {
            onClose();
            showToast({ tone: "success", title: t("milestones.form.updatedToast") });
          },
          onError: (mutationError) =>
            setError(getApiErrorMessage(mutationError, t("milestones.form.saveError"))),
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
        onSuccess: () => {
          onClose();
          showToast({ tone: "success", title: t("milestones.form.createdToast") });
        },
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, t("milestones.form.createError"))),
      },
    );
  }

  return (
    <Modal
      title={editing ? t("milestones.form.editTitle") : t("milestones.form.addTitle")}
      description={t("milestones.form.description")}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-5">
        <Field label={t("milestones.form.name")}>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            placeholder={t("milestones.form.namePlaceholder")}
            className={inputClass}
          />
        </Field>

        <Field label={t("milestones.form.descriptionLabel")}>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            placeholder={t("milestones.form.descriptionPlaceholder")}
            className={`${inputClass} resize-y`}
          />
        </Field>

        <Field label={t("milestones.form.dueDate")}>
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
            <span className="text-[13px] text-[var(--color-text-primary)]">
              {t("milestones.form.markCompleted")}
            </span>
          </label>
        ) : null}

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
            {t("common.cancel")}
          </Button>

          <Button type="submit" variant="primary" disabled={isSubmitting || !name.trim()}>
            {isSubmitting
              ? t("common.saving")
              : editing
                ? t("common.saveChanges")
                : t("milestones.form.addButton")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
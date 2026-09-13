import { useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, inputClass, Modal,
} from "../../organizations/components/OrganizationUi";
import { useAddProjectMember } from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type { ProjectMemberRole } from "../types/project.types";
import { useTranslation } from "react-i18next";

const roles: ProjectMemberRole[] = [
  "MANAGER",
  "ENGINEER",
  "SUPERVISOR",
  "SITE_MANAGER",
  "MEMBER",
];

interface ProjectMemberDialogProps {
  projectId: string;
  onClose: () => void;
}

export function ProjectMemberDialog({
  projectId,
  onClose,
}: ProjectMemberDialogProps) {
  const { t } = useTranslation();
  const addMember = useAddProjectMember();

  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<ProjectMemberRole>("MEMBER");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    addMember.mutate(
      {
        projectId,
        payload: {
          user_id: userId.trim(),
          role,
        },
      },
      {
        onSuccess: onClose,
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, t("projects.members.addError")))
      },
    );
  }

  return (
    <Modal
      title={t("projects.members.addTitle")}
      description={t("projects.members.addDescription")}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-5">
        <Field label={t("projects.members.userId")} hint={t("projects.members.userIdHint")}>
          <input
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            placeholder={t("projects.members.userIdPlaceholder")}
            required
            className={`${inputClass} font-mono`}
          />
        </Field>

        <Field label={t("projects.members.role")}>
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as ProjectMemberRole)}
            className={inputClass}
          >
            {roles.map((item) => (
              <option key={item} value={item}>
                {item.replace("_", " ")}
              </option>
            ))}
          </select>
        </Field>

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={addMember.isPending}>
            {t("common.cancel")}
          </Button>

          <Button type="submit" variant="primary" disabled={addMember.isPending || !userId.trim()}>
            {addMember.isPending ? t("projects.members.adding") : t("projects.members.addButton")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
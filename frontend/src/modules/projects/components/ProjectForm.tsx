import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, inputClass, Modal,
} from "../../organizations/components/OrganizationUi";
import { QuotaLimitNotice, useQuotaStatus } from "../../subscriptions";
import {useCreateProject, useUpdateProject,
} from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type {Client, Project, ProjectStatus,
} from "../types/project.types";
import { useTranslation } from "react-i18next";

interface ProjectFormProps {
  project?: Project;
  clients: Client[];
  isSubmitting?: boolean;
  onClose: () => void;
}

const statuses: ProjectStatus[] = [
  "PLANNING",
  "ACTIVE",
  "ON_HOLD",
  "COMPLETED",
  "CANCELLED",
];

export function ProjectForm({
  project,
  clients,
  onClose,
}: ProjectFormProps) {
  const { t } = useTranslation();
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();

  const editing = Boolean(project);
  const projectQuota = useQuotaStatus("projects");
  const blockedByQuota = !editing && projectQuota.isAtLimit;

  const [name, setName] = useState(project?.name ?? "");
  const [code, setCode] = useState(project?.code ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [clientId, setClientId] = useState(project?.client_id ?? "");
  const [location, setLocation] = useState(project?.location ?? "");
  const [status, setStatus] = useState<ProjectStatus>(project?.status ?? "PLANNING");
  const [startDate, setStartDate] = useState(project?.start_date ?? "");
  const [expectedEndDate, setExpectedEndDate] = useState(project?.expected_end_date ?? "");
  const [actualEndDate, setActualEndDate] = useState(project?.actual_end_date ?? "");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!project) {
      return;
    }

    setName(project.name);
    setCode(project.code ?? "");
    setDescription(project.description ?? "");
    setClientId(project.client_id ?? "");
    setLocation(project.location ?? "");
    setStatus(project.status);
    setStartDate(project.start_date ?? "");
    setExpectedEndDate(project.expected_end_date ?? "");
    setActualEndDate(project.actual_end_date ?? "");
  }, [project]);

  const isSubmitting = createProject.isPending || updateProject.isPending;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (editing && project) {
      updateProject.mutate(
        {
          projectId: project.id,
          payload: {
            name: name.trim(),
            code: code.trim() || null,
            description: description.trim() || null,
            client_id: clientId || null,
            location: location.trim() || null,
            status,
            start_date: startDate || null,
            expected_end_date: expectedEndDate || null,
            actual_end_date: actualEndDate || null,
          },
        },
        {
          onSuccess: onClose,
          onError: (mutationError) =>
            setError(getApiErrorMessage(mutationError, t("projects.form.saveError")))
        },
      );

      return;
    }

    createProject.mutate(
      {
        name: name.trim(),
        code: code.trim() || null,
        description: description.trim() || null,
        client_id: clientId || null,
        location: location.trim() || null,
        start_date: startDate || null,
        expected_end_date: expectedEndDate || null,
      },
      {
        onSuccess: onClose,
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, t("projects.form.createError")))
      },
    );
  }

  return (
    <Modal
      title={editing ? t("projects.form.editTitle") : t("projects.form.createTitle")}
      description={t("projects.form.description")}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("projects.form.name")}>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              placeholder={t("projects.form.namePlaceholder")}
              className={inputClass}
            />
          </Field>

          <Field label={t("projects.form.code")}>
            <input
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder={t("projects.form.codePlaceholder")}
              className={inputClass}
            />
          </Field>
        </div>

        <Field label={t("projects.form.descriptionLabel")}>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            placeholder={t("projects.form.descriptionPlaceholder")}
            className={`${inputClass} resize-y`}
          />
        </Field>

        <div className={`grid gap-4 ${editing ? "sm:grid-cols-2" : "sm:grid-cols-1"}`}>
          <Field label={t("projects.form.client")}>
            <select
              value={clientId}
              onChange={(event) => setClientId(event.target.value)}
              className={inputClass}
            >
              <option value="">{t("projects.form.noClient")}</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </Field>

          {editing ? (
            <Field label={t("projects.form.status")}>
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value as ProjectStatus)}
                className={inputClass}
              >
                {statuses.map((projectStatus) => (
                  <option key={projectStatus} value={projectStatus}>
                    {projectStatus.replace("_", " ")}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
        </div>

        <Field label={t("projects.form.location")}>
          <input
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder={t("projects.form.locationPlaceholder")}
            className={inputClass}
          />
        </Field>

        <div className={`grid gap-4 ${editing ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
          <Field label={t("projects.form.startDate")}>
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label={t("projects.form.expectedEnd")}>
            <input
              type="date"
              value={expectedEndDate}
              onChange={(event) => setExpectedEndDate(event.target.value)}
              className={inputClass}
            />
          </Field>

          {editing ? (
            <Field label={t("projects.form.actualEnd")}>
              <input
                type="date"
                value={actualEndDate}
                onChange={(event) => setActualEndDate(event.target.value)}
                className={inputClass}
              />
            </Field>
          ) : null}
        </div>

        {blockedByQuota ? (
          <QuotaLimitNotice
            message={t("projects.form.quotaLimit", { count: projectQuota.limit, limit: projectQuota.limit })}
          />
        ) : null}

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-5">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
            {t("common.cancel")}
          </Button>

          <Button type="submit" variant="primary" disabled={isSubmitting || !name.trim() || blockedByQuota}>
            {isSubmitting
             ? t("common.saving")
             : editing
               ? t("common.saveChanges")
               : t("projects.form.createButton")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
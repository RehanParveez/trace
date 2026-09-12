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
            setError(getApiErrorMessage(mutationError, "Couldn't save this project. Please try again.")),
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
          setError(getApiErrorMessage(mutationError, "Couldn't create this project. The code may already be in use.")),
      },
    );
  }

  return (
    <Modal
      title={editing ? "Edit project" : "Create project"}
      description="Core project identity, delivery timeline and client assignment."
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Project name">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              placeholder="Main construction project"
              className={inputClass}
            />
          </Field>

          <Field label="Project code">
            <input
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="PRJ-001"
              className={inputClass}
            />
          </Field>
        </div>

        <Field label="Description">
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            placeholder="Project description"
            className={`${inputClass} resize-y`}
          />
        </Field>

        <div className={`grid gap-4 ${editing ? "sm:grid-cols-2" : "sm:grid-cols-1"}`}>
          <Field label="Client">
            <select
              value={clientId}
              onChange={(event) => setClientId(event.target.value)}
              className={inputClass}
            >
              <option value="">No client</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </Field>

          {editing ? (
            <Field label="Status">
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

        <Field label="Location">
          <input
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder="Project location"
            className={inputClass}
          />
        </Field>

        <div className={`grid gap-4 ${editing ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
          <Field label="Start date">
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Expected end">
            <input
              type="date"
              value={expectedEndDate}
              onChange={(event) => setExpectedEndDate(event.target.value)}
              className={inputClass}
            />
          </Field>

          {editing ? (
            <Field label="Actual end">
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
            message={`You've reached your plan's limit of ${projectQuota.limit} project${projectQuota.limit === 1 ? "" : "s"}. Upgrade to create more.`}
          />
        ) : null}

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-5">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>

          <Button type="submit" variant="primary" disabled={isSubmitting || !name.trim() || blockedByQuota}>
            {isSubmitting ? "Saving…" : editing ? "Save changes" : "Create project"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
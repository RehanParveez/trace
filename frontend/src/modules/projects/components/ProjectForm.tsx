import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {Button, Icon,
} from "../../organizations/components/OrganizationUi";
import {useCreateProject, useUpdateProject,
} from "../hooks";

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

  const [name, setName] =
    useState(project?.name ?? "");

  const [code, setCode] =
    useState(project?.code ?? "");

  const [description, setDescription] =
    useState(project?.description ?? "");

  const [clientId, setClientId] =
    useState(project?.client_id ?? "");

  const [location, setLocation] =
    useState(project?.location ?? "");

  const [status, setStatus] =
    useState<ProjectStatus>(
      project?.status ?? "PLANNING",
    );

  const [startDate, setStartDate] =
    useState(project?.start_date ?? "");

  const [expectedEndDate, setExpectedEndDate] =
    useState(
      project?.expected_end_date ?? "",
    );

  const [actualEndDate, setActualEndDate] =
    useState(
      project?.actual_end_date ?? "",
    );

  useEffect(() => {
    if (!project) {
      return;
    }

    setName(project.name);
    setCode(project.code ?? "");
    setDescription(
      project.description ?? "",
    );
    setClientId(project.client_id ?? "");
    setLocation(project.location ?? "");
    setStatus(project.status);
    setStartDate(project.start_date ?? "");
    setExpectedEndDate(
      project.expected_end_date ?? "",
    );
    setActualEndDate(
      project.actual_end_date ?? "",
    );
  }, [project]);

  const isSubmitting =
    createProject.isPending ||
    updateProject.isPending;

  function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const payload = {
      name: name.trim(),
      code: code.trim() || null,
      description:
        description.trim() || null,
      client_id: clientId || null,
      location:
        location.trim() || null,
      status,
      start_date: startDate || null,
      expected_end_date:
        expectedEndDate || null,
      actual_end_date:
        actualEndDate || null,
    };

    if (editing && project) {
      updateProject.mutate(
        {
          projectId: project.id,
          payload,
        },
        {
          onSuccess: onClose,
        },
      );

      return;
    }

    createProject.mutate(payload, {
      onSuccess: onClose,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#16283f]/45 p-4 backdrop-blur-[2px]">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[12px] border border-[#d9ceb9] bg-[#fbf8f2] shadow-[0_24px_70px_rgba(20,25,35,0.22)]">
        <div className="flex items-start justify-between border-b border-[#e1d5bc] p-5 sm:p-6">
          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.14em] text-[#a2957c]">
              PROJECT CONFIGURATION
            </div>

            <h2 className="mt-1 font-[Archivo] text-[21px] font-bold tracking-[-0.02em] text-[#191410]">
              {editing
                ? "Edit project"
                : "Create project"}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-[7px] text-[#756957] hover:bg-[#efe6d3]"
          >
            <Icon
              name="close"
              size={13}
            />
          </button>
        </div>

        <form
          onSubmit={submit}
          className="space-y-5 p-5 sm:p-6"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Project name"
              required
              value={name}
              onChange={setName}
              placeholder="Main construction project"
            />

            <Field
              label="Project code"
              value={code}
              onChange={setCode}
              placeholder="PRJ-001"
            />
          </div>

          <Field
            label="Description"
            value={description}
            onChange={setDescription}
            textarea
            placeholder="Project description"
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Client"
              value={clientId}
              onChange={setClientId}
            >
              <option value="">
                No client
              </option>

              {clients.map((client) => (
                <option
                  key={client.id}
                  value={client.id}
                >
                  {client.name}
                </option>
              ))}
            </SelectField>

            <SelectField
              label="Status"
              value={status}
              onChange={(value) =>
                setStatus(
                  value as ProjectStatus,
                )
              }
            >
              {statuses.map(
                (projectStatus) => (
                  <option
                    key={projectStatus}
                    value={projectStatus}
                  >
                    {projectStatus.replace(
                      "_",
                      " ",
                    )}
                  </option>
                ),
              )}
            </SelectField>
          </div>

          <Field
            label="Location"
            value={location}
            onChange={setLocation}
            placeholder="Project location"
          />

          <div className="grid gap-4 sm:grid-cols-3">
            <DateField
              label="Start date"
              value={startDate}
              onChange={setStartDate}
            />

            <DateField
              label="Expected end"
              value={expectedEndDate}
              onChange={setExpectedEndDate}
            />

            <DateField
              label="Actual end"
              value={actualEndDate}
              onChange={setActualEndDate}
            />
          </div>

          <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-5">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="primary"
              disabled={
                isSubmitting ||
                !name.trim()
              }
            >
              {isSubmitting
                ? "Saving..."
                : editing
                  ? "Save changes"
                  : "Create project"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  textarea?: boolean;
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  required,
  textarea,
}: FieldProps) {
  const className =
    "mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[11px] text-[#191410] outline-none transition placeholder:text-[#a2957c] focus:border-[#c39a38] focus:ring-2 focus:ring-[#d9a441]/15";

  return (
    <label className="block">
      <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
        {label}
        {required ? " *" : ""}
      </span>

      {textarea ? (
        <textarea
          value={value}
          onChange={(event) =>
            onChange(event.target.value)
          }
          placeholder={placeholder}
          rows={4}
          className={className}
        />
      ) : (
        <input
          value={value}
          onChange={(event) =>
            onChange(event.target.value)
          }
          placeholder={placeholder}
          required={required}
          className={className}
        />
      )}
    </label>
  );
}

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
}

function SelectField({
  label,
  value,
  onChange,
  children,
}: SelectFieldProps) {
  return (
    <label className="block">
      <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
        {label}
      </span>

      <select
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38] focus:ring-2 focus:ring-[#d9a441]/15"
      >
        {children}
      </select>
    </label>
  );
}

interface DateFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

function DateField({
  label,
  value,
  onChange,
}: DateFieldProps) {
  return (
    <label className="block">
      <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
        {label}
      </span>

      <input
        type="date"
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[10.5px] text-[#191410] outline-none focus:border-[#c39a38] focus:ring-2 focus:ring-[#d9a441]/15"
      />
    </label>
  );
}
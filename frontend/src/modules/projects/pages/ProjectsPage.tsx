import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {Button, ErrorState, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import {useClients, useCreateProject, useDeleteProject, useProjects,
} from "../hooks";
import type { Project, ProjectStatus } from "../types/project.types";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { ClientTable } from "../components/ClientTable";
import { ProjectForm } from "../components/ProjectForm";
import { ProjectStatusBadge } from "../components/ProjectStatusBadge";

export function ProjectsPage() {
  const navigate = useNavigate();
  const permissions = usePermissionKeys();

  const [formOpen, setFormOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | undefined>();
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "ALL">("ALL");

  const projectsQuery = useProjects();
  const clientsQuery = useClients();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();

  const canRead = permissions.includes(IDENTITY_PERMISSIONS.PROJECT_READ);
  const canCreate = permissions.includes(IDENTITY_PERMISSIONS.PROJECT_CREATE);
  const canUpdate = permissions.includes(IDENTITY_PERMISSIONS.PROJECT_UPDATE);
  const canDelete = permissions.includes(IDENTITY_PERMISSIONS.PROJECT_DELETE);

  const projects = projectsQuery.data ?? [];
  const clients = clientsQuery.data ?? [];

  const filteredProjects =
    statusFilter === "ALL"
      ? projects
      : projects.filter((project) => project.status === statusFilter);

  const activeCount = projects.filter(
    (project) => project.status === "ACTIVE",
  ).length;

  const planningCount = projects.filter(
    (project) => project.status === "PLANNING",
  ).length;

  const completedCount = projects.filter(
    (project) => project.status === "COMPLETED",
  ).length;

  const clientMap = new Map(
    clients.map((client) => [client.id, client.name]),
  );

  function openCreate() {
    setEditingProject(undefined);
    setFormOpen(true);
  }

  function openEdit(project: Project) {
    setEditingProject(project);
    setFormOpen(true);
  }

  function handleDelete(project: Project) {
    const confirmed = window.confirm(
      `Delete "${project.name}"? This action cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    deleteProject.mutate(project.id);
  }

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title="Project access unavailable"
        description="You do not have permission to view this organization's projects."
      />
    );
  }

  if (projectsQuery.isLoading || clientsQuery.isLoading) {
    return <LoadingState />;
  }

  if (
    projectsQuery.isError ||
    clientsQuery.isError ||
    !projectsQuery.data ||
    !clientsQuery.data
  ) {
    return (
      <ErrorState
        title="We couldn't load projects"
        description="The projects or client information could not be loaded."
        onRetry={() => {
          void projectsQuery.refetch();
          void clientsQuery.refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="PROJECT MANAGEMENT"
        title="Projects"
        description="Manage construction projects, clients, project teams and delivery milestones."
        actions={
          canCreate ? (
            <Button variant="primary" onClick={openCreate}>
              Create project
            </Button>
          ) : null
        }
      />

      <section>
        <SectionDivider
          title="Project pulse"
          description="Current project portfolio across this organization."
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Total"
            value={projects.length}
            note="Organization projects"
            icon="building"
            tone="blue"
            actionLabel={statusFilter !== "ALL" ? "Clear filter" : undefined}
            onAction={statusFilter !== "ALL" ? () => setStatusFilter("ALL") : undefined}
          />

          <StatCard
            label="Active"
            value={activeCount}
            note="Currently underway"
            icon="check"
            tone="green"
            actionLabel="View active"
            onAction={() => setStatusFilter("ACTIVE")}
          />

          <StatCard
            label="Planning"
            value={planningCount}
            note="Not yet underway"
            icon="settings"
            tone="gold"
            actionLabel="View planning"
            onAction={() => setStatusFilter("PLANNING")}
          />

          <StatCard
            label="Completed"
            value={completedCount}
            note="Finished projects"
            icon="shield"
            tone="blue"
            actionLabel="View completed"
            onAction={() => setStatusFilter("COMPLETED")}
          />
        </div>
      </section>

      <section>
        <SectionDivider
          title="Project register"
          description="Organization-scoped project records returned by the Projects service."
        />

        <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-muted)]">
          <div className="flex flex-wrap items-center gap-2 border-b border-[var(--color-border)] p-4">
            {(
              [
                ["ALL", "All"],
                ["PLANNING", "Planning"],
                ["ACTIVE", "Active"],
                ["ON_HOLD", "On hold"],
                ["COMPLETED", "Completed"],
                ["CANCELLED", "Cancelled"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatusFilter(value)}
                className={`rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${
                  statusFilter === value
                    ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {filteredProjects.length === 0 ? (
            <div className="p-8 text-center text-[12px] text-[var(--color-text-secondary)]">
              No projects match this filter.
            </div>
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              {filteredProjects.map((project) => (
                <div
                  key={project.id}
                  className="flex flex-col gap-4 p-5 transition hover:bg-[var(--color-surface)] sm:flex-row sm:items-center sm:justify-between"
                >
                  <button
                    type="button"
                    onClick={() =>
                      navigate(`/app/projects/${project.id}`)
                    }
                    className="min-w-0 text-left"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-[Archivo] text-[16px] font-bold text-[var(--color-text-primary)]">
                        {project.name}
                      </span>

                      <ProjectStatusBadge status={project.status} />
                    </div>

                    <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-[var(--color-text-secondary)]">
                      {project.code ? (
                        <span className="font-mono">{project.code}</span>
                      ) : null}

                      <span>
                        {project.client_id
                          ? (clientMap.get(project.client_id) ??
                            "Unknown client")
                          : "No client"}
                      </span>

                      {project.location ? (
                        <span>{project.location}</span>
                      ) : null}
                    </div>
                  </button>

                  {canUpdate || canDelete ? (
                    <div className="flex shrink-0 gap-2">
                      {canUpdate ? (
                        <Button
                          variant="ghost"
                          onClick={() => openEdit(project)}
                        >
                          Edit
                        </Button>
                      ) : null}

                      {canDelete ? (
                        <Button
                          variant="ghost"
                          onClick={() => handleDelete(project)}
                          disabled={deleteProject.isPending}
                        >
                          Delete
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section>
        <SectionDivider
          title="Client directory"
          description="Clients that can be linked to projects in this organization."
        />

        <ClientTable
          clients={clients}
          canUpdate={canUpdate}
          canDelete={canDelete}
        />
      </section>

      {formOpen ? (
        <ProjectForm
          project={editingProject}
          clients={clients}
          onClose={() => {
            if (!createProject.isPending) {
              setFormOpen(false);
              setEditingProject(undefined);
            }
          }}
        />
      ) : null}
    </div>
  );
}
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {Button, ErrorState, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import {useClients, useCreateProject, useDeleteProject, useProjects,
} from "../hooks";
import type {Project, ProjectStatus,
} from "../types/project.types";
import { PROJECT_PERMISSIONS } from "../permissions";
import { ProjectForm } from "../components/ProjectForm";
import { ProjectStatusBadge } from "../components/ProjectStatusBadge";

interface ProjectsPageProps {
  permissions?: string[];
}

export function ProjectsPage({
  permissions = [],
}: ProjectsPageProps) {
  const navigate = useNavigate();

  const [formOpen, setFormOpen] = useState(false);
  const [editingProject, setEditingProject] =
    useState<Project | undefined>();
  const [statusFilter, setStatusFilter] =
    useState<ProjectStatus | "ALL">("ALL");

  const projectsQuery = useProjects();
  const clientsQuery = useClients();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();

  const canRead = permissions.includes(
    PROJECT_PERMISSIONS.PROJECT_READ,
  );

  const canCreate = permissions.includes(
    PROJECT_PERMISSIONS.PROJECT_CREATE,
  );

  const canUpdate = permissions.includes(
    PROJECT_PERMISSIONS.PROJECT_UPDATE,
  );

  const canDelete = permissions.includes(
    PROJECT_PERMISSIONS.PROJECT_DELETE,
  );

  const projects = projectsQuery.data ?? [];
  const clients = clientsQuery.data ?? [];

  const filteredProjects =
    statusFilter === "ALL"
      ? projects
      : projects.filter(
          (project) =>
            project.status === statusFilter,
        );

  const activeCount = projects.filter(
    (project) =>
      project.status === "ACTIVE",
  ).length;

  const planningCount = projects.filter(
    (project) =>
      project.status === "PLANNING",
  ).length;

  const completedCount = projects.filter(
    (project) =>
      project.status === "COMPLETED",
  ).length;

  const clientMap = new Map(
    clients.map((client) => [
      client.id,
      client.name,
    ]),
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

  if (
    projectsQuery.isLoading ||
    clientsQuery.isLoading
  ) {
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
            <Button
              variant="primary"
              onClick={openCreate}
            >
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
          />

          <StatCard
            label="Active"
            value={activeCount}
            note="Currently underway"
            icon="check"
            tone="green"
          />

          <StatCard
            label="Planning"
            value={planningCount}
            note="Not yet underway"
            icon="settings"
            tone="gold"
          />

          <StatCard
            label="Completed"
            value={completedCount}
            note="Finished projects"
            icon="shield"
            tone="blue"
          />
        </div>
      </section>

      <section>
        <SectionDivider
          title="Project register"
          description="Organization-scoped project records returned by the Projects service."
        />

        <div className="overflow-hidden rounded-[11px] border border-[#d9ceb9] bg-[#fbf8f2]">
          <div className="flex flex-wrap items-center gap-2 border-b border-[#e1d5bc] p-4">
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
                onClick={() =>
                  setStatusFilter(value)
                }
                className={`rounded-[7px] border px-3 py-1.5 text-[10px] font-semibold transition ${
                  statusFilter === value
                    ? "border-[#d9a441] bg-[#fbefd9] text-[#76531a]"
                    : "border-[#e1d5bc] bg-white text-[#6b6152] hover:border-[#cdbd9c]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {filteredProjects.length === 0 ? (
            <div className="p-8 text-center text-[11px] text-[#756957]">
              No projects match this filter.
            </div>
          ) : (
            <div className="divide-y divide-[#e1d5bc]">
              {filteredProjects.map(
                (project) => (
                  <div
                    key={project.id}
                    className="flex flex-col gap-4 p-5 transition hover:bg-white sm:flex-row sm:items-center sm:justify-between"
                  >
                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/app/projects/${project.id}`,
                        )
                      }
                      className="min-w-0 text-left"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-[Archivo] text-[15px] font-bold text-[#191410]">
                          {project.name}
                        </span>

                        <ProjectStatusBadge
                          status={project.status}
                        />
                      </div>

                      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[#756957]">
                        {project.code ? (
                          <span className="font-mono">
                            {project.code}
                          </span>
                        ) : null}

                        <span>
                          {project.client_id
                            ? clientMap.get(
                                project.client_id,
                              ) ??
                              "Unknown client"
                            : "No client"}
                        </span>

                        {project.location ? (
                          <span>
                            {project.location}
                          </span>
                        ) : null}
                      </div>
                    </button>

                    {canUpdate || canDelete ? (
                      <div className="flex shrink-0 gap-2">
                        {canUpdate ? (
                          <Button
                            variant="ghost"
                            onClick={() =>
                              openEdit(project)
                            }
                          >
                            Edit
                          </Button>
                        ) : null}

                        {canDelete ? (
                          <Button
                            variant="ghost"
                            onClick={() =>
                              handleDelete(project)
                            }
                            disabled={
                              deleteProject.isPending
                            }
                          >
                            Delete
                          </Button>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ),
              )}
            </div>
          )}
        </div>
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
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {Button, ErrorState, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import {useClients, useCreateProject, useDeleteProject, useProjects,
} from "../hooks";
import type { Project, ProjectStatus } from "../types/project.types";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { QuotaLimitNotice, useQuotaStatus } from "../../subscriptions";
import { ClientTable } from "../components/ClientTable";
import { ProjectForm } from "../components/ProjectForm";
import { ProjectCard } from "../components/ProjectCard";
import { useTranslation } from "react-i18next";

export function ProjectsPage() {
  const { t } = useTranslation();
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

  const projectQuota = useQuotaStatus("projects");
  const blockedByQuota = projectQuota.isAtLimit;

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
      t("projects.detail.deleteConfirm", { name: project.name }),
    );

    if (!confirmed) {
      return;
    }

    deleteProject.mutate(project.id);
  }

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title={t("projects.page.accessUnavailable")}
        description={t("projects.page.accessUnavailableDesc")}
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
        title={t("projects.page.loadError")}
        description={t("projects.page.loadErrorDesc")}
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
        eyebrow={t("projects.page.eyebrow")}
        title={t("projects.page.title")}
        description={t("projects.page.description")}
        actions={
         canCreate ? (
          <Button
            variant="primary"
            onClick={openCreate}
            disabled={blockedByQuota}
            title={blockedByQuota ? t("projects.page.quotaTitle") : undefined}
          >
            {t("projects.page.create")}
          </Button>
         ) : null
       }
    />

      {canCreate && blockedByQuota ? (
        <QuotaLimitNotice
          message={t("projects.form.quotaLimit", {
           count: projectQuota.limit,
           limit: projectQuota.limit,
          })}
        />
      ) : null}

      <section>
        <SectionDivider
          title={t("projects.page.pulseTitle")}
          description={t("projects.page.pulseDesc")}
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label={t("projects.page.statTotal")}
            value={projects.length}
            note={t("projects.page.statTotalNote")}
            icon="building"
            tone="blue"
            actionLabel={statusFilter !== "ALL" ? t("projects.page.clearFilter") : undefined}
            onAction={statusFilter !== "ALL" ? () => setStatusFilter("ALL") : undefined}
          />

          <StatCard
            label={t("projects.page.statActive")}
            value={activeCount}
            note={t("projects.page.statActiveNote")}
            icon="check"
            tone="green"
            actionLabel={t("projects.page.viewActive")}
            onAction={() => setStatusFilter("ACTIVE")}
          />

          <StatCard
            label={t("projects.page.statPlanning")}
            value={planningCount}
            note={t("projects.page.statPlanningNote")}
            icon="settings"
            tone="gold"
            actionLabel={t("projects.page.viewPlanning")}
            onAction={() => setStatusFilter("PLANNING")}
          />

          <StatCard
            label={t("projects.page.statCompleted")}
            value={completedCount}
            note={t("projects.page.statCompletedNote")}
            icon="shield"
            tone="blue"
            actionLabel={t("projects.page.viewCompleted")}
            onAction={() => setStatusFilter("COMPLETED")}
          />
        </div>
      </section>

            <section>
        <SectionDivider
          title={t("projects.page.registerTitle")}
          description={t("projects.page.registerDesc")}
        />

        <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
          <div className="flex flex-wrap items-center gap-2">
            {(
              [
                ["ALL", t("projects.status.all")],
                ["PLANNING", t("projects.status.planning")],
                ["ACTIVE", t("projects.status.active")],
                ["ON_HOLD", t("projects.status.onHold")],
                ["COMPLETED", t("projects.status.completed")],
                ["CANCELLED", t("projects.status.cancelled")]
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
        </div>

        {filteredProjects.length === 0 ? (
          <div className="mt-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-8 text-center text-[12px] text-[var(--color-text-secondary)]">
            {t("projects.page.emptyFilter")}
          </div>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                clientName={
                  project.client_id ? clientMap.get(project.client_id) : undefined
                }
                canUpdate={canUpdate}
                canDelete={canDelete}
                onOpen={(item) => navigate(`/app/projects/${item.id}`)}
                onEdit={openEdit}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionDivider
          title={t("projects.page.clientsTitle")}
          description={t("projects.page.clientsDesc")}
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
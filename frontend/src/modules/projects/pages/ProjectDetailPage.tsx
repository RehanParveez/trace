import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {ErrorState, LoadingState, PageHeader, SectionDivider, StatCard, useToast,
} from "../../organizations/components/OrganizationUi";
import {useClients, useDeleteProject, useProject, useProjectMembers, useProjectMilestones,
} from "../hooks";
import { IDENTITY_PERMISSIONS, getApiErrorMessage, usePermissionKeys } from "../../identity";
import { ProjectHeader } from "../components/ProjectHeader";
import { ProjectForm } from "../components/ProjectForm";
import { ProjectMembers } from "../components/ProjectMembers";
import { MilestoneTable } from "../components/MilestoneTable";
import { DrawingsBoqSection } from "../../drawings_boq";
import { VerificationSection } from "../../verification";
import { ProjectFinancialSummary } from "../../budgets";
import { ProjectActivityFeed } from "../components/ProjectActivityFeed";
import { useTranslation } from "react-i18next";

export function ProjectDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const permissions = usePermissionKeys();
  const { showToast } = useToast();

  const { projectId } = useParams<{ projectId: string }>();

  const [editOpen, setEditOpen] = useState(false);

  const projectQuery = useProject(projectId ?? "");
  const clientsQuery = useClients();
  const membersQuery = useProjectMembers(projectId ?? "");
  const milestonesQuery = useProjectMilestones(projectId ?? "");
  const deleteProject = useDeleteProject();

  const canRead = permissions.includes(IDENTITY_PERMISSIONS.PROJECT_READ);
  const canUpdate = permissions.includes(IDENTITY_PERMISSIONS.PROJECT_UPDATE);
  const canDelete = permissions.includes(IDENTITY_PERMISSIONS.PROJECT_DELETE);

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
       title={t("projects.detail.accessUnavailable")}
       description={t("projects.detail.accessUnavailableDesc")}
      />
    );
  }

  if (
    !projectId ||
    projectQuery.isLoading ||
    clientsQuery.isLoading ||
    membersQuery.isLoading ||
    milestonesQuery.isLoading
  ) {
    return <LoadingState />;
  }

  if (
    projectQuery.isError ||
    clientsQuery.isError ||
    membersQuery.isError ||
    milestonesQuery.isError ||
    !projectQuery.data ||
    !clientsQuery.data ||
    !membersQuery.data ||
    !milestonesQuery.data
  ) {
    return (
      <ErrorState
        title={t("projects.detail.loadError")}
        description={t("projects.detail.loadErrorDesc")}
        onRetry={() => {
          void projectQuery.refetch();
          void clientsQuery.refetch();
          void membersQuery.refetch();
          void milestonesQuery.refetch();
        }}
      />
    );
  }

  const project = projectQuery.data;
  const clients = clientsQuery.data;
  const members = membersQuery.data;
  const milestones = milestonesQuery.data;

  const client = clients.find((item) => item.id === project.client_id);

  const completedMilestones = milestones.filter(
    (milestone) => milestone.completed_at !== null,
  ).length;

  function handleDelete() {
    const confirmed = window.confirm(
      t("projects.detail.deleteConfirm", { name: project.name }),
    );

    if (!confirmed) {
      return;
    }

    deleteProject.mutate(project.id, {
      onSuccess: () => {
        navigate("/app/projects");
        showToast({
          tone: "success",
          title: t("projects.page.deletedToast", { name: project.name }),
        });
      },
      onError: (error) =>
        showToast({
          tone: "error",
          title: t("projects.page.deleteErrorTitle"),
          description: getApiErrorMessage(error, t("projects.page.deleteErrorFallback")),
        }),
    });
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={t("projects.detail.eyebrow")}
        title={t("projects.detail.title")}
        description={t("projects.detail.description")}
      />

     <ProjectHeader
        project={project}
        canUpdate={canUpdate}
        canDelete={canDelete}
        onEdit={() => setEditOpen(true)}
        onDelete={handleDelete}
      />

      <ProjectActivityFeed projectId={project.id} />

      <section>
        <SectionDivider
          title={t("projects.detail.pulseTitle")}
          description={t("projects.detail.pulseDesc")}
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label={t("projects.detail.statStatus")}
            value={project.status}
            note={t("projects.detail.statStatusNote")}
            icon="check"
            tone="green"
          />

          <StatCard
            label={t("projects.detail.statClient")}
            value={client?.name ?? t("projects.card.noClient")}
            note={t("projects.detail.statClientNote")}
            icon="building"
            tone="blue"
          />

          <StatCard
            label={t("projects.detail.statTeam")}
            value={members.length}
            note={t("projects.detail.statTeamNote")}
            icon="shield"
            tone="gold"
            actionLabel={t("projects.detail.viewTeam")}
            onAction={() =>
              document
                .getElementById("project-team")
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          />

          <StatCard
            label={t("projects.detail.statMilestones")}
            value={milestones.length}
            note={t("projects.detail.statMilestonesNote", { count: completedMilestones })}
            icon="check"
            tone="blue"
            actionLabel={t("projects.detail.viewMilestones")}
            onAction={() =>
              document
                .getElementById("project-milestones")
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          />
       </div>
      </section>

      <section>
        <SectionDivider
          title={t("projects.detail.financialsTitle")}
          description={t("projects.detail.financialsDesc")}
        />

        <ProjectFinancialSummary projectId={project.id} />
      </section>

      <section id="project-milestones">
        <SectionDivider
          title={t("projects.detail.milestonesTitle")}
          description={t("projects.detail.milestonesDesc")}
        />

        <MilestoneTable
          projectId={project.id}
          milestones={milestones}
          canUpdate={canUpdate}
        />
      </section>

      <section>
        <SectionDivider
          title={t("projects.detail.drawingsTitle")}
          description={t("projects.detail.drawingsDesc")}
        />
        <DrawingsBoqSection projectId={project.id} />
      </section>

      <section>
        <SectionDivider
          title={t("projects.detail.verificationTitle")}
          description={t("projects.detail.verificationDesc")}
        />
        <VerificationSection
          projectId={project.id}
          permissions={permissions}
        />
      </section>

      <section id="project-team">
        <SectionDivider
          title={t("projects.detail.teamTitle")}
          description={t("projects.detail.teamDesc")}
        />

        <ProjectMembers
          projectId={project.id}
          members={members}
          canUpdate={canUpdate}
        />
      </section>

      {editOpen ? (
        <ProjectForm
          project={project}
          clients={clients}
          onClose={() => setEditOpen(false)}
        />
      ) : null}
    </div>
  );
}
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {ErrorState, LoadingState, PageHeader, SectionDivider, StatCard,
} from "../../organizations/components/OrganizationUi";
import {useClients, useDeleteProject, useProject, useProjectMembers, useProjectMilestones,
} from "../hooks";
import { PROJECT_PERMISSIONS } from "../permissions";
import { ProjectHeader } from "../components/ProjectHeader";
import { ProjectForm } from "../components/ProjectForm";
import { ProjectMembers } from "../components/ProjectMembers";
import { MilestoneTable } from "../components/MilestoneTable";
import { usePermissionKeys } from "../../identity/";
import { DrawingsBoqSection } from "../../drawings_boq";
import { VerificationSection } from "../../verification";

interface ProjectDetailPageProps {
  permissions?: string[];
}

export function ProjectDetailPage({
  permissions: providedPermissions,
}: ProjectDetailPageProps) {
  const permissions =
    providedPermissions ?? usePermissionKeys();
  const navigate = useNavigate();

  const { projectId } =
    useParams<{ projectId: string }>();

  const [editOpen, setEditOpen] =
    useState(false);

  const projectQuery =
    useProject(projectId ?? "");

  const clientsQuery = useClients();

  const membersQuery =
    useProjectMembers(projectId ?? "");

  const milestonesQuery =
    useProjectMilestones(projectId ?? "");

  const deleteProject =
    useDeleteProject();

  const canRead = permissions.includes(
    PROJECT_PERMISSIONS.PROJECT_READ,
  );

  const canUpdate = permissions.includes(
    PROJECT_PERMISSIONS.PROJECT_UPDATE,
  );

  const canDelete = permissions.includes(
    PROJECT_PERMISSIONS.PROJECT_DELETE,
  );

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title="Project access unavailable"
        description="You do not have permission to view this project."
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
        title="We couldn't load this project"
        description="The project, team or milestone information could not be loaded."
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

  const client = clients.find(
    (item) => item.id === project.client_id,
  );

  const completedMilestones =
    milestones.filter(
      (milestone) =>
        milestone.completed_at !== null,
    ).length;

  function handleDelete() {
    const confirmed = window.confirm(
      `Delete "${project.name}"? This action cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    deleteProject.mutate(project.id, {
      onSuccess: () => {
        navigate("/app/projects");
      },
    });
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="PROJECT WORKSPACE"
        title="Project details"
        description="Project context, delivery milestones and assigned project team."
      />

      <ProjectHeader
        project={project}
        canUpdate={canUpdate}
        canDelete={canDelete}
        onEdit={() =>
          setEditOpen(true)
        }
        onDelete={handleDelete}
      />

      <section>
        <SectionDivider
          title="Project pulse"
          description="Core delivery information for this project."
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Status"
            value={project.status}
            note="Current project state"
            icon="check"
            tone="green"
          />

          <StatCard
            label="Client"
            value={
              client?.name ?? "No client"
            }
            note="Assigned client"
            icon="building"
            tone="blue"
          />

          <StatCard
            label="Team"
            value={members.length}
            note="Assigned project members"
            icon="shield"
            tone="gold"
          />

          <StatCard
            label="Milestones"
            value={milestones.length}
            note={`${completedMilestones} completed`}
            icon="check"
            tone="blue"
          />
        </div>
      </section>

      <section>
        <SectionDivider
          title="Delivery milestones"
          description="Track the major delivery checkpoints attached to this project."
        />

        <MilestoneTable
          projectId={project.id}
          milestones={milestones}
          canUpdate={canUpdate}
        />
      </section>

      <section>
        <SectionDivider title="Drawings & BOQ" description="Upload IFC drawings and manage the auto-generated bill of quantities." />
        <DrawingsBoqSection projectId={project.id} permissions={permissions} />
      </section>

      <section>
        <SectionDivider title="Progress verification" description="Claims of physical progress, backed by photo evidence, against approved BOQ items." />
        <VerificationSection projectId={project.id} permissions={permissions} />
      </section>

      <section>
        <SectionDivider
          title="Project team"
          description="Users assigned to this project and their project-level responsibilities."
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
          onClose={() =>
            setEditOpen(false)
          }
        />
      ) : null}
    </div>
  );
}
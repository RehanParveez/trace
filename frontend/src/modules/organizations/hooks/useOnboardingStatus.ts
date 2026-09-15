import { useMembers } from "./useMembers";
import { useProjects } from "../../projects";
import { useDrawingOrganizationSummary } from "../../drawings_boq";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";

export interface OnboardingStep {
  key: string;
  label: string;
  done: boolean;
  locked: boolean;
  to: string;
  lockedHint?: string;
}

export interface OnboardingStatus {
  steps: OnboardingStep[];
  completedCount: number;
  totalCount: number;
  isComplete: boolean;
  isLoading: boolean;
}

export function useOnboardingStatus(): OnboardingStatus {
  const permissions = usePermissionKeys();
  const canViewDrawings = permissions.includes(IDENTITY_PERMISSIONS.DRAWING_READ);

  const projectsQuery = useProjects();
  const membersQuery = useMembers(0, 100);
  const drawingSummaryQuery = useDrawingOrganizationSummary({ enabled: canViewDrawings });

  const projects = projectsQuery.data ?? [];
  const hasProject = projects.length > 0;
  const memberCount = membersQuery.data?.total ?? 0;
  const hasTeam = memberCount > 1;
  const drawingCount = drawingSummaryQuery.data?.drawing_count ?? 0;
  const hasDrawing = drawingCount > 0;
  const firstProjectId = projects[0]?.id;

  const steps: OnboardingStep[] = [
    {
      key: "project",
      label: "Create your first project",
      done: hasProject,
      locked: false,
      to: "/app/projects",
    },
    {
      key: "team",
      label: "Invite your team",
      done: hasTeam,
      locked: false,
      to: "/app/organization/invitations",
    },
    {
      key: "drawing",
      label: "Upload a drawing or reference document",
      done: hasDrawing,
      locked: !hasProject,
      lockedHint: "Create a project first",
      to: firstProjectId ? `/app/projects/${firstProjectId}` : "/app/projects",
    },
  ];

  const completedCount = steps.filter((step) => step.done).length;

  return {
    steps,
    completedCount,
    totalCount: steps.length,
    isComplete: completedCount === steps.length,
    isLoading:
      projectsQuery.isLoading ||
      membersQuery.isLoading ||
      (canViewDrawings && drawingSummaryQuery.isLoading),
  };
}
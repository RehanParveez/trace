import { useMembers } from "./useMembers";
import { useProjects } from "../../projects";

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
  const projectsQuery = useProjects();
  const membersQuery = useMembers(0, 100);

  const projects = projectsQuery.data ?? [];
  const hasProject = projects.length > 0;

  const memberCount = membersQuery.data?.total ?? 0;
  const hasTeam = memberCount > 1;

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
  ];

  const completedCount = steps.filter((step) => step.done).length;

  return {
    steps,
    completedCount,
    totalCount: steps.length,
    isComplete: completedCount === steps.length,
    isLoading:
      projectsQuery.isLoading ||
      membersQuery.isLoading,
  };
}
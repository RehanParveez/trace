import {useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { projectsApi } from "../api/projects.api";
import type {ClientCreateRequest, ClientUpdateRequest, MilestoneCreateRequest, MilestoneUpdateRequest, ProjectCreateRequest, ProjectMemberCreateRequest,
 ProjectMemberUpdateRequest, ProjectUpdateRequest,
} from "../types/project.types";

export const projectKeys = {
  all: ["projects"] as const,

  list: () =>
    [...projectKeys.all, "list"] as const,

  detail: (projectId: string) =>
    [...projectKeys.all, "detail", projectId] as const,

  clients: () =>
    [...projectKeys.all, "clients"] as const,

  client: (clientId: string) =>
    [...projectKeys.all, "client", clientId] as const,

  members: (projectId: string) =>
    [...projectKeys.all, "members", projectId] as const,

  milestones: (projectId: string) =>
    [...projectKeys.all, "milestones", projectId] as const,
};

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: projectsApi.listProjects,
  });
}

export function useProject(
  projectId: string,
) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () =>
      projectsApi.getProject(projectId),
    enabled: Boolean(projectId),
  });
}

export function useClients() {
  return useQuery({
    queryKey: projectKeys.clients(),
    queryFn: projectsApi.listClients,
  });
}

export function useClient(
  clientId: string,
) {
  return useQuery({
    queryKey: projectKeys.client(clientId),
    queryFn: () =>
      projectsApi.getClient(clientId),
    enabled: Boolean(clientId),
  });
}

export function useProjectMembers(
  projectId: string,
) {
  return useQuery({
    queryKey: projectKeys.members(projectId),
    queryFn: () =>
      projectsApi.listMembers(projectId),
    enabled: Boolean(projectId),
  });
}

export function useProjectMilestones(
  projectId: string,
) {
  return useQuery({
    queryKey: projectKeys.milestones(projectId),
    queryFn: () =>
      projectsApi.listMilestones(projectId),
    enabled: Boolean(projectId),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: ProjectCreateRequest,
    ) => projectsApi.createProject(payload),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.list(),
      });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      payload,
    }: {
      projectId: string;
      payload: ProjectUpdateRequest;
    }) =>
      projectsApi.updateProject(
        projectId,
        payload,
      ),

    onSuccess: (project) => {
      queryClient.setQueryData(
        projectKeys.detail(project.id),
        project,
      );

      void queryClient.invalidateQueries({
        queryKey: projectKeys.list(),
      });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      projectsApi.deleteProject(projectId),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.list(),
      });
    },
  });
}

export function useCreateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: ClientCreateRequest,
    ) => projectsApi.createClient(payload),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.clients(),
      });
    },
  });
}

export function useUpdateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      clientId,
      payload,
    }: {
      clientId: string;
      payload: ClientUpdateRequest;
    }) =>
      projectsApi.updateClient(
        clientId,
        payload,
      ),

    onSuccess: (client) => {
      queryClient.setQueryData(
        projectKeys.client(client.id),
        client,
      );

      void queryClient.invalidateQueries({
        queryKey: projectKeys.clients(),
      });

      void queryClient.invalidateQueries({
        queryKey: projectKeys.list(),
      });
    },
  });
}

export function useDeleteClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (clientId: string) =>
      projectsApi.deleteClient(clientId),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.clients(),
      });

      void queryClient.invalidateQueries({
        queryKey: projectKeys.list(),
      });
    },
  });
}

export function useAddProjectMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      payload,
    }: {
      projectId: string;
      payload: ProjectMemberCreateRequest;
    }) =>
      projectsApi.addMember(
        projectId,
        payload,
      ),

    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.members(
          variables.projectId,
        ),
      });
    },
  });
}

export function useUpdateProjectMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      userId,
      payload,
    }: {
      projectId: string;
      userId: string;
      payload: ProjectMemberUpdateRequest;
    }) =>
      projectsApi.updateMember(
        projectId,
        userId,
        payload,
      ),

    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.members(
          variables.projectId,
        ),
      });
    },
  });
}

export function useRemoveProjectMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      userId,
    }: {
      projectId: string;
      userId: string;
    }) =>
      projectsApi.removeMember(
        projectId,
        userId,
      ),

    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.members(
          variables.projectId,
        ),
      });
    },
  });
}

export function useCreateMilestone() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      payload,
    }: {
      projectId: string;
      payload: MilestoneCreateRequest;
    }) =>
      projectsApi.createMilestone(
        projectId,
        payload,
      ),

    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.milestones(
          variables.projectId,
        ),
      });
    },
  });
}

export function useUpdateMilestone() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      milestoneId,
      payload,
    }: {
      projectId: string;
      milestoneId: string;
      payload: MilestoneUpdateRequest;
    }) =>
      projectsApi.updateMilestone(
        projectId,
        milestoneId,
        payload,
      ),

    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.milestones(
          variables.projectId,
        ),
      });
    },
  });
}

export function useDeleteMilestone() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      milestoneId,
    }: {
      projectId: string;
      milestoneId: string;
    }) =>
      projectsApi.deleteMilestone(
        projectId,
        milestoneId,
      ),

    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.milestones(
          variables.projectId,
        ),
      });
    },
  });
}
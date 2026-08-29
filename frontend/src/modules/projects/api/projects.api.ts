import { apiClient } from "../../../shared/api/client";
import type {Client, ClientCreateRequest, ClientUpdateRequest, Milestone, MilestoneCreateRequest, MilestoneUpdateRequest, Project, ProjectCreateRequest, ProjectMember,
  ProjectMemberCreateRequest, ProjectMemberUpdateRequest, ProjectUpdateRequest,
} from "../types/project.types";

export const projectsApi = {
  async listClients(): Promise<Client[]> {
    const response = await apiClient.get<Client[]>(
      "/projects/clients",
    );

    return response.data;
  },

  async getClient(
    clientId: string,
  ): Promise<Client> {
    const response = await apiClient.get<Client>(
      `/projects/clients/${clientId}`,
    );

    return response.data;
  },

  async createClient(
    payload: ClientCreateRequest,
  ): Promise<Client> {
    const response =
      await apiClient.post<Client>(
        "/projects/clients",
        payload,
      );

    return response.data;
  },

  async updateClient(
    clientId: string,
    payload: ClientUpdateRequest,
  ): Promise<Client> {
    const response =
      await apiClient.patch<Client>(
        `/projects/clients/${clientId}`,
        payload,
      );

    return response.data;
  },

  async deleteClient(
    clientId: string,
  ): Promise<void> {
    await apiClient.delete(
      `/projects/clients/${clientId}`,
    );
  },

  async listProjects(): Promise<Project[]> {
    const response = await apiClient.get<Project[]>(
      "/projects",
    );

    return response.data;
  },

  async getProject(
    projectId: string,
  ): Promise<Project> {
    const response =
      await apiClient.get<Project>(
        `/projects/${projectId}`,
      );

    return response.data;
  },

  async createProject(
    payload: ProjectCreateRequest,
  ): Promise<Project> {
    const response =
      await apiClient.post<Project>(
        "/projects",
        payload,
      );

    return response.data;
  },

  async updateProject(
    projectId: string,
    payload: ProjectUpdateRequest,
  ): Promise<Project> {
    const response =
      await apiClient.patch<Project>(
        `/projects/${projectId}`,
        payload,
      );

    return response.data;
  },

  async deleteProject(
    projectId: string,
  ): Promise<void> {
    await apiClient.delete(
      `/projects/${projectId}`,
    );
  },

  async listMembers(
    projectId: string,
  ): Promise<ProjectMember[]> {
    const response =
      await apiClient.get<ProjectMember[]>(
        `/projects/${projectId}/members`,
      );

    return response.data;
  },

  async addMember(
    projectId: string,
    payload: ProjectMemberCreateRequest,
  ): Promise<ProjectMember> {
    const response =
      await apiClient.post<ProjectMember>(
        `/projects/${projectId}/members`,
        payload,
      );

    return response.data;
  },

  async updateMember(
    projectId: string,
    userId: string,
    payload: ProjectMemberUpdateRequest,
  ): Promise<ProjectMember> {
    const response =
      await apiClient.patch<ProjectMember>(
        `/projects/${projectId}/members/${userId}`,
        payload,
      );

    return response.data;
  },

  async removeMember(
    projectId: string,
    userId: string,
  ): Promise<void> {
    await apiClient.delete(
      `/projects/${projectId}/members/${userId}`,
    );
  },

  async listMilestones(
    projectId: string,
  ): Promise<Milestone[]> {
    const response =
      await apiClient.get<Milestone[]>(
        `/projects/${projectId}/milestones`,
      );

    return response.data;
  },

  async createMilestone(
    projectId: string,
    payload: MilestoneCreateRequest,
  ): Promise<Milestone> {
    const response =
      await apiClient.post<Milestone>(
        `/projects/${projectId}/milestones`,
        payload,
      );

    return response.data;
  },

  async updateMilestone(
    projectId: string,
    milestoneId: string,
    payload: MilestoneUpdateRequest,
  ): Promise<Milestone> {
    const response =
      await apiClient.patch<Milestone>(
        `/projects/${projectId}/milestones/${milestoneId}`,
        payload,
      );

    return response.data;
  },

  async deleteMilestone(
    projectId: string,
    milestoneId: string,
  ): Promise<void> {
    await apiClient.delete(
      `/projects/${projectId}/milestones/${milestoneId}`,
    );
  },
};
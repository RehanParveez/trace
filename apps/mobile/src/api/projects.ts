import { authenticatedRequest } from "./client";
import type {
  Client,
  ClientPayload,
  Milestone,
  MilestonePayload,
  MilestoneUpdatePayload,
  OrganizationMember,
  Project,
  ProjectCreatePayload,
  ProjectMember,
  ProjectMemberRole,
  ProjectStatus,
  ProjectUpdatePayload,
} from "./types";

function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}

export function listProjects(): Promise<Project[]> {
  return authenticatedRequest<Project[]>("/projects");
}

export function getProject(projectId: string): Promise<Project> {
  return authenticatedRequest<Project>(`/projects/${projectId}`);
}

export function createProject(payload: ProjectCreatePayload): Promise<Project> {
  return authenticatedRequest<Project>("/projects", {
    method: "POST",
    body: jsonBody(payload),
  });
}

export function updateProject(
  projectId: string,
  payload: ProjectUpdatePayload,
): Promise<Project> {
  return authenticatedRequest<Project>(`/projects/${projectId}`, {
    method: "PATCH",
    body: jsonBody(payload),
  });
}

export function deleteProject(projectId: string): Promise<void> {
  return authenticatedRequest<void>(`/projects/${projectId}`, {
    method: "DELETE",
  });
}

export function listClients(): Promise<Client[]> {
  return authenticatedRequest<Client[]>("/projects/clients");
}

export function createClient(payload: ClientPayload): Promise<Client> {
  return authenticatedRequest<Client>("/projects/clients", {
    method: "POST",
    body: jsonBody(payload),
  });
}

export function updateClient(
  clientId: string,
  payload: Partial<ClientPayload>,
): Promise<Client> {
  return authenticatedRequest<Client>(`/projects/clients/${clientId}`, {
    method: "PATCH",
    body: jsonBody(payload),
  });
}

export function deleteClient(clientId: string): Promise<void> {
  return authenticatedRequest<void>(`/projects/clients/${clientId}`, {
    method: "DELETE",
  });
}

export function listOrganizationMembers(): Promise<OrganizationMember[]> {
  return authenticatedRequest<OrganizationMember[]>(
    "/organizations/me/members?skip=0&limit=100",
  );
}

export function listProjectMembers(projectId: string): Promise<ProjectMember[]> {
  return authenticatedRequest<ProjectMember[]>(
    `/projects/${projectId}/members`,
  );
}

export function addProjectMember(
  projectId: string,
  userId: string,
  role: ProjectMemberRole,
): Promise<ProjectMember> {
  return authenticatedRequest<ProjectMember>(
    `/projects/${projectId}/members`,
    {
      method: "POST",
      body: jsonBody({ user_id: userId, role }),
    },
  );
}

export function updateProjectMember(
  projectId: string,
  userId: string,
  role: ProjectMemberRole,
): Promise<ProjectMember> {
  return authenticatedRequest<ProjectMember>(
    `/projects/${projectId}/members/${userId}`,
    {
      method: "PATCH",
      body: jsonBody({ role }),
    },
  );
}

export function deleteProjectMember(
  projectId: string,
  userId: string,
): Promise<void> {
  return authenticatedRequest<void>(
    `/projects/${projectId}/members/${userId}`,
    { method: "DELETE" },
  );
}

export function listMilestones(projectId: string): Promise<Milestone[]> {
  return authenticatedRequest<Milestone[]>(
    `/projects/${projectId}/milestones`,
  );
}

export function createMilestone(
  projectId: string,
  payload: MilestonePayload,
): Promise<Milestone> {
  return authenticatedRequest<Milestone>(
    `/projects/${projectId}/milestones`,
    {
      method: "POST",
      body: jsonBody(payload),
    },
  );
}

export function updateMilestone(
  projectId: string,
  milestoneId: string,
  payload: MilestoneUpdatePayload,
): Promise<Milestone> {
  return authenticatedRequest<Milestone>(
    `/projects/${projectId}/milestones/${milestoneId}`,
    {
      method: "PATCH",
      body: jsonBody(payload),
    },
  );
}

export function deleteMilestone(
  projectId: string,
  milestoneId: string,
): Promise<void> {
  return authenticatedRequest<void>(
    `/projects/${projectId}/milestones/${milestoneId}`,
    { method: "DELETE" },
  );
}

export type { ProjectStatus };
import { authenticatedRequest } from "./client";
import type { Project, ProjectCreatePayload, Client } from "./types";

export function listProjects(): Promise<Project[]> {
  return authenticatedRequest<Project[]>("/projects");
}

export function getProject(projectId: string): Promise<Project> {
  return authenticatedRequest<Project>(`/projects/${projectId}`);
}

export function createProject(payload: ProjectCreatePayload): Promise<Project> {
  return authenticatedRequest<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listClients(): Promise<Client[]> {
  return authenticatedRequest<Client[]>("/projects/clients");
}
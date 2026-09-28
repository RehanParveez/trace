import { authenticatedRequest } from "./client";
import type { Project } from "./types";

export function listProjects(): Promise<Project[]> {
  return authenticatedRequest<Project[]>("/projects");
}
import { apiClient } from "../../../../shared/api/client";
import type { CompanyConventions, ConventionsUpdate, ProjectOverridesUpdate } from "../types/companyConventions.types";

const BASE = "/drawings-boq/company-conventions";

export const companyConventionsApi = {
  async get(projectId?: string | null): Promise<CompanyConventions> {
    return (await apiClient.get<CompanyConventions>(BASE, { params: projectId ? { project_id: projectId } : undefined })).data;
  },
  async saveProject(projectId: string, body: ProjectOverridesUpdate): Promise<CompanyConventions> {
    return (await apiClient.put<CompanyConventions>(`/drawings-boq/projects/${projectId}/rule-overrides`, body)).data;
  },
  async save(body: ConventionsUpdate): Promise<CompanyConventions> {
    return (await apiClient.put<CompanyConventions>(BASE, body)).data;
  },
  async adoptQs(): Promise<CompanyConventions> {
    return (await apiClient.post<CompanyConventions>(`${BASE}/adopt-qs`)).data;
  },
};

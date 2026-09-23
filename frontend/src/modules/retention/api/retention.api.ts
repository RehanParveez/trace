import { apiClient } from "../../../shared/api/client";
import type {OrganizationRetentionSummary, ProjectRetentionSummary, RetentionHolderType, RetentionRelease,
} from "../types/retention.types";

export const retentionApi = {
  async listReleases(projectId?: string): Promise<RetentionRelease[]> {
    return (await apiClient.get<RetentionRelease[]>("/retention/releases", { params: { project_id: projectId } })).data;
  },
  async recordRelease(payload: {
    holder_type: RetentionHolderType; project_id: string; boq_version_id?: string | null;
    agreement_id?: string | null; amount: number; release_date: string; notes?: string | null;
  }): Promise<RetentionRelease> {
    return (await apiClient.post<RetentionRelease>("/retention/releases", payload)).data;
  },
  async getProjectSummary(projectId: string): Promise<ProjectRetentionSummary> {
    return (await apiClient.get<ProjectRetentionSummary>(`/retention/projects/${projectId}/summary`)).data;
  },
  async getOrganizationSummary(): Promise<OrganizationRetentionSummary> {
    return (await apiClient.get<OrganizationRetentionSummary>("/retention/organization-summary")).data;
  },
};
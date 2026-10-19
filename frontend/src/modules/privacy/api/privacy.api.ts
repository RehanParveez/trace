import { apiClient } from "../../../shared/api/client";
import type {DeletionRequest, DeletionRequestCreate, ExportDownload, ExportJob, PrivacyOverview, SupportGrant, SupportGrantCreateRequest,
} from "../types/privacy.types";

export const privacyApi = {
  async getOverview(): Promise<PrivacyOverview> {
    const response = await apiClient.get<PrivacyOverview>("/privacy/overview");
    return response.data;
  },

  async listSupportGrants(): Promise<SupportGrant[]> {
    const response = await apiClient.get<SupportGrant[]>("/privacy/support-grants");
    return response.data;
  },

  async createSupportGrant(payload: SupportGrantCreateRequest): Promise<SupportGrant> {
    const response = await apiClient.post<SupportGrant>("/privacy/support-grants", payload);
    return response.data;
  },

  async revokeSupportGrant(grantId: string): Promise<SupportGrant> {
    const response = await apiClient.post<SupportGrant>(
      `/privacy/support-grants/${grantId}/revoke`,
    );
    return response.data;
  },

  async listExports(): Promise<ExportJob[]> {
    const response = await apiClient.get<ExportJob[]>("/privacy/exports");
    return response.data;
  },

  async requestExport(): Promise<ExportJob> {
    const response = await apiClient.post<ExportJob>("/privacy/exports");
    return response.data;
  },

  async getExportDownload(jobId: string): Promise<ExportDownload> {
    const response = await apiClient.get<ExportDownload>(
      `/privacy/exports/${jobId}/download`,
    );
    return response.data;
  },

  async getDeletionRequest(): Promise<DeletionRequest | null> {
    const response = await apiClient.get<DeletionRequest | null>("/privacy/deletion-request");
    return response.data ?? null;
  },

  async requestDeletion(payload: DeletionRequestCreate): Promise<DeletionRequest> {
    const response = await apiClient.post<DeletionRequest>(
      "/privacy/deletion-request",
      payload,
    );
    return response.data;
  },

  async cancelDeletion(): Promise<DeletionRequest> {
    const response = await apiClient.post<DeletionRequest>("/privacy/deletion-request/cancel");
    return response.data;
  },
};

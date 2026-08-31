import { apiClient } from "../../../shared/api/client";
import type {PhotoBOQLink, PhotoBOQLinkCreateRequest, ProgressClaim, ProgressClaimCreateRequest, ProgressClaimReviewRequest, ProgressClaimStatus, ProgressClaimUpdateRequest,
} from "../types/verification.types";

interface ListClaimsParams {
  projectId?: string;
  status?: ProgressClaimStatus;
  skip?: number;
  limit?: number;
}

export const verificationApi = {
  async listClaims(params: ListClaimsParams = {}): Promise<ProgressClaim[]> {
    const response = await apiClient.get<ProgressClaim[]>("/verification/progress-claims", {
      params: { project_id: params.projectId, status: params.status, skip: params.skip ?? 0, limit: params.limit ?? 100 },
    });
    return response.data;
  },

  async getClaim(claimId: string): Promise<ProgressClaim> {
    const response = await apiClient.get<ProgressClaim>(`/verification/progress-claims/${claimId}`);
    return response.data;
  },

  async createClaim(payload: ProgressClaimCreateRequest): Promise<ProgressClaim> {
    const response = await apiClient.post<ProgressClaim>("/verification/progress-claims", payload);
    return response.data;
  },

  async updateClaim(claimId: string, payload: ProgressClaimUpdateRequest): Promise<ProgressClaim> {
    const response = await apiClient.patch<ProgressClaim>(`/verification/progress-claims/${claimId}`, payload);
    return response.data;
  },

  async submitClaim(claimId: string): Promise<ProgressClaim> {
    const response = await apiClient.post<ProgressClaim>(`/verification/progress-claims/${claimId}/submit`);
    return response.data;
  },

  async approveClaim(claimId: string, payload: ProgressClaimReviewRequest): Promise<ProgressClaim> {
    const response = await apiClient.post<ProgressClaim>(`/verification/progress-claims/${claimId}/approve`, payload);
    return response.data;
  },

  async rejectClaim(claimId: string, payload: ProgressClaimReviewRequest): Promise<ProgressClaim> {
    const response = await apiClient.post<ProgressClaim>(`/verification/progress-claims/${claimId}/reject`, payload);
    return response.data;
  },

  async listPhotoBOQLinks(progressClaimId: string): Promise<PhotoBOQLink[]> {
    const response = await apiClient.get<PhotoBOQLink[]>("/verification/photo-boq-links", {
      params: { progress_claim_id: progressClaimId, limit: 100 },
    });
    return response.data;
  },

  async createPhotoBOQLink(payload: PhotoBOQLinkCreateRequest): Promise<PhotoBOQLink> {
    const response = await apiClient.post<PhotoBOQLink>("/verification/photo-boq-links", payload);
    return response.data;
  },

  async deletePhotoBOQLink(linkId: string): Promise<void> {
    await apiClient.delete(`/verification/photo-boq-links/${linkId}`);
  },
};
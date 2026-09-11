import { apiClient } from "../../../shared/api/client";
import type {ProcurementCreateRequest, ProcurementListParams, ProcurementOrganizationSummary, ProcurementRequest, ProcurementStatusUpdateRequest,
} from "../types/procurement.types";

export const procurementApi = {
  async listRequests(params: ProcurementListParams = {}): Promise<ProcurementRequest[]> {
    const response = await apiClient.get<ProcurementRequest[]>("/procurement/requests", {
      params: {
        project_id: params.projectId,
        status: params.status,
        skip: params.skip ?? 0,
        limit: params.limit ?? 100,
      },
    });

    return response.data;
  },

  async createRequest(payload: ProcurementCreateRequest): Promise<ProcurementRequest> {
    const response = await apiClient.post<ProcurementRequest>("/procurement/requests", payload);
    return response.data;
  },

  async updateStatus(requestId: string, payload: ProcurementStatusUpdateRequest): Promise<ProcurementRequest> {
    const response = await apiClient.patch<ProcurementRequest>(`/procurement/requests/${requestId}/status`, payload);
    return response.data;
  },
  
  async getOrganizationSummary(): Promise<ProcurementOrganizationSummary> {
    const response = await apiClient.get<ProcurementOrganizationSummary>(
      "/procurement/organization-summary",
    );

    return response.data;
  },

};
import { apiClient } from "../../../shared/api/client";
import type {ProcurementCreateRequest, ProcurementListParams, ProcurementOrganizationSummary, ProcurementRequest, ProcurementStatusUpdateRequest, ProcurementStatusSummary, ProcurementListResponse,
} from "../types/procurement.types";

export const procurementApi = {
  async listRequests(params: ProcurementListParams = {}): Promise<ProcurementListResponse> {
    const response = await apiClient.get<ProcurementListResponse>("/procurement/requests", {
      params: {
        project_id: params.projectId,
        status: params.status,
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
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

  async getStatusSummary(params: { projectId?: string } = {}): Promise<ProcurementStatusSummary> {
    const response = await apiClient.get<ProcurementStatusSummary>("/procurement/status-summary", {
      params: { project_id: params.projectId },
    });

    return response.data;
  },

};
import { apiClient } from "../../../shared/api/client";
import type { AIRequestEntry, AIRequestListParams, AIUsageSummary } from "../types/ai-requests.types";

export const aiRequestsApi = {
  async listRequests(params: AIRequestListParams = {}): Promise<AIRequestEntry[]> {
    const response = await apiClient.get<AIRequestEntry[]>("/ai-requests", {
      params: {
        purpose: params.purpose, entity_type: params.entityType, entity_id: params.entityId,
        skip: params.skip ?? 0, limit: params.limit ?? 100,
      },
    });
    return response.data;
  },

  async getUsageSummary(): Promise<AIUsageSummary> {
    const response = await apiClient.get<AIUsageSummary>("/ai-requests/usage-summary");
    return response.data;
  },
};
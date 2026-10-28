import { apiClient } from "../../../../shared/api/client";
import type { FinishRules, FinishRulesUpdate } from "../types/finishRules.types";

export const finishRulesApi = {
  async get(projectId: string): Promise<FinishRules> {
    return (await apiClient.get<FinishRules>(`/drawings-boq/projects/${projectId}/finish-rules`)).data;
  },
  async save(projectId: string, body: FinishRulesUpdate): Promise<FinishRules> {
    return (await apiClient.put<FinishRules>(`/drawings-boq/projects/${projectId}/finish-rules`, body)).data;
  },
};

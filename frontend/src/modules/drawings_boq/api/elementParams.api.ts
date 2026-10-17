import { apiClient } from "../../../shared/api/client";

export interface ElementParameterRange {
  low: number;
  high: number;
  default: number;
}

export interface ElementParameters {
  values: Record<string, Record<string, number>>;
  labels: Record<string, string>;
  ranges: Record<string, ElementParameterRange>;
}

export interface ElementParametersUpdate {
  values: Record<string, Record<string, number | null>>;
  labels?: Record<string, string>;
}

export const elementParamsApi = {
  async get(projectId: string): Promise<ElementParameters> {
    if (!projectId) throw new Error("Project ID is required");
    const response = await apiClient.get<ElementParameters>(`/drawings-boq/projects/${projectId}/element-parameters`);
    return response.data;
  },

  async save(projectId: string, update: ElementParametersUpdate): Promise<ElementParameters> {
    if (!projectId) throw new Error("Project ID is required");
    const response = await apiClient.put<ElementParameters>(`/drawings-boq/projects/${projectId}/element-parameters`, update);
    return response.data;
  },
};

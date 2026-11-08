import { apiClient } from "../../../../../shared/api/client";
import type { ReviewActionBody, ReviewActionResponse, ReviewResponse } from "../types/review.types";

const BASE = "/drawings-boq";

export const reviewApi = {
  async list(projectId: string, item?: string | null): Promise<ReviewResponse> {
    return (await apiClient.get<ReviewResponse>(`${BASE}/projects/${projectId}/takeoff/review`, { params: item ? { item } : undefined })).data;
  },
  async act(projectId: string, key: string, body: ReviewActionBody): Promise<ReviewActionResponse> {
    return (await apiClient.post<ReviewActionResponse>(`${BASE}/projects/${projectId}/takeoff/review/${encodeURIComponent(key)}/action`, body)).data;
  },
};

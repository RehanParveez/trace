import { apiClient } from "../../../../shared/api/client";
import type { PricedView } from "../types/priced.types";

const BASE = "/drawings-boq";

function params(profile?: string, rateBookId?: string) {
  return { profile: profile || undefined, rate_book_id: rateBookId || undefined };
}

export const pricedApi = {
  async get(projectId: string, profile?: string, rateBookId?: string): Promise<PricedView> {
    return (await apiClient.get<PricedView>(`${BASE}/projects/${projectId}/priced`, { params: params(profile, rateBookId) })).data;
  },
  async xlsx(projectId: string, profile?: string, rateBookId?: string): Promise<Blob> {
    return (await apiClient.get<Blob>(`${BASE}/projects/${projectId}/priced.xlsx`, { params: params(profile, rateBookId), responseType: "blob" })).data;
  },
};

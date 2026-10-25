import { apiClient } from "../../../../shared/api/client";
import type { MarkChoiceBody, MarkChoiceResult, MarkEntities } from "../types/markEntities.types";

const BASE = "/drawings-boq";

export const markEntitiesApi = {
  async list(drawingId: string): Promise<MarkEntities> {
    return (await apiClient.get<MarkEntities>(`${BASE}/drawings/${drawingId}/takeoff/mark-entities`)).data;
  },
  async choose(drawingId: string, body: MarkChoiceBody): Promise<MarkChoiceResult> {
    return (await apiClient.post<MarkChoiceResult>(`${BASE}/drawings/${drawingId}/takeoff/mark-entities/choose`, body)).data;
  },
};

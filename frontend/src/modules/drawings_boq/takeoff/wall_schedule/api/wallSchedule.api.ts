import { apiClient } from "../../../../../shared/api/client";
import type { WallSchedule } from "../types/wallSchedule.types";

const BASE = "/drawings-boq";

export const wallScheduleApi = {
  async get(drawingId: string): Promise<WallSchedule> {
    return (await apiClient.get<WallSchedule>(`${BASE}/drawings/${drawingId}/takeoff/wall-schedule`)).data;
  },
  async xlsx(drawingId: string): Promise<Blob> {
    return (await apiClient.get(`${BASE}/drawings/${drawingId}/takeoff/wall-schedule.xlsx`, { responseType: "blob" })).data;
  },
};

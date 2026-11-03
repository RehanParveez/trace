import { apiClient } from "../../../../../shared/api/client";
import type { DrawingPasses, TankSizeBody } from "../types/passes.types";

const BASE = "/drawings-boq";

export const passesApi = {
  async get(drawingId: string): Promise<DrawingPasses> {
    return (await apiClient.get<DrawingPasses>(`${BASE}/drawings/${drawingId}/takeoff/passes`)).data;
  },
  async typeTankSize(drawingId: string, body: TankSizeBody): Promise<DrawingPasses> {
    return (await apiClient.put<DrawingPasses>(`${BASE}/drawings/${drawingId}/takeoff/tank-sizes`, body)).data;
  },
};

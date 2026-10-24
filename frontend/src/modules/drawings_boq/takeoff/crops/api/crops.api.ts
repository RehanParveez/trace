import { apiClient } from "../../../../../shared/api/client";

export const cropsApi = {
  async candidate(candidateId: string, size: number): Promise<Blob> {
    const r = await apiClient.get(`/drawings-boq/takeoff/candidates/${candidateId}/crop`, { params: { size }, responseType: "blob" });
    return r.data as Blob;
  },
};

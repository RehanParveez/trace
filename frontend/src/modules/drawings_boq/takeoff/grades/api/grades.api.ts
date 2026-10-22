import { apiClient } from "../../../../../shared/api/client";
import type { GradesReport, StampBody } from "../../grades/types/grades.types";

const BASE = "/drawings-boq";

export const gradesApi = {
  async report(drawingId: string): Promise<GradesReport> {
    return (await apiClient.get<GradesReport>(`${BASE}/drawings/${drawingId}/takeoff/printed-grades`)).data;
  },
  async stamp(drawingId: string, body: StampBody): Promise<GradesReport> {
    return (await apiClient.post<GradesReport>(`${BASE}/drawings/${drawingId}/takeoff/printed-grades/stamp`, body)).data;
  },
  async unstamp(drawingId: string): Promise<GradesReport> {
    return (await apiClient.post<GradesReport>(`${BASE}/drawings/${drawingId}/takeoff/printed-grades/unstamp`)).data;
  },
};

import { apiClient } from "../../../../shared/api/client";
import type { LayoutChoiceBody, LayoutChoiceResult, LayoutGroups } from "../types/layoutGroups.types";

const BASE = "/drawings-boq";

export const layoutGroupsApi = {
  async list(drawingId: string): Promise<LayoutGroups> {
    return (await apiClient.get<LayoutGroups>(`${BASE}/drawings/${drawingId}/takeoff/layout-groups`)).data;
  },
  async choose(drawingId: string, body: LayoutChoiceBody): Promise<LayoutChoiceResult> {
    return (await apiClient.post<LayoutChoiceResult>(`${BASE}/drawings/${drawingId}/takeoff/layout-groups/choose`, body)).data;
  },
};

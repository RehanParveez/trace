import { apiClient } from "../../../../shared/api/client";
import type { MembersView } from "../types/members.types";

const BASE = "/drawings-boq";

export const membersApi = {
  async get(drawingId: string): Promise<MembersView> {
    return (await apiClient.get<MembersView>(`${BASE}/drawings/${drawingId}/takeoff/members`)).data;
  },
};

import { apiClient } from "../../../../shared/api/client";
import type { readingGapsResponse } from "../types/readingGaps.types";

const BASE = "/drawings-boq";

export const readingGapsApi = {
  async sheet(sheetId: string): Promise<readingGapsResponse> {
    return (await apiClient.get<readingGapsResponse>(`${BASE}/takeoff/sheets/${sheetId}/left-out`)).data;
  },
};

import { apiClient } from "../../../../shared/api/client";
import type { ReadingGapsResponse } from "../types/readingGaps.types";

const BASE = "/drawings-boq";

export const readingGapsApi = {
  async sheet(sheetId: string): Promise<ReadingGapsResponse> {
    return (await apiClient.get<ReadingGapsResponse>(`${BASE}/takeoff/sheets/${sheetId}/reading-gaps`)).data;
  },
};

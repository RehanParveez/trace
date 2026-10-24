import { apiClient } from "../../../../../shared/api/client";
import type { NotesReport } from "../types/notes.types";

const BASE = "/drawings-boq";

export const notesApi = {
  async report(drawingId: string): Promise<NotesReport> {
    return (await apiClient.get<NotesReport>(`${BASE}/drawings/${drawingId}/takeoff/notes`)).data;
  },
};

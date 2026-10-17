import { apiClient } from "../../../shared/api/client";

export type DatumBasis = "model" | "drawing" | "param" | "default" | "typed";

export interface DatumView {
  name: string;
  label: string;
  typed_z_mm: number | null;
  run_z_mm: number | null;
  run_basis: DatumBasis | null;
  run_note: string | null;
  editable: boolean;
}

export interface DatumsResponse {
  datums: DatumView[];
  typed: Record<string, number>;
  run_id: string | null;
  recorded_at: string | null;
}

export type DatumsUpdate = Record<string, number | null>;

export const datumsApi = {
  async get(projectId: string): Promise<DatumsResponse> {
    if (!projectId) throw new Error("Project ID is required");
    const response = await apiClient.get<DatumsResponse>(`/drawings-boq/projects/${projectId}/datums`);
    return response.data;
  },

  async save(projectId: string, values: DatumsUpdate): Promise<DatumsResponse> {
    if (!projectId) throw new Error("Project ID is required");
    const response = await apiClient.put<DatumsResponse>(`/drawings-boq/projects/${projectId}/datums`, { values });
    return response.data;
  },
};

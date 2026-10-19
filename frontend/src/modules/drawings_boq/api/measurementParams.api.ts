import { apiClient } from "../../../shared/api/client";
import type { DerivedParamName } from "../types/drawings-boq.types";

export interface MeasurementParameters {
  values: Partial<Record<DerivedParamName, number>>;
  defaults: Partial<Record<DerivedParamName, number>>;
  qs?: Partial<Record<DerivedParamName, number>>;
  drawing?: Partial<Record<DerivedParamName, number>>;
  drawing_notes?: Record<string, { text?: string | null; pages?: number[]; count?: number }>;
  drawing_conflicts?: { param: string; values: { value_mm: number; text?: string | null; pages?: number[] }[] }[];
  lap_table_mm?: Record<string, number>;
}

export type MeasurementParametersUpdate = Partial<Record<DerivedParamName, number | null>>;

export const measurementParamsApi = {
  async get(projectId: string): Promise<MeasurementParameters> {
    if (!projectId) throw new Error("Project ID is required");
    const response = await apiClient.get<MeasurementParameters>(
      `/drawings-boq/projects/${projectId}/measurement-parameters`,
    );
    return response.data;
  },

  async save(projectId: string, values: MeasurementParametersUpdate): Promise<MeasurementParameters> {
    if (!projectId) throw new Error("Project ID is required");
    const response = await apiClient.put<MeasurementParameters>(
      `/drawings-boq/projects/${projectId}/measurement-parameters`,
      { values },
    );
    return response.data;
  },
};

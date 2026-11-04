import { apiClient } from "../../../../../shared/api/client";
import type { SteelFigures, SteelFiguresSource, SteelSourceChoice } from "../types/steelFigures.types";

const B = "/drawings-boq";

export const steelFiguresApi = {
  async figures(runId: string, wastagePct?: number | null) {
    return (await apiClient.get<SteelFigures>(`${B}/calculation-runs/${runId}/steel-figures`, { params: { wastage_pct: wastagePct ?? undefined } })).data;
  },

  async source(projectId: string) {
    return (await apiClient.get<SteelSourceChoice>(`${B}/projects/${projectId}/steel-source`)).data;
  },

  async setSource(projectId: string, source: SteelFiguresSource) {
    return (await apiClient.put<SteelSourceChoice>(`${B}/projects/${projectId}/steel-source`, { source })).data;
  },
};

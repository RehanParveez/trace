import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { steelFiguresApi } from "../api/steelFigures.api";
import type { SteelFiguresSource } from "../types/steelFigures.types";

export const steelKeys = {
  root: ["steel-figures"] as const,
  figures: (runId: string, wastagePct: number | null) => ["steel-figures", runId, wastagePct ?? -1] as const,
};

export function useSteelFigures(runId: string, wastagePct: number | null = null) {
  return useQuery({ queryKey: steelKeys.figures(runId, wastagePct), queryFn: () => steelFiguresApi.figures(runId, wastagePct), enabled: Boolean(runId) });
}

export function useSetSteelSource(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (source: SteelFiguresSource) => steelFiguresApi.setSource(projectId, source),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: steelKeys.root }); },
  });
}

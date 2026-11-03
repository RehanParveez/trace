import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { takeoffKeys } from "../../hooks/useTakeoff";
import { passesApi } from "../api/passes.api";
import type { DrawingPasses, TankSizeBody } from "../types/passes.types";

export const passesKey = (drawingId: string, version: number) => [...takeoffKeys.all, "passes", drawingId, version] as const;

export function useDrawingPasses(drawingId: string | undefined, version = 0) {
  return useQuery({
    queryKey: passesKey(drawingId ?? "", version),
    queryFn: () => passesApi.get(drawingId as string),
    enabled: Boolean(drawingId),
    placeholderData: keepPreviousData,
  });
}

export function useTypeTankSize(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TankSizeBody): Promise<DrawingPasses> => passesApi.typeTankSize(drawingId as string, body),
    onSettled: () => {
      if (!drawingId) return;
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "passes", drawingId] });
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "review"] });
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "decisions", drawingId] });
    },
  });
}

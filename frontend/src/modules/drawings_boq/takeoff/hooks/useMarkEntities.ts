import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { markEntitiesApi } from "../api/markEntities.api";
import type { MarkChoiceBody } from "../types/markEntities.types";
import { takeoffKeys } from "./useTakeoff";

export const markEntityKeys = {
  list: (drawingId: string) => [...takeoffKeys.floorSources(drawingId), "marks"] as const,
};

export function useMarkEntities(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: markEntityKeys.list(drawingId ?? ""),
    queryFn: () => markEntitiesApi.list(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useChooseMarks(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MarkChoiceBody) => markEntitiesApi.choose(drawingId as string, body),
    onSuccess: (data) => { if (drawingId) qc.setQueryData(markEntityKeys.list(drawingId), data.marks); },
    onSettled: () => {
      if (!drawingId) return;
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
      void qc.invalidateQueries({ queryKey: takeoffKeys.ready(drawingId) });
      void qc.invalidateQueries({ queryKey: takeoffKeys.floorSources(drawingId) });
      void qc.invalidateQueries({ queryKey: takeoffKeys.overview(drawingId) });
    },
  });
}

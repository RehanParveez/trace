import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { layoutGroupsApi } from "../api/layoutGroups.api";
import type { LayoutChoiceBody } from "../types/layoutGroups.types";
import { takeoffKeys } from "./useTakeoff";

export const layoutGroupKeys = {
  list: (drawingId: string) => [...takeoffKeys.floorSources(drawingId), "layouts"] as const,
};

export function useLayoutGroups(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: layoutGroupKeys.list(drawingId ?? ""),
    queryFn: () => layoutGroupsApi.list(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useChooseLayouts(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LayoutChoiceBody) => layoutGroupsApi.choose(drawingId as string, body),
    onSuccess: (data) => { if (drawingId) qc.setQueryData(layoutGroupKeys.list(drawingId), data.layouts); },
    onSettled: () => {
      if (!drawingId) return;
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
      void qc.invalidateQueries({ queryKey: takeoffKeys.ready(drawingId) });
      void qc.invalidateQueries({ queryKey: takeoffKeys.floorSources(drawingId) });
      void qc.invalidateQueries({ queryKey: takeoffKeys.overview(drawingId) });
    },
  });
}

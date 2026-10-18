import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reviewApi } from "../api/review.api";
import { takeoffApi } from "../api/takeoff.api";
import { drawingsBoqKeys } from "../../hooks/useDrawingsBoq";
import { takeoffKeys } from "./useTakeoff";
import type { ResolveConflictsBody, SteelConventions } from "../types/review.types";

export const reviewKeys = {
  all: [...takeoffKeys.all, "review"] as const,
  conflicts: (drawingId: string, policy: string) => [...takeoffKeys.all, "review", "conflicts", drawingId, policy] as const,
  links: (drawingId: string) => [...takeoffKeys.all, "review", "links", drawingId] as const,
  steel: (drawingId: string, conventions: string) => [...takeoffKeys.all, "review", "steel", drawingId, conventions] as const,
};

function useRefreshAfterChange(drawingId: string | undefined) {
  const qc = useQueryClient();
  return () => {
    if (!drawingId) return;
    void qc.invalidateQueries({ queryKey: reviewKeys.all });
    void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "approve-preview"] });
    void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
    void qc.invalidateQueries({ queryKey: takeoffKeys.floorSources(drawingId) });
    void qc.invalidateQueries({ queryKey: takeoffKeys.overview(drawingId) });
    void qc.invalidateQueries({ queryKey: [...drawingsBoqKeys.all, "elements-page", drawingId] });
    void qc.invalidateQueries({ queryKey: drawingsBoqKeys.elements(drawingId) });
  };
}

export function useReviewFloors(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.floorSources(drawingId ?? ""),
    queryFn: () => takeoffApi.floorSources(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useCombineFloorSources(drawingId: string | undefined) {
  const qc = useQueryClient();
  const refresh = useRefreshAfterChange(drawingId);
  return useMutation({
    mutationFn: () => reviewApi.combineFloorSources(drawingId as string),
    onSuccess: (data) => { if (drawingId) qc.setQueryData(takeoffKeys.floorSources(drawingId), data.floors); },
    onSettled: refresh,
  });
}

export function useValueConflicts(drawingId: string | undefined, policy: Record<string, string>, enabled = true) {
  return useQuery({
    queryKey: reviewKeys.conflicts(drawingId ?? "", JSON.stringify(policy)),
    queryFn: () => reviewApi.conflicts(drawingId as string, policy),
    enabled: Boolean(drawingId) && enabled,
    staleTime: 0,
    placeholderData: keepPreviousData,
  });
}

export function useResolveConflicts(drawingId: string | undefined) {
  const refresh = useRefreshAfterChange(drawingId);
  return useMutation({
    mutationFn: (body: ResolveConflictsBody) => reviewApi.resolveConflicts(drawingId as string, body),
    onSettled: refresh,
  });
}

export function useMemberLinks(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: reviewKeys.links(drawingId ?? ""),
    queryFn: () => reviewApi.links(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
    staleTime: 0,
    placeholderData: keepPreviousData,
  });
}

export function useSteelRollup(drawingId: string | undefined, conventions: Partial<SteelConventions>, enabled = true) {
  return useQuery({
    queryKey: reviewKeys.steel(drawingId ?? "", JSON.stringify(conventions)),
    queryFn: () => reviewApi.steelRollup(drawingId as string, conventions),
    enabled: Boolean(drawingId) && enabled,
    staleTime: 0,
    placeholderData: keepPreviousData,
  });
}

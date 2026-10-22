import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tuningApi } from "../api/tuning.api";
import type { DecideBody, PlanBody } from "../types/tuning.types";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const tuningKeys = {
  all: [...takeoffKeys.all, "tuning"] as const,
  registry: () => [...takeoffKeys.all, "tuning", "registry"] as const,
  sweeps: (drawingId: string) => [...takeoffKeys.all, "tuning", "sweeps", drawingId] as const,
  sweep: (sweepId: string) => [...takeoffKeys.all, "tuning", "sweep", sweepId] as const,
};

export function useTuningRegistry(enabled = true) {
  return useQuery({ queryKey: tuningKeys.registry(), queryFn: () => tuningApi.registry(), enabled, staleTime: 5 * 60 * 1000 });
}

export function useTuningSweeps(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: tuningKeys.sweeps(drawingId ?? ""),
    queryFn: () => tuningApi.sweeps(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useTuningSweep(sweepId: string | null) {
  return useQuery({ queryKey: tuningKeys.sweep(sweepId ?? ""), queryFn: () => tuningApi.sweep(sweepId as string), enabled: Boolean(sweepId), staleTime: Infinity });
}

export function useTuningPlan(drawingId: string | undefined) {
  return useMutation({ mutationFn: (body: PlanBody) => tuningApi.plan(drawingId as string, body) });
}

export function useDecideAgain(sweepId: string | null) {
  return useMutation({ mutationFn: (body: DecideBody) => tuningApi.decide(sweepId as string, body) });
}

export function useDeleteSweep(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sweepId: string) => tuningApi.remove(sweepId),
    onSuccess: () => { if (drawingId) void qc.invalidateQueries({ queryKey: tuningKeys.sweeps(drawingId) }); },
  });
}
